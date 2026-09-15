"""Margemechaniek van een futures-positie, dag voor dag doorgerekend.

Dit bestand bevat geen statistiek maar boekhouding: hoe een margerekening
werkt, wanneer een margin call komt, en hoeveel cash je nodig had om hem te
overleven.

De begrippen
------------
**Notionele waarde** — de waarde van het onderliggende goud. Eén
COMEX-contract is 100 troy ounce, dus bij $4.000 per ounce is dat $400.000.
Dit bedrag betaal je NIET; het is alleen de maatstaf waarover je winst en
verlies berekend wordt.

**Initial margin** — het bedrag dat op je rekening moet staan om de positie
te mogen openen. Ongeveer 5% van de notionele waarde. Dit is geen aanbetaling
en geen kostenpost: het blijft van jou, het staat als onderpand vast.

**Maintenance margin** — de ondergrens. Zakt je saldo hieronder, dan volgt een
margin call. Ligt doorgaans rond 90% van de initial margin.

**Mark-to-market** — elke handelsdag wordt je positie herrekend tegen de
slotkoers. Beweegt de prijs tegen je in, dan gaat dat bedrag diezelfde dag van
je rekening af. Het is dus geen papieren verlies dat je kunt uitzitten; het
geld verdwijnt echt.

**Margin call** — het verzoek om bij te storten tot de initial margin. Doe je
dat niet (meestal binnen één dag), dan sluit de broker je positie gedwongen —
vaak op het slechtste moment.

**Variation margin** — het bedrag dat je bijstort. Dat is waar je
cash-buffer voor dient.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Standaard COMEX-goudcontract.
CONTRACT_SIZE_OUNCES = 100


@dataclass
class MarginSettings:
    """Instellingen van de margerekening.

    Attributen:
        initial_margin_pct: Percentage van de notionele waarde dat je moet
            storten om te mogen handelen.
        maintenance_pct: Percentage waaronder een margin call volgt,
            uitgedrukt als deel van de notionele waarde.
        contracts: Aantal contracten in de positie.
        is_short: True voor een short positie (winst bij dalende prijs).
    """

    initial_margin_pct: float = 0.05
    maintenance_pct: float = 0.045
    contracts: int = 1
    is_short: bool = True


@dataclass
class MarginDay:
    """Eén dag in de margerekening."""

    date: pd.Timestamp
    price: float
    daily_pnl: float
    balance_before_call: float
    margin_call: float
    balance_after_call: float
    cumulative_deposited: float
    maintenance_level: float


@dataclass
class MarginResult:
    """Uitkomst van een doorgerekende periode."""

    days: list[MarginDay] = field(default_factory=list)
    initial_margin: float = 0.0
    notional_start: float = 0.0
    total_deposited: float = 0.0
    n_margin_calls: int = 0
    largest_single_call: float = 0.0
    peak_cash_needed: float = 0.0
    net_loss: float = 0.0
    final_balance: float = 0.0

    def to_frame(self) -> pd.DataFrame:
        """Geeft het verloop als tabel terug."""
        return pd.DataFrame(
            [
                {
                    "datum": d.date.date(),
                    "prijs": d.price,
                    "dagresultaat": d.daily_pnl,
                    "saldo": d.balance_before_call,
                    "ondergrens": d.maintenance_level,
                    "bijstorten": d.margin_call,
                    "saldo_na": d.balance_after_call,
                    "totaal_gestort": d.cumulative_deposited,
                }
                for d in self.days
            ]
        )


def simulate_margin(
    prices: pd.Series, settings: MarginSettings | None = None
) -> MarginResult:
    """Rekent een futures-positie dag voor dag door.

    Argumenten:
        prices: Dagelijkse slotkoersen. De eerste is de instapprijs.
        settings: Marge-instellingen; None gebruikt de standaard.

    Geeft terug:
        ``MarginResult`` met per dag het verloop en samenvattende getallen.

    De berekening volgt de echte gang van zaken bij een broker:

    1. Bij opening stort je de initial margin.
    2. Elke dag wordt de positie herrekend tegen de nieuwe slotkoers. Het
       verschil gaat van je rekening af of komt erbij.
    3. Zakt het saldo onder de maintenance margin, dan moet je bijstorten tot
       de *initial* margin — niet tot de maintenance margin. Dat verschil is
       belangrijk: een margin call vraagt meer dan het tekort.

    Let op dat de margevereiste meebeweegt met de prijs. Stijgt goud, dan
    stijgt de notionele waarde en dus ook het bedrag dat je moet aanhouden.
    Bij een short positie werkt dat dubbel tegen je: je verliest geld én de
    eis wordt hoger.
    """
    settings = settings or MarginSettings()
    if len(prices) < 2:
        raise ValueError("Minstens twee koersen nodig om een verloop te berekenen.")

    ounces = CONTRACT_SIZE_OUNCES * settings.contracts
    direction = -1.0 if settings.is_short else 1.0

    entry_price = float(prices.iloc[0])
    notional_start = entry_price * ounces
    initial_margin = notional_start * settings.initial_margin_pct

    balance = initial_margin
    cumulative_deposited = initial_margin
    result = MarginResult(
        initial_margin=initial_margin,
        notional_start=notional_start,
    )

    previous_price = entry_price
    for date, raw_price in prices.iloc[1:].items():
        price = float(raw_price)

        # Mark-to-market: het prijsverschil maal het aantal ounces.
        daily_pnl = direction * (price - previous_price) * ounces
        balance += daily_pnl

        # De vereisten schalen mee met de actuele notionele waarde.
        notional_now = price * ounces
        maintenance_level = notional_now * settings.maintenance_pct
        required_level = notional_now * settings.initial_margin_pct

        balance_before = balance
        call = 0.0
        if balance < maintenance_level:
            # Bijstorten tot de INITIAL margin, niet tot de ondergrens.
            call = required_level - balance
            balance += call
            cumulative_deposited += call
            result.n_margin_calls += 1
            result.largest_single_call = max(result.largest_single_call, call)

        result.days.append(
            MarginDay(
                date=pd.Timestamp(date),
                price=price,
                daily_pnl=daily_pnl,
                balance_before_call=balance_before,
                margin_call=call,
                balance_after_call=balance,
                cumulative_deposited=cumulative_deposited,
                maintenance_level=maintenance_level,
            )
        )
        previous_price = price

    result.total_deposited = cumulative_deposited
    result.final_balance = balance

    # Twee verschillende getallen die je uit elkaar moet houden:
    #
    # peak_cash_needed — hoeveel cash je BESCHIKBAAR moest hebben om alle
    #   margin calls te kunnen voldoen. Dit is wat je buffer moet dekken.
    #
    # net_loss — wat je uiteindelijk KWIJT bent. Lager, omdat een deel van
    #   het gestorte geld gewoon op je rekening staat en terugkomt als je de
    #   positie sluit.
    #
    # Voor de buffervraag telt de eerste; voor de vraag "wat kost dit mij"
    # de tweede. Ze verwarren leidt tot een te hoge schatting van de kosten.
    result.peak_cash_needed = cumulative_deposited - initial_margin
    result.net_loss = cumulative_deposited - balance
    return result


def buffer_needed_for_confidence(
    returns: pd.Series,
    *,
    horizon_days: int,
    confidence: float = 0.99,
    settings: MarginSettings | None = None,
    n_windows: int | None = None,
) -> dict:
    """Berekent hoeveel buffer je historisch nodig had, als percentage.

    Methode: schuif een venster van ``horizon_days`` over de hele historie,
    reken voor elk venster door hoeveel je had moeten bijstorten, en neem het
    gevraagde percentiel van die verdeling.

    Dit is een *historische simulatie*: geen model, geen aannames over de
    verdeling, gewoon "wat was er nodig geweest?" Dat maakt hem eerlijk als
    referentie, maar ook beperkt — hij kent alleen scenario's die echt
    gebeurd zijn. Fase 4 vervangt dit door een Monte Carlo die ook
    scenario's genereert die nog niet voorkwamen.

    Argumenten:
        returns: Dagelijkse log-rendementen.
        horizon_days: Lengte van de periode die je wilt overbruggen.
        confidence: Bijvoorbeeld 0,99 voor "in 99 van de 100 gevallen genoeg".
        settings: Marge-instellingen.
        n_windows: Beperk het aantal vensters (voor snelheid); None = alle.

    Geeft terug:
        Dict met de buffer als percentage van de notionele waarde, plus
        context: hoeveel vensters, hoe vaak een margin call optrad, en het
        ergste geval.
    """
    settings = settings or MarginSettings()
    # Reconstrueer een prijsreeks uit de rendementen; het niveau doet er niet
    # toe omdat we alles als percentage van de notionele waarde uitdrukken.
    prices = pd.Series(
        100.0 * np.exp(returns.cumsum().values), index=returns.index
    )

    starts = range(0, len(prices) - horizon_days)
    if n_windows is not None and len(prices) - horizon_days > n_windows:
        step = (len(prices) - horizon_days) // n_windows
        starts = range(0, len(prices) - horizon_days, max(step, 1))

    buffers_pct: list[float] = []
    windows_with_call = 0

    for start in starts:
        window = prices.iloc[start : start + horizon_days + 1]
        outcome = simulate_margin(window, settings)
        notional = outcome.notional_start
        buffers_pct.append(outcome.peak_cash_needed / notional * 100)
        if outcome.n_margin_calls:
            windows_with_call += 1

    buffers = np.array(buffers_pct)
    return {
        "buffer_pct": float(np.percentile(buffers, confidence * 100)),
        "median_pct": float(np.median(buffers)),
        "worst_pct": float(buffers.max()),
        "n_windows": len(buffers),
        "share_with_margin_call": windows_with_call / len(buffers),
        "horizon_days": horizon_days,
        "confidence": confidence,
    }
