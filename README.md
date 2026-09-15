# Goudprijsmodel — macro-drivers, regressie en Monte Carlo

Een kwantitatief onderzoeksproject naar de relatie tussen de goudprijs en
macro-economische variabelen, met een Monte Carlo-simulatie voor het
inschatten van margeverplichtingen op futures-posities.

**Status:** fase 1 van 4 (datalaag) — afgerond en getest.

> **Nieuw hier, of even het overzicht kwijt?** Begin bij
> **[docs/START_HIER.md](docs/START_HIER.md)** — het hele project in vier
> bevindingen, één pagina. De rest van deze README is naslagwerk.

---

## Wat dit project *niet* is

Dit staat bovenaan omdat het belangrijker is dan wat het wel is.

- **Geen handelsadvies en geen beleggingsaanbeveling.** Niets in deze
  repository is bedoeld als grondslag voor een financiële beslissing.
- **Geen puntvoorspelling van de goudprijs.** De simulatielaag produceert een
  kansverdeling, geen getal. "Goud staat over drie maanden op $2.400" is een
  uitspraak die dit project niet doet en niet kan doen.
- **Geen bewijs dat goudprijzen voorspelbaar zijn.** Het uitgangspunt is het
  tegendeel: financiële markten zijn grotendeels efficiënt en de nulhypothese
  is dat een random walk niet te verslaan is. Als de validatie dat bevestigt,
  is dat het resultaat van het project en zo wordt het gerapporteerd.
- **Geen productiesysteem.** Het is een leer- en portfolioproject, gebouwd om
  methodologie te demonstreren.

Wat het wél is: een poging om een eerlijke, verdedigbare analyse te doen,
waarbij elke methodologische keuze expliciet gemaakt en gemotiveerd wordt —
inclusief de keuzes die het resultaat mínder indrukwekkend maken.

---

## De centrale vraag

> Hoeveel liquiditeit moet ik aanhouden voor margeverplichtingen op een short
> goudfutures-positie, zodat ik met 99% zekerheid geen margin call mis?

Een bestaande hedging-tool beantwoordt die vraag nu met een vuistregel van
5-10% van de notionele waarde. Dit project vervangt die vuistregel door een
onderbouwde verdeling: simuleer duizenden prijspaden over een kwartaal, kijk
naar de grootste tussentijdse tegenbeweging per pad, en lees het 99e
percentiel af.

De vuistregel is niet per se fout — het doel is om te kúnnen zeggen hoe fout
hij is, en onder welke marktomstandigheden.

---

## Opbouw in vier lagen

| Fase | Laag | Inhoud | Status |
|---|---|---|---|
| 1 | Data | FRED + yfinance ophalen, cachen, vintage-vraag | **klaar** |
| 2 | Verkenning | Stationariteit, ACF/PACF, correlatiestabiliteit, staarten | volgt |
| 3 | Regressie | OLS met Newey-West, VAR, ridge/lasso, walk-forward | volgt |
| 4 | Simulatie | GBM → t-schokken → GARCH, VaR/ES, margebehoefte | volgt |

De validatielaag (walk-forward backtesting, benchmarkvergelijking, Kupiec-toets)
loopt dwars door fase 3 en 4 heen en wordt niet achteraf toegevoegd.

---

## Aan de slag

### Installatie

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### FRED-sleutel

