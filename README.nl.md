# Goudprijs-risicomodel

**Kwantitatieve analyse van goudfutures: macro-drivers, validatie van
voorspelkracht, en Monte Carlo-simulatie voor margebehoefte.**

*English version: [README.md](README.md)*

---

## De vraag die dit project beantwoordt

> Ik houd een short goudfutures-positie aan als hedge, een kwartaal lang.
> Hoeveel liquiditeit moet ik beschikbaar hebben om met 99% zekerheid geen
> margin call te missen?

Een bestaande hedging-tool antwoordt met een vuistregel: **5 tot 10% van de
notionele waarde**. Dit project vervangt die door een getal dat uit de data
volgt, met een expliciete uitspraak over hoe onzeker dat getal is.

**De kernuitkomst:** over een kwartaal dekt 5% ongeveer 44% van de gesimuleerde
paden en 10% ongeveer 69%. Voor 99% zekerheid is grofweg **26 tot 34% van de
notionele waarde** nodig, afhankelijk van het volatiliteitsmodel — en die
bandbreedte is zelf de bevinding, niet een gebrek.

---

## Wat dit project *niet* is

Deze sectie staat vooraan omdat hij belangrijker is dan de resultaten.

- **Geen handelsadvies.** Niets hierin is een grondslag voor een financiële
  beslissing.
- **Geen puntvoorspelling.** De simulatie levert een kansverdeling, nooit één
  voorspelde prijs.
- **Geen bewijs dat goudrendementen voorspelbaar zijn.** De nulhypothese was dat
  een random walk niet te verslaan is. Fase 3 bevestigt dat, en zo wordt het
  gerapporteerd.
- **Geen productiesysteem.** Het is een leer- en portfolioproject, gebouwd om
  methodologie te demonstreren.

Wat het wél is: een eerlijke, verdedigbare analyse waarin elke methodologische
keuze expliciet wordt gemaakt en gemotiveerd — inclusief de keuzes die het
resultaat *minder* indrukwekkend maken.

---

## Kernbevindingen

| # | Bevinding | Bewijs |
|---|---|---|
| 1 | Rendementen hebben dikke staarten | Exces-kurtosis **6,05**; **79** dagen buiten 3σ waar een normale verdeling **16** voorspelt |
| 2 | Verliezen zijn extremer dan winsten | Scheefheid **−0,49** |
| 3 | Volatiliteit clustert en houdt aan | GARCH-persistentie **0,9956**, halfwaardetijd **156 dagen** |
| 4 | Er zit geen cyclus in de volatiliteit | Spectrale piek op 64 dagen verklaart **0,8%** van de variantie en faalt out-of-sample |
| 5 | Macro-verbanden zijn zwak | Sterkste losse driver verklaart **16%** van de dagelijkse variantie |
| 6 | Macro-verbanden zijn instabiel | **4 van 5** drivers wisselen van teken door de tijd (S&P 500: −0,33 tot +0,43) |
| 7 | Goud is op dagbasis geen veilige haven | Correlatie goud–VIX **−0,02** over de hele periode *en in elke subperiode*, inclusief de crash van 2020 |
| 8 | De richting is niet voorspelbaar | R² out-of-sample **−0,04**; directional accuracy **43,8%** (onder munt-opgooien) |
| 9 | De grootte *wel* | Dit is wat het margemodel gebruikt |

**Het centrale contrast:** de richting is onvoorspelbaar, de grootte niet. Een
margeberekening heeft alleen het tweede nodig.

---

## Methodologie

### Fase 1 — Datalaag en verdelingsanalyse

- 12 reeksen van FRED en Yahoo Finance, 2003 tot nu (**5.957** handelsdagen)
- Elke reeks heeft een economische motivatie en een **vooraf vastgelegd verwacht
  teken** in [`config.py`](src/goldmodel/config.py) — een discipline tegen
  achteraf-rationalisatie
- Parquet-cache met TTL, stale-fallback en graceful degradation per reeks
- Revisiegedrag per reeks geclassificeerd; ALFRED vintage-ophaling geïmplementeerd
  voor reeksen die *wel* worden herzien
