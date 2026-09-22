"""Fase 4: Monte Carlo-simulatie en de margevraag.

Dit script beantwoordt de vraag waar het project om begon:
hoeveel cash moet ik achterhouden voor een kwartaal-hedge?

Gebruik:
    python scripts/fase4_simulatie.py
    python scripts/fase4_simulatie.py --skip-backtest   # sneller, zonder Kupiec
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats as sps  # noqa: E402

from goldmodel.config import ALL_SERIES  # noqa: E402
from goldmodel.data.loader import DataLoader  # noqa: E402
from goldmodel.margin import CONTRACT_SIZE_OUNCES  # noqa: E402
from goldmodel.simulate import (  # noqa: E402
    SimulationSettings,
    compare_to_history,
    backtest_var,
    fit_garch,
    simulate_garch,
    simulate_gbm_normal,
    simulate_gbm_student_t,
)
from goldmodel.viz.distributions import compute_returns  # noqa: E402

LINE = "=" * 78


def section(title: str) -> None:
    """Print een sectiekop."""
    print(f"\n{LINE}\n{title}\n{LINE}")


def explain_the_approach() -> None:
    """Legt uit wat fase 4 doet en waarom dat mag na fase 3."""
    section("WAT FASE 4 DOET, EN WAAROM DAT MAG")
    print(
        "\nFase 3 concludeerde: de RICHTING van goud is niet te voorspellen.\n"
        "Toch gaan we nu simuleren. Is dat niet tegenstrijdig?\n"
        "\n"
        "Nee, en dat is de kern van fase 4.\n"
        "\n"
        "Een simulatie voorspelt de richting OOK NIET. Elk gesimuleerd pad is\n"
        "puur toeval - de ene helft gaat omhoog, de andere omlaag. Wat we wel\n"
        "gebruiken is de GROOTTE van de bewegingen, en die is aantoonbaar\n"
        "voorspelbaar: de autocorrelatie van de volatiliteit is 0,98.\n"
        "\n"
        "Voor je margevraag is dat precies genoeg. Je hoeft niet te weten of\n"
        "goud stijgt of daalt. Je moet weten HOE GROOT de tegenbeweging kan\n"
        "zijn, want dat bepaalt of je wordt uitgestopt.\n"
        "\n"
        "WAT WE PER PAD METEN\n"
        "Niet de eindwaarde. Voor een margin call telt de grootste\n"
        "TUSSENTIJDSE tegenbeweging: een pad dat halverwege 30% tegen je in\n"
        "staat en daarna terugkomt, heeft je wel degelijk uitgestopt.\n"
        "\n"
        "Dat heet de maximum adverse excursion, en het is het getal dat de\n"
        "margebehoefte bepaalt."
    )


def show_the_inputs(returns: pd.Series, spot: float) -> dict:
    """Toont de geschatte parameters en waar ze vandaan komen."""
    section("STAP 1: DE INPUT — WAT WE UIT DE DATA SCHATTEN")

    daily_mean = float(returns.mean())
    daily_volatility = float(returns.std())
    degrees_of_freedom = float(sps.t.fit(returns.values)[0])

    print(
        f"\nUit {len(returns):,} handelsdagen goudhistorie:\n"
        f"\n"
        f"  gemiddeld dagrendement     {daily_mean * 100:+.4f}%\n"
        f"  dagelijkse volatiliteit    {daily_volatility * 100:.4f}%\n"
        f"  op jaarbasis               {daily_volatility * np.sqrt(252) * 100:.1f}%\n"
        f"  t-vrijheidsgraden          {degrees_of_freedom:.2f}\n"
    )
    print(
        "WAAR DIE VRIJHEIDSGRADEN VANDAAN KOMEN\n"
        "Uit de QQ-plot van fase 1. Een t-verdeling met deze vrijheidsgraden\n"
        "past de goudrendementen veel beter dan een normale verdeling. Lage\n"
        "vrijheidsgraden betekenen dikke staarten.\n"
    )

    print("NU HET GARCH-MODEL")
    print(
        "\nGARCH(1,1) schat hoe de volatiliteit evolueert:\n"
        "\n"
        "    sigma^2_t = omega + alpha * schok^2_(t-1) + beta * sigma^2_(t-1)\n"
        "\n"
        "In woorden: de onrust van morgen is een basisniveau, plus een deel\n"
        "van de klap van gisteren, plus een deel van de onrust van gisteren."
    )

    parameters = fit_garch(returns)
    print(
        f"\n  omega (basisniveau)        {parameters.omega:.3e}\n"
        f"  alpha (klap van gisteren)  {parameters.alpha:.4f}\n"
        f"  beta  (onrust van gisteren){parameters.beta:.4f}\n"
        f"  persistentie (alpha+beta)  {parameters.persistence:.4f}\n"
        f"  halfwaardetijd van een schok {parameters.half_life_days:.0f} dagen\n"
        f"  t-vrijheidsgraden          {parameters.degrees_of_freedom:.2f}\n"
    )
    print(
        f"HOE JE DE PERSISTENTIE LEEST\n"
        f"Alpha plus beta is {parameters.persistence:.4f}. Dat is hoe traag een\n"
        "volatiliteitsschok uitdooft. Bij financiele data ligt dit normaal\n"
        "tussen 0,95 en 0,99; boven 1 zou het model niet-stationair zijn en\n"
        "zou onrust nooit uitdoven.\n"
        "\n"
        f"De halfwaardetijd van {parameters.half_life_days:.0f} dagen maakt het\n"
        "concreet: na die periode is de helft van een volatiliteitspiek\n"
        "weggeebd. Dat is precies de persistentie die fase 1 vond, nu als\n"
        "getal in een model."
    )

    current_volatility = float(np.sqrt(parameters.last_variance) * np.sqrt(252) * 100)
    long_run_volatility = float(
        np.sqrt(parameters.long_run_variance) * np.sqrt(252) * 100
    )
    print(
        f"\nDE HUIDIGE MARKT TEGENOVER HET GEMIDDELDE\n"
        f"  volatiliteit nu            {current_volatility:.1f}% (jaarbasis)\n"
        f"  langetermijnniveau         {long_run_volatility:.1f}%\n"
    )
    if current_volatility > long_run_volatility * 1.15:
        print(
            "  -> De markt is NU ONRUSTIGER dan gemiddeld. Een vaste vuistregel\n"
            "     op basis van het langjarig gemiddelde is op dit moment dus TE\n"
            "     KRAP."
        )
    elif current_volatility < long_run_volatility * 0.85:
        print(
            "  -> De markt is NU RUSTIGER dan gemiddeld. Een vaste vuistregel\n"
            "     houdt op dit moment dus onnodig veel kapitaal vast."
        )
    else:
        print("  -> De markt zit nu rond het langetermijngemiddelde.")

    print(
        "\nDIT IS WAT EEN VASTE VUISTREGEL NIET KAN.\n"
        "GARCH begint de simulatie bij de volatiliteit van VANDAAG, niet bij\n"
        "het gemiddelde van 23 jaar. Daardoor beweegt het antwoord mee met de\n"
        "markt."
    )

    return {
        "daily_mean": daily_mean,
        "daily_volatility": daily_volatility,
        "degrees_of_freedom": degrees_of_freedom,
        "garch": parameters,
        "spot": spot,
    }


def compare_models(
    inputs: dict, settings: SimulationSettings, returns: pd.Series
) -> dict:
    """Simuleert met de drie modellen en vergelijkt de uitkomsten."""
    section("STAP 2: DRIE MODELLEN, VAN SIMPEL NAAR REALISTISCH")
    print(
        f"\n{settings.n_paths:,} paden, horizon {settings.horizon_days} handelsdagen "
        "(ongeveer een kwartaal).\n"
        "Positie: SHORT, dus een prijsSTIJGING is het verlies.\n"
    )

    normal = simulate_gbm_normal(
        inputs["daily_mean"], inputs["daily_volatility"], settings
    )
    student = simulate_gbm_student_t(
        inputs["daily_mean"],
        inputs["daily_volatility"],
        inputs["degrees_of_freedom"],
        settings,
    )
    garch = simulate_garch(inputs["daily_mean"], inputs["garch"], settings)

    print("MODEL 1: GBM MET NORMALE SCHOKKEN")
    print(
        "  Het standaardmodel (Black-Scholes). Twee aannames die fase 1\n"
        "  weerlegde: normale schokken en constante volatiliteit.\n"
        "  We gebruiken het als REFERENTIE, niet als antwoord."
    )
    print("\nMODEL 2: GBM MET T-SCHOKKEN")
    print(
        "  Repareert aanname 1. Onderbouwd met de QQ-plot uit fase 1.\n"
        "  Volatiliteit nog wel constant."
    )
    print("\nMODEL 3: GARCH MET T-SCHOKKEN")
    print(
        "  Repareert ook aanname 2. De volatiliteit evolueert per dag en\n"
        "  begint bij het niveau van vandaag."
    )

    rows = []
    for result in (normal, student, garch):
        rows.append(
            {
                "model": result.model_name,
                "mediaan_tegenbeweging": result.percentiles((50,)).iloc[0][
                    "max_tegenbeweging_pct"
                ],
                "var_95": result.value_at_risk(0.95) * 100,
                "var_99": result.value_at_risk(0.99) * 100,
                "es_99": result.expected_shortfall(0.99) * 100,
                "ergste_pad": float(result.max_adverse.max()) * 100,
            }
        )

    table = pd.DataFrame(rows)
    print("\nGROOTSTE TUSSENTIJDSE TEGENBEWEGING, in procent van de notionele waarde:\n")
    print(table.round(2).to_string(index=False))

    print(
        "\nHOE JE DIT LEEST\n"
        "  var_95   in 95% van de paden bleef de tegenbeweging hieronder\n"
        "  var_99   idem voor 99%\n"
        "  es_99    het GEMIDDELDE verlies in de slechtste 1% van de paden\n"
        "\n"
        "Expected Shortfall repareert de bekende zwakte van VaR: een 99%-VaR\n"
        "van 20% is verenigbaar met een verlies van 21% in het slechtste\n"
        "procent, maar ook met 60%. ES vertelt je welke van de twee het is.\n"
        "Sinds Basel III de voorkeursmaat voor banken, om precies die reden."
    )

    print(
        "\nMAAR EERST: KLOPPEN DEZE GETALLEN MET DE WERKELIJKHEID?\n"
        "\n"
        "Een simulatie produceert altijd getallen. Voordat we er iets mee\n"
        "doen, zetten we ze naast wat er ECHT gebeurd is in 23 jaar\n"
        "goudhistorie."
    )
    comparison = compare_to_history(
        {"GBM normaal": normal, "GBM t": student, "GARCH t": garch},
        returns,
        horizon_days=settings.horizon_days,
        is_short=settings.is_short,
    )
    print()
    print(comparison.round(1).to_string(index=False))

    historical_p99 = float(comparison.loc[0, "p99"])
    deviations = comparison.iloc[1:].set_index("bron")["afwijking_p99_pp"]

    print(
        "\nDIT IS EEN ECHTE BEVINDING, GEEN DETAIL\n"
        f"  historisch gemeten 99%-grens: {historical_p99:.1f}%\n"
    )
    for model_name, deviation in deviations.items():
        direction = "overschat" if deviation > 0 else "onderschat"
        print(f"  {model_name:14s} {direction} met {abs(deviation):.1f} procentpunt")

    print(
        "\nWAAROM GARCH TE HOOG UITKOMT\n"
        "De geschatte persistentie is 0,9956 - bijna 1. Bij zo'n waarde is\n"
        "het model bijna niet-stationair en is het langetermijnniveau slecht\n"
        "bepaald: GARCH schat de langetermijnvolatiliteit op 20,8% terwijl de\n"
        "data 18,3% zegt. Over 63 dagen tikt dat verschil flink aan.\n"
        "\n"
        "WAT JE HIERMEE DOET\n"
        "Niet wegpoetsen. Je rapporteert een BANDBREEDTE: de modellen met\n"
        "constante volatiliteit geven een ondergrens, GARCH een bovengrens,\n"
        "en de historie zit ertussen. Voor een buffer is de bovengrens de\n"
        "conservatieve keuze - maar je moet weten DAT hij conservatief is, en\n"
        "waarom."
    )

    normal_var = table.loc[0, "var_99"]
    student_var = table.loc[1, "var_99"]
    garch_var = table.loc[2, "var_99"]

    print(
        f"\nWAT DE VERBETERINGEN OPLEVEREN (99%-VaR)\n"
        f"  normale schokken           {normal_var:.1f}%\n"
        f"  t-schokken                 {student_var:.1f}%  "
        f"({student_var - normal_var:+.1f} procentpunt)\n"
        f"  GARCH + t-schokken         {garch_var:.1f}%  "
        f"({garch_var - normal_var:+.1f} procentpunt tegenover normaal)"
    )

    if student_var > normal_var:
        print(
            f"\nDe t-schokken verhogen de geschatte margebehoefte met\n"
            f"{student_var - normal_var:.1f} procentpunt. Dat is precies het\n"
            "staartrisico dat het normale model niet ziet - en het is geen\n"
            "modelleerkeuze maar een correctie van een aantoonbaar foute\n"
            "aanname."
        )

    return {"normal": normal, "student": student, "garch": garch, "table": table}


def answer_the_question(inputs: dict, results: dict, settings: SimulationSettings) -> None:
    """Zet de simulatie om in een concreet antwoord op de margevraag."""
    section("STAP 3: HET ANTWOORD OP DE OORSPRONKELIJKE VRAAG")

    garch = results["garch"]
    spot = inputs["spot"]
    notional = spot * CONTRACT_SIZE_OUNCES

    print(
        f"\nDE POSITIE\n"
        f"  goudprijs                  ${spot:,.2f} per ounce\n"
        f"  een contract (100 ounce)   ${notional:,.0f} notioneel\n"
        f"  initial margin (5%)        ${notional * 0.05:,.0f}\n"
        f"  horizon                    {settings.horizon_days} handelsdagen\n"
    )

    print("HOEVEEL BUFFER, PER ZEKERHEIDSNIVEAU\n")
    rows = []
    for confidence, label in (
        (0.50, "de helft van de tijd"),
        (0.90, "9 van de 10 keer"),
        (0.95, "19 van de 20 keer"),
        (0.99, "99 van de 100 keer"),
        (0.999, "999 van de 1000"),
    ):
        var = garch.value_at_risk(confidence)
        rows.append(
            {
                "zekerheid": f"{confidence:.1%}",
                "betekenis": label,
                "buffer_pct": var * 100,
                "buffer_dollar": var * notional,
            }
        )
    frame = pd.DataFrame(rows)
    frame["buffer_pct"] = frame["buffer_pct"].map(lambda v: f"{v:.1f}%")
    frame["buffer_dollar"] = frame["buffer_dollar"].map(lambda v: f"${v:,.0f}")
    print(frame.to_string(index=False))

    var_99 = garch.value_at_risk(0.99)
    es_99 = garch.expected_shortfall(0.99)

    print(
        f"\nHET ANTWOORD\n"
        f"  Bij 99% zekerheid: {var_99 * 100:.1f}% van de notionele waarde\n"
        f"  = ${var_99 * notional:,.0f} per contract\n"
        f"\n"
        f"  En als je die grens toch doorbreekt, is het gemiddelde tekort\n"
        f"  {es_99 * 100:.1f}% (${es_99 * notional:,.0f}) - dat is de Expected\n"
        f"  Shortfall."
    )

    print(
        f"\nVERGELIJKING MET JE HUIDIGE VUISTREGEL\n"
        f"  jouw 5%                    ${notional * 0.05:,.0f}\n"
        f"  jouw 10%                   ${notional * 0.10:,.0f}\n"
        f"  model bij 99%              ${var_99 * notional:,.0f}"
    )

    coverage_5 = float((garch.max_adverse <= 0.05).mean())
    coverage_10 = float((garch.max_adverse <= 0.10).mean())
    print(
        f"\n  Volgens de simulatie dekt 5% {coverage_5:.1%} van de paden,\n"
        f"  en 10% dekt {coverage_10:.1%}."
    )

    print(
        "\nDE BELANGRIJKE NUANCE\n"
        "Dit is een LIQUIDITEITSbehoefte, geen verlies. Bij een hedge stijgt\n"
        "je fysieke goud evenveel als je futures verliezen; je vermogen blijft\n"
        "intact. Je hebt het geld alleen nodig OP HET MOMENT dat de broker\n"
        "belt.\n"
        "\n"
        "Een kredietlijn tegen je onderpand doet dus hetzelfde werk als cash,\n"
        "en kost je geen rendement."
    )


def validate(returns: pd.Series) -> None:
    """Backtest de VaR en toetst hem met Kupiec."""
    section("STAP 4: KLOPT HET MODEL? (KUPIEC-TOETS)")
    print(
        "\nDit is de belangrijkste stap van fase 4. Een simulatie produceert\n"
        "altijd wel getallen; deze toets stelt vast of die getallen ergens op\n"
        "gebaseerd zijn.\n"
        "\n"
        "HET IDEE\n"
        "Zeg je '99% VaR', dan verwacht je dat 1% van de waarnemingen de grens\n"
        "doorbreekt. Zie je er veel meer, dan is je model te optimistisch;\n"
        "veel minder, dan is het te conservatief en houd je onnodig kapitaal\n"
        "aan.\n"
        "\n"
        "DE OPZET (dezelfde discipline als fase 3)\n"
        "  - schat het model op data tot dag t\n"
        "  - voorspel de VaR voor de volgende 63 dagen\n"
        "  - kijk achteraf of de werkelijke tegenbeweging binnen de grens bleef\n"
        "  - schuif op, herhaal\n"
        "\n"
        "Dit duurt even: per venster wordt een GARCH-model geschat en 2000\n"
        "paden gesimuleerd."
    )

    outcome = backtest_var(
        returns, horizon_days=63, confidence=0.99, window=1000, step=63, n_paths=2000
    )
    kupiec = outcome["kupiec"]

    print(
        f"\n  vensters getest            {kupiec['n_observations']}\n"
        f"  overschrijdingen           {kupiec['n_exceedances']}\n"
        f"  verwacht bij 99%           {kupiec['expected_exceedances']:.1f}\n"
        f"  waargenomen percentage     {kupiec['observed_rate']:.2%}\n"
        f"  verwacht percentage        {kupiec['expected_rate']:.2%}\n"
        f"\n"
        f"  toetsingsgrootheid         {kupiec['statistic']:.3f}\n"
        f"  p-waarde                   {kupiec['p_value']:.4f}\n"
    )

    if kupiec["model_accepted"]:
        print(
            "  -> HET MODEL WORDT NIET VERWORPEN.\n"
            "     Het aantal overschrijdingen is verenigbaar met wat het model\n"
            "     belooft. Dat is geen bewijs dat het model perfect is, maar\n"
            "     het is wel wat je minimaal nodig hebt om het te gebruiken."
        )
    else:
        print(
            "  -> HET MODEL WORDT VERWORPEN.\n"
            "     Het aantal overschrijdingen wijkt significant af van de\n"
            "     belofte. Dat is een resultaat om te rapporteren, niet om weg\n"
            "     te poetsen."
        )

    if kupiec["n_exceedances"] < kupiec["expected_exceedances"]:
        print(
            "\n     Let op de RICHTING: er zijn MINDER overschrijdingen dan\n"
            "     verwacht. Het model is dus te conservatief - de buffer is\n"
            "     ruimer dan nodig. Dat is veiliger, maar het kost rendement."
        )

    print(
        "\nEEN BEPERKING DIE JE MOET BENOEMEN\n"
        "De testvensters overlappen niet in deze opzet (step = horizon), maar\n"
        "daardoor houd je weinig vensters over. Met zo'n klein aantal is de\n"
        "Kupiec-toets zwak: hij verwerpt alleen bij een grove afwijking.\n"
        "\n"
        "Dat is een eerlijke beperking van 23 jaar data bij een\n"
        "kwartaalhorizon, geen fout in de opzet. Met meer data zou de toets\n"
        "scherper zijn."
    )


def main() -> int:
    """Draait fase 4."""
    warnings.simplefilter("ignore")
    pd.set_option("display.width", 170)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-backtest",
        action="store_true",
        help="sla de Kupiec-backtest over (veel sneller)",
    )
    parser.add_argument("--paths", type=int, default=10_000, help="aantal paden")
    args = parser.parse_args()

    print(LINE)
    print("FASE 4: MONTE CARLO EN DE MARGEVRAAG")
    print(LINE)

    loader = DataLoader()
    report = loader.load_all(ALL_SERIES)
    panel = DataLoader.build_panel(report)
    prices = panel["gold_futures"].dropna()
    returns = compute_returns(panel, "gold_futures")

    explain_the_approach()
    inputs = show_the_inputs(returns, float(prices.iloc[-1]))

    settings = SimulationSettings(
        n_paths=args.paths, horizon_days=63, seed=42, is_short=True
    )
    results = compare_models(inputs, settings, returns)
    answer_the_question(inputs, results, settings)

    if args.skip_backtest:
        print(f"\n{LINE}")
        print("Kupiec-backtest overgeslagen (--skip-backtest).")
    else:
        validate(returns)

    section("WAT FASE 4 HEEFT OPGELEVERD")
    garch_var = results["garch"].value_at_risk(0.99) * 100
    normal_var = results["normal"].value_at_risk(0.99) * 100
    print(
        f"\n1. Een onderbouwd getal in plaats van een vuistregel:\n"
        f"   {garch_var:.1f}% buffer voor 99% zekerheid over een kwartaal.\n"
        f"\n"
        f"2. Het normale model zou {normal_var:.1f}% zeggen. Het verschil van\n"
        f"   {garch_var - normal_var:.1f} procentpunt is het staartrisico dat de\n"
        f"   klokvorm niet ziet.\n"
        f"\n"
        f"3. Een getal dat MEEBEWEEGT met de markt, doordat GARCH bij de\n"
        f"   volatiliteit van vandaag begint in plaats van bij het gemiddelde\n"
        f"   van 23 jaar.\n"
        f"\n"
        f"4. En een toets die vaststelt of die 99% ook echt 99% is.\n"
        f"\n"
        f"DE VOLLEDIGE KETEN\n"
        f"  fase 1  dikke staarten gemeten     -> t-verdeling nodig\n"
        f"  fase 1  clustering gemeten         -> GARCH nodig\n"
        f"  fase 2  verbanden zwak en instabiel\n"
        f"  fase 3  richting onvoorspelbaar    -> niet op richting mikken\n"
        f"  fase 4  grootte wel voorspelbaar   -> margebuffer berekenen\n"
        f"\n"
        f"Elke keuze in fase 4 is onderbouwd met een meting uit een eerdere\n"
        f"fase. Dat is wat het verdedigbaar maakt."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