Haal een gratis sleutel op bij
[fredaccount.stlouisfed.org/apikeys](https://fredaccount.stlouisfed.org/apikeys),
kopieer `.env.example` naar `.env` en vul hem in:

```
FRED_API_KEY=jouw_sleutel_hier
```

`.env` staat in `.gitignore` en mag nooit gecommit worden.

### Controleer de installatie

```powershell
python scripts/check_setup.py
```

Dit controleert de Python-versie, de pakketten, je API-sleutel, beide
verbindingen en de cache — en zegt per onderdeel wat je moet doen als er iets
mis is.

### Data ophalen

```powershell
python scripts/fetch_data.py              # cache-eerst, alle reeksen
python scripts/fetch_data.py --refresh    # negeer de cache
python scripts/fetch_data.py --core       # alleen de kernreeksen
python scripts/fetch_data.py --cache-info # wat staat er in de cache?
```

### Zelftoets

```powershell
python scripts/zelftoets.py
```

Zes vragen over de vier bevindingen, met uitleg bij elk antwoord. Bedoeld om
zelf te kunnen zien wat al zit en wat nog niet.

Zonder FRED-sleutel draait het script gewoon door met alleen de
yfinance-reeksen; het rapporteert per reeks wat er gelukt is. Dat is bewust:
één onbereikbare bron mag een werksessie niet blokkeren.

### Tests

```powershell
python -m pytest tests/ -q
```

De tests raken het netwerk niet — ze gebruiken verzonnen dataframes en een
tijdelijke cachemap.

---

## Structuur

```
├── src/goldmodel/
│   ├── config.py              # reeksdefinities + economische motivatie
│   ├── data/
│   │   ├── cache.py           # Parquet-cache met TTL en stale-fallback
│   │   ├── fred_client.py     # FRED + ALFRED (vintage)
│   │   ├── yahoo_client.py    # yfinance met normalisatie
│   │   └── loader.py          # orkestratie, paneelopbouw
│   └── viz/
│       ├── style.py           # gedeelde opmaak en kleuren
│       └── distributions.py   # figuren over de verdeling
├── scripts/
│   ├── analyse_cycles.py      # spectraalanalyse van de volatiliteit
│   ├── check_setup.py         # controleert installatie en sleutels
│   ├── fetch_data.py          # haalt op en toont basisstatistieken
│   ├── plot_distributions.py  # maakt de zes figuren
│   └── zelftoets.py           # zes vragen over de bevindingen
├── tests/
│   ├── test_data_layer.py
│   ├── test_spectral.py
│   └── test_viz.py
├── docs/
│   ├── START_HIER.md          # het project in vier bevindingen (begin hier)
│   ├── uitleg_datalaag.md     # hoe de code werkt, stap voor stap
│   ├── begrippen.md           # elk statistisch begrip uitgelegd + links
│   ├── vintage_data.md        # revisies en look-ahead bias
│   └── gevorderd/             # verdieping, geen hoofdpad
├── output/figures/            # gitignored
└── data/cache/                # gitignored
```

**Leeswijzer, in volgorde:**

1. [START_HIER.md](docs/START_HIER.md) — de vier bevindingen, één pagina
2. [uitleg_datalaag.md](docs/uitleg_datalaag.md) — hoe de code werkt, zonder theorie
3. [begrippen.md](docs/begrippen.md) — naslagwerk per begrip, met links
4. `docs/gevorderd/` — verdieping, alleen als je er zin in hebt

---

## Gemaakte keuzes en waarom

### Welke variabelen, en waarom die

Elke reeks in [`config.py`](src/goldmodel/config.py) heeft een `rationale` van
enkele zinnen en een `expected_sign`. Dat verwachte teken is vooraf
opgeschreven — een discipline tegen achteraf-rationalisatie. Vindt het model
het omgekeerde teken, dan is dat iets om te verklaren, niet om weg te redeneren.

De belangrijkste driver is de **reële rente (DFII10)**, en die keuze rust op
een arbitrage-argument in plaats van op een gevonden correlatie: goud betaalt
geen rente, dus de kosten van het aanhouden ervan zijn precies de reële rente
die je misloopt op een veilig alternatief. Dat is uit te leggen zonder naar
data te verwijzen, wat het sterker maakt dan een empirisch verband.

Twee dingen zijn expliciet als *probleem* gemarkeerd in de configuratie:

- **T10YIE en DFII10 zijn definitorisch verbonden** (nominaal = reëel +
  breakeven). Ze samen in één regressie levert multicollineariteit op. Daarom
  kijken we in fase 3 naar VIF's en overwegen we regularisatie.
- **DXY en DTWEXBGS meten allebei de dollar.** Ze zijn er als robuustheidscheck
  op elkaar, niet als twee onafhankelijke drivers.

### Parquet in plaats van SQLite

We lezen vrijwel altijd hele reeksen in en werken daarna in pandas. Dan betaal
je bij SQLite de complexiteit (schema's, connecties, SQL) zonder het voordeel
te gebruiken. Parquet bewaart dtypes exact en `pd.read_parquet` geeft in één
regel hetzelfde dataframe terug.

Die keuze kan kantelen. Zodra we vintage-panels opslaan — elke observatiedatum
× elke publicatiedatum — wordt de data veel groter en gaan we er wél selectief
in filteren. Dat is een queryprobleem en daar wint SQLite. De cache-interface
is daarom smal gehouden (`load`/`save`/`is_fresh`), zodat er later een
SQLite-implementatie naast kan zonder de aanroepende code te raken.

### Vintage data: gebouwd, bewust niet overal gebruikt

Zie [`docs/vintage_data.md`](docs/vintage_data.md) voor de volledige
behandeling. Samengevat:

De kernreeksen zijn **dagelijkse marktnoteringen** — TIPS-rendementen,
wisselkoersen, obligatiespreads. Die worden niet herzien: het TIPS-rendement
van 3 maart 2020 was toen wat het nu is. Voor die reeksen levert huidige data
geen vertekening in de waarden op, en is het vintage-panel ophalen alleen
duurder en trager.

Wat wél speelt, ook zonder revisies, is de **publicatievertraging**: FRED
publiceert de waarde van dag *t* pas op werkdag *t+1*. Wie het goudrendement
van dag *t* verklaart uit de rente van dag *t*, gebruikt een getal dat toen nog
niet op FRED stond. Daarom heeft elke reeks een `publication_lag_days` die in
fase 2 bij het bouwen van de modelmatrix wordt toegepast.

De ALFRED-machinerie (`fetch_vintage_series`, `as_known_on`) is geïmplementeerd
en getest, klaar voor het moment dat we een reeks als CPI toevoegen waar
revisies wél substantieel zijn.

### Gaten in het paneel worden niet opgevuld

FRED-reeksen missen Amerikaanse feestdagen, Yahoo-reeksen het weekend, en de
Fed-balans is wekelijks. Het paneel bevat dus NaN's, en de datalaag vult die
niet op.

Dat is opzettelijk. Forward-fill van een wekelijkse reeks naar dagelijkse
frequentie creëert vijf identieke waarden op rij, en dus kunstmatige
autocorrelatie. Die maakt de standaardfouten in een regressie te klein en de
Durbin-Watson-statistiek onbruikbaar. Zo'n beslissing hoort zichtbaar in de
modelleerlaag thuis, met de gevolgen erbij, niet stilzwijgend in de datalaag.

---

## Eerste bevinding uit de data

De datalaag levert al één resultaat op dat de rest van het project stuurt.
Dagelijkse log-rendementen, 2003 tot heden (~5.900 handelsdagen):

| Reeks | Scheefheid | Exces-kurtosis | Dagen >3σ | Verwacht onder normaal |
|---|---|---|---|---|
| Goud | −0,53 | 6,54 | 77 | 16 |
| Zilver | −1,47 | 20,06 | 92 | 16 |
| S&P 500 | −0,46 | 13,21 | 97 | 16 |
| DXY | −0,05 | 1,82 | 66 | 16 |

Extreme dagen komen vier tot zes keer zo vaak voor als een normale verdeling
voorspelt, en Jarque-Bera verwerpt normaliteit met een p-waarde van praktisch
nul. De negatieve scheefheid betekent bovendien dat de grote dalingen extremer
zijn dan de grote stijgingen.

Dit is geen verrassing — het is een van de best gedocumenteerde feiten in de
financiële economie — maar het heeft directe gevolgen. Een Monte Carlo met
normaal verdeelde schokken **onderschat het staartrisico systematisch**, en
dat is precies het risico waar een margeberekening over gaat. De keuze voor
t-verdeelde schokken en GARCH in fase 4 is daarmee onderbouwd met data uit dit
project, in plaats van overgenomen als recept.

### De figuren

```powershell
python scripts/plot_distributions.py
```

Zes figuren in `output/figures/`, elk met een uitleg in de terminal:

| # | Figuur | Wat het laat zien |
|---|---|---|
| 1 | Verdeling tegenover normaal | Hogere piek, dikkere staarten, tekort in het middengebied |
| 2 | Kurtosis uitgelegd | Waarom de vierde macht; **1% van de dagen levert 73% van de kurtosis** |
| 3 | Scheefheid | Dalingen over stijgingen geklapt; de tien extreemste dagen |
| 4 | QQ-plot | De klassieke S-curve tegen normaal, bijna recht tegen t |
| 5 | Volatiliteitsclustering | Richting onvoorspelbaar, grootte wél — de basis voor GARCH |
| 6 | Reeksen vergeleken | Dikke staarten zijn niet uniek voor goud |

Drie extra figuren over de cyclusvraag staan in `output/figures/gevorderd/`.

### Onderzoeksvraag: zit er een cyclus in de volatiliteit?

Rustige en onrustige periodes wisselen elkaar af — zit daar een vast ritme in?
**Nee.** Wat eruitziet als cycliciteit is *persistentie*: onrust houdt aan en
dooft uit, zonder klok. Dat is wel voorspelbaar, maar anders — en precies wat
GARCH modelleert.

De volledige analyse (spectraalanalyse, referentieverdelingen, het
Slutsky-Yule-effect) staat in
[docs/gevorderd/cyclusanalyse.md](docs/gevorderd/cyclusanalyse.md). Dat is
verdiepingsmateriaal, geen onderdeel van het hoofdpad.

Drie dingen die uit de figuren kwamen en niet uit de tabel:

**De t-verdeling past met 3,6 vrijheidsgraden.** Dat is laag — de staarten zijn
fors dikker dan normaal. In de QQ-plot ligt de data er zichtbaar beter op dan
op de normale lijn. Dat is de empirische onderbouwing voor de schokverdeling
in fase 4.

**Kurtosis is extreem geconcentreerd.** 1% van de handelsdagen bepaalt 73% van
het getal, 5% bepaalt 90%. Dat maakt kurtosis een instabiele schatting: haal
je vijf dagen weg, dan verandert het getal fors. Het is een reden om er niet
te veel gewicht aan te geven en de QQ-plot als hoofdbewijs te gebruiken.

**Volatiliteit clustert, en dat is een apart verschijnsel.** De autocorrelatie
van de rendementen zelf blijft binnen de toevalsgrenzen — de richting is
onvoorspelbaar, zoals de efficiënte-markthypothese voorspelt. Maar de
autocorrelatie van de *absolute* rendementen is duidelijk positief en houdt
weken aan. Dat contrast is precies wat GARCH modelleert.

---

## Vervolg

Fase 2 begint met de vraag die aan alle regressie voorafgaat: zijn deze reeksen
stationair? Het antwoord is vrijwel zeker nee voor de niveaus, en dat bepaalt
in welke vorm alles het model in gaat.

---

## Licentie en disclaimer

Educatief project. De data komt van FRED (publiek domein) en Yahoo Finance
(onofficiële bron, geen garanties op juistheid of beschikbaarheid). Geen
handelsadvies.