- Publicatievertraging per reeks vastgelegd (FRED publiceert dag *t* op werkdag
  *t+1*) en toegepast bij het bouwen van de modelmatrix

### Fase 2 — Stationariteit en stabiliteit van verbanden

- **Schijnregressie gequantificeerd:** op prijsniveaus vindt OLS een
  "significant" verband in **92%** van 400 proeven met *onafhankelijke random
  walks*. Op verschillen: 4%, zoals het hoort.
- ADF en KPSS op alle reeksen — tegengestelde nulhypotheses, zodat ze elkaar
  kunnen bevestigen of tegenspreken. Tien van de twaalf reeksen zijn
  niet-stationair in niveaus.
- Rolling correlaties (venster van 252 dagen) leggen de instabiliteit bloot die
  een gemiddelde over de hele periode verbergt.
- VIF per driver om multicollineariteit zichtbaar te maken.

### Fase 3 — Regressie met eerlijke validatie

- OLS met **Newey-West** standaardfouten, omdat de residuen heteroskedastisch en
  geautocorreleerd zijn. De correctie blaast de standaardfouten met
  **1,66 tot 1,81 keer** op; één driver gaat daardoor van significant naar
  niet-significant.
- **Walk-forward validatie:** schat tot dag *t*, voorspel *t+1*, schuif op.
  Drivers met één dag gelagd. Nooit getraind op toekomstige data.
- De benchmark is een **random walk**. Uitkomst: OLS is **1,96% slechter** op
  RMSE, met een negatieve out-of-sample R².
- **Diebold-Mariano-toets** om een echt verschil van ruis te scheiden: geen
  significant verschil.

### Fase 4 — Monte Carlo en margebehoefte

Drie modellen, elk onderbouwd met een eerdere meting:

| Model | Repareert | 99%-buffer | Expected Shortfall |
|---|---|---|---|
| GBM, normale schokken | — (referentie) | 26,0% | 29,7% |
| GBM, Student-t (df 3,5) | dikke staarten (fase 1) | 26,4% | 32,3% |
| **GARCH(1,1), t-schokken** | ook clustering (fase 1) | **34,5%** | **44,9%** |

- Per pad meten we de **maximum adverse excursion** — de grootste *tussentijdse*
  beweging tegen de positie in, want daar komt de margin call, niet op de
  einddatum.
- **De drift staat standaard op nul.** Het historische gemiddelde van
  +0,043% per dag is +2,7% per kwartaal en verhoogt de 99%-VaR met ruim 3
  procentpunt. Fase 3 toonde dat de richting onvoorspelbaar is, en de
  standaardfout van dat gemiddelde is een derde van de schatting zelf. Hem
  meenemen zou stilletjes een puntvoorspelling inbouwen.

#### Validatie tegen de werkelijkheid, niet alleen interne consistentie

| Bron | p50 | p95 | p99 | Afwijking |
|---|---|---|---|---|
| **Historisch (echte data)** | 6,7% | 21,3% | **29,3%** | — |
| GBM normaal | 5,7% | 18,9% | 26,0% | −3,3 pp |
| GBM t | 5,3% | 18,6% | 26,4% | −3,0 pp |
| GARCH t | 6,1% | 22,3% | 34,5% | +5,2 pp |

De modellen met constante volatiliteit **onderschatten** de staart; GARCH
**overschat** hem. Oorzaak: een persistentie van 0,9956 is bijna
niet-stationair, waardoor het langetermijnniveau slecht bepaald is — GARCH schat
20,8% jaarvolatiliteit waar de data 18,3% zegt.

- **Kupiec-toets** (proportion of failures) over drie horizonnen. Alle drie de
  modellen halen de toets, maar GARCH is het best gekalibreerd: op de scherpste
  toets (495 vensters) precies 5 overschrijdingen tegen 5 verwacht, tegenover 9
  voor het normale model.

---

## Het antwoord

Bij $4.379 per ounce is één contract (100 ounce) **$437.940** notioneel.

| Zekerheid | Buffer | USD |
|---|---|---|
| 50% | 6,1% | $26.554 |
| 95% | 22,3% | $97.751 |
| **99%** | **34,5%** | **$151.108** |
| 99,9% | 57,6% | $252.443 |

Gerapporteerd als **bandbreedte**, omdat de modellen uiteenlopen en dat verschil
informatief is:

- **Ondergrens** (constante volatiliteit): ongeveer 26%
- **Historisch gemeten**: 29,3%
- **Bovengrens** (GARCH, best gekalibreerd): 34,5%

### De nuance die het resultaat herkadert

Dit is een **liquiditeitsbehoefte, geen verlies.** Bij een hedge stijgt het
fysieke goud evenveel als de futures-positie verliest; het netto vermogen
verandert niet. De cash is alleen nodig *op het moment* dat de broker belt.

Een kredietlijn tegen het onderpand doet dus hetzelfde werk als cash, zonder de
gemiste rendementen. "Toegang tot 34,5%" is een wezenlijk andere eis dan "34,5%
in cash".

---

## Gevonden en gecorrigeerde fouten

Gedocumenteerd, omdat ze vinden precies is waar de validatielaag voor is.

| Fout | Gevolg | Hoe het bovenkwam |
|---|---|---|
| Alle margestortingen opgeteld in plaats van de piek netto-inleg | Kwartaalbuffer ongeveer 5 pp te hoog | Het nettoverlies was niet gelijk aan de prijsbeweging |
| De gelijktijdige R² van 18,6% gerapporteerd als bruikbaar | Voorspelbaarheid factor 11 overschat | Drivers lagen liet hem naar 1,7% zakken |
| Beweerd dat Kupiec het normale model verwierp (p=0,045) | Onjuiste bevinding | De p-waarde flipte met het toevalszaad — Monte Carlo-ruis, geen bewijs |
| Een geschudde referentie gebruikt in de spectraaltoets | Zou een "cyclus" van 1.483 dagen hebben gevonden | Een AR(1)-referentie die persistentie behoudt liet hem verdwijnen |
| Beweerd dat aangepaste R² nutteloze variabelen afstraft | Bescherming overschat | 50 kolommen ruis toevoegen *verhoogde* de aangepaste R² |

Elk van deze is nu gedekt door een regressietest.

---

## Kwaliteitsborging

- **139 tests**, zonder netwerkafhankelijkheid (verzonnen dataframes, tijdelijke
  mappen)
- **Positieve controles overal:** de walk-forward-validator moet een ingebouwd
  signaal *vinden* (R² out-of-sample > 0,5); de Kupiec-toets moet een verkeerd
  gekalibreerd model *verwerpen*. Zonder die controles zegt "geen signaal
  gevonden" niets.
- **Look-ahead-bewaking:** een test vervangt alle data na dag 1.500 door onzin en
  controleert dat eerdere voorspellingen bit-identiek blijven.
- Vaste toevalszaden, zodat elk gerapporteerd getal reproduceerbaar is.

---

## Aan de slag

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1           # Windows
pip install -r requirements.txt

cp .env.example .env                  # vul een gratis FRED API-sleutel in
python scripts/check_setup.py         # controleert pakketten, sleutel, verbindingen, cache
```

Zonder FRED-sleutel draait het project door op de Yahoo Finance-reeksen en
rapporteert het per reeks wat gelukt is.

### De analyse reproduceren

```bash
python scripts/fetch_data.py              # data ophalen en cachen
python scripts/plot_distributions.py      # fase 1: verdelingsfiguren
python scripts/fase2_stationariteit.py    # fase 2: ADF/KPSS, schijnregressie
python scripts/fase2_correlaties.py       # fase 2: correlaties en stabiliteit
python scripts/fase3_regressie.py         # fase 3: OLS, walk-forward, DM-toets
python scripts/fase4_simulatie.py         # fase 4: Monte Carlo, VaR, ES
python scripts/fase4_figuren.py           # fase 4: figuren en Kupiec-validatie
python -m pytest tests/ -q                # 139 tests
```

---

## Technische stack

`pandas` · `numpy` · `statsmodels` · `arch` (GARCH) · `scikit-learn` (ridge) ·
`scipy` · `pyarrow` · `matplotlib` · `pytest`

**Ontwerpkeuzes.** Reeksdefinities zijn data, geen code — een driver toevoegen is
een configuratiewijziging. De cache-interface is bewust smal
(`load`/`save`/`is_fresh`), zodat een SQLite-backend Parquet kan vervangen zodra
vintage-panels selectief bevraagd moeten worden. Docstrings en commentaar zijn in
het Nederlands; alle identifiers in het Engels.

---

## Structuur

```
src/goldmodel/
  config.py          reeksdefinities: economische motivatie + verwacht teken
  margin.py          margeboekhouding en bufferberekening
  models.py          OLS/Newey-West, walk-forward, Diebold-Mariano
  simulate.py        Monte Carlo, GARCH, VaR/ES, Kupiec
  data/              FRED + ALFRED, Yahoo, Parquet-cache, loader
  viz/               figuren per analyselaag
scripts/             één uitvoerbaar script per analysestap
tests/               139 tests, inclusief positieve controles
docs/                bevindingen per fase, begrippen, backlog
output/figures/      23 figuren, 20 in de hoofdanalyse (gitignored)
```

### Documentatie

| Document | Inhoud |
|---|---|
| [HET_HELE_VERHAAL.md](docs/HET_HELE_VERHAAL.md) | het volledige verhaal, van nul tot nu |
| [fase2_resultaat.md](docs/fase2_resultaat.md) | stationariteit, correlaties, stabiliteit |
| [fase3_resultaat.md](docs/fase3_resultaat.md) | regressie en walk-forward validatie |
| [fase4_resultaat.md](docs/fase4_resultaat.md) | simulatie, VaR, Kupiec, het antwoord |
| [r2_uitgelegd.md](docs/r2_uitgelegd.md) | waarom R² 18,6%, 1,7% en −0,04 is |
| [vintage_data.md](docs/vintage_data.md) | revisies, ALFRED, look-ahead bias |
| [begrippen.md](docs/begrippen.md) | elk statistisch begrip, met verwijzingen |
| [backlog/](docs/backlog/README.md) | voorstellen met de reden waarom ze wachten |

---

## Bekende beperkingen

Expliciet benoemd in plaats van aan de lezer gelaten.

1. **De Kupiec-toets is zwak bij deze steekproefgrootte.** Zelfs bij 495
   vensters verwacht je maar 5 overschrijdingen; het verschil tussen 5 en 9 is
   statistisch niet te scheiden. De modellen echt onderscheiden zou meer dan 23
   jaar data vragen.
2. **GARCH-persistentie van 0,9956 is bijna niet-stationair.** De
   langetermijnvariantie is daardoor slecht bepaald, en dat is waarom GARCH de
   kwartaalstaart met ongeveer 5 pp overschat.
3. **Differentiëren gooit niveau-informatie weg.** Het arbitrage-argument over de
   reële rente gaat over niveaus; cointegratie zou dat opvangen en is niet
   geïmplementeerd. Gedocumenteerd in de backlog.
4. **Continue front-month futures bevatten roll-effecten.** Klein bij goud
   (vlakke forwardcurve) maar aanwezig.
5. **Weinig backtest-vensters op kwartaalhorizon** (78 niet-overlappend) — een
   onvermijdelijk gevolg van 23 jaar data op die horizon.
6. **Instabiele coëfficiënten worden gerapporteerd, niet opgelost.** Vier van de
   vijf drivers wisselen van teken door de tijd; een regime-switching model is de
   logische vervolgstap en staat in de backlog.

---

## Licentie en databronnen

Educatief project. Data van FRED (publiek domein) en Yahoo Finance (onofficiële
bron, geen garanties op juistheid of beschikbaarheid). Geen beleggingsadvies.
