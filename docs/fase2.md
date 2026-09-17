# Fase 2: wat doet het, en waar staan we?

## Wat fase 2 doet

Fase 1 vroeg: **hoe** beweegt goud? (dikke staarten, scheefheid, onrust in
blokken)

Fase 2 vraagt: **waarom** beweegt goud? Kunnen we die bewegingen verklaren uit
macro-economische data — de reële rente, de dollar, de inflatieverwachting?

Maar er zit een valkuil tussen, en die wegnemen is stap 1.

---

## Stap 1: de valkuil — schijnregressie

### Het experiment

Ik maak twee reeksen met een toevalsgenerator. Elke reeks is een cumulatieve som
van eigen toevalsgetallen. Er is **per constructie geen verband**: geen gedeelde
schok, geen gedeelde trend, niets.

Dan regresseer ik de één op de ander:

| | R² | t-waarde | p-waarde |
|---|---|---|---|
| Op **niveaus** | 0,789 | 61,0 | ~0 |
| Op **veranderingen** | 0,0001 | −0,25 | 0,80 |

De bovenste regel zou je in een gesprek presenteren als "een sterk significant
verband, 79% verklaarde variantie". Het is **volledig nep** — de data is
toevalsruis.

### Hoe vaak dit gebeurt

Ik heb het experiment 400 keer herhaald met steeds nieuwe toevalsreeksen:

| Regressie op | "Significant" gevonden | Hoort te zijn |
|---|---|---|
| **niveaus** | **92%** | 5% |
| veranderingen | 4% | 5% |

Lees dat goed. Bij een significantieniveau van 5% hóórt een toets in 5% van de
gevallen ten onrechte "significant" te zeggen — dat is wat 5% betekent. Op
veranderingen klopt dat. Op niveaus is het 92%: **de toets is dan gewoon kapot.**

### Waarom

Twee reeksen die allebei een trend hebben, bewegen allebei "omhoog over tijd".
Dat alleen al levert een hoge correlatie op. De regressie ziet gezamenlijke
*beweging* en noemt dat gezamenlijke *oorzaak*.

Granger en Newbold beschreven dit in 1974. Het is de meest voorkomende manier
waarop econometrisch onderzoek fout gaat.

*Figuur: `output/figures/13_schijnregressie.png`*

---

## Stap 2: de oplossing — stationariteit

Een reeks is **stationair** als zijn statistische eigenschappen niet van de tijd
afhangen:

- hetzelfde gemiddelde, of je naar 2005 of 2025 kijkt
- dezelfde spreiding
- dezelfde samenhang met zijn eigen verleden

**Een prijsreeks is dat vrijwel nooit.** Goud stond rond $400 in 2003 en rond
$4.300 in 2026. Er is geen "gemiddelde goudprijs" waar hij naar terugkeert — het
gemiddelde hangt af van welke periode je pakt.

Concreet uit de data: het voortschrijdend vijfjaarsgemiddelde van de goudprijs
liep van $500 naar $2.700. Dat van het dagrendement bleef tussen −0,03% en
+0,09%.

*Figuur: `output/figures/14_stationariteit.png` — let op het verschil in
y-as-schaal tussen de twee rechterpanelen*

---

## De twee toetsen

### ADF (Augmented Dickey-Fuller)

- **Nulhypothese:** de reeks is NIET stationair
- Kleine p-waarde → bewijs **vóór** stationariteit

### KPSS

- **Nulhypothese:** de reeks IS stationair (precies omgekeerd)
- Kleine p-waarde → bewijs **tégen** stationariteit

### Waarom twee toetsen met omgekeerde vraagstelling?

Omdat ze elkaar kunnen bevestigen of tegenspreken. Vier uitkomsten:

| ADF | KPSS | Conclusie |
|---|---|---|
| verwerpt | verwerpt niet | stationair — beide eens |
| verwerpt niet | verwerpt | niet stationair — beide eens |
| verwerpt | verwerpt | **onduidelijk** — mogelijk trend of structuurbreuk |
| verwerpt niet | verwerpt niet | **onduidelijk** — te weinig informatie |

Een enkele toets kan falen door te weinig data. Twee onafhankelijke toetsen die
hetzelfde zeggen, is veel sterker bewijs.

> **Een eigenschap van KPSS die je moet kennen:** hij geeft af en toe een valse
> verwerping. Ik heb 40 reeksen zuivere ruis erdoor gehaald; bij een grens van 5%
> verwacht je 2 valse verwerpingen, en het waren er meer. Dat is vastgelegd in
> een test (`test_kpss_gives_occasional_false_alarms_on_pure_noise`). Een enkele
> KPSS-verwerping is dus geen hard bewijs — daarom kijken we altijd naar beide.

---

## De resultaten op jouw data

### Op niveau

| Reeks | ADF p | KPSS p | Oordeel |
|---|---|---|---|
| real_rate_10y | 0,518 | 0,010 | niet stationair |
| usd_broad_index | 0,755 | 0,010 | niet stationair |
| breakeven_inflation_10y | 0,006 | 0,010 | **onduidelijk** |
| fed_funds_rate | 0,849 | 0,010 | niet stationair |
| term_spread_10y2y | 0,390 | 0,010 | niet stationair |
| high_yield_spread | 0,057 | 0,010 | niet stationair |
| fed_balance_sheet | 0,758 | 0,010 | niet stationair |
| gold_futures | 0,997 | 0,010 | niet stationair |
| silver_futures | 0,772 | 0,010 | niet stationair |
| **vix** | **0,000** | **0,091** | **stationair** |
| sp500 | 1,000 | 0,010 | niet stationair |
| dxy | 0,399 | 0,010 | niet stationair |

**10 van de 12 zijn niet stationair.** Na transformatie (log-rendement of eerste
verschil) zijn alle 12 stationair.

### Twee uitkomsten die opvallen

**De VIX is stationair op niveau.** Dat is de enige reeks die je ongetransformeerd
mag gebruiken, en het is economisch logisch: volatiliteit keert terug naar een
gemiddelde. Een VIX van 80 is onhoudbaar, een VIX van 8 ook.

**De breakeven-inflatie is "onduidelijk".** De toetsen spreken elkaar tegen, en
dat is informatief. Nagekeken per periode:

| Periode | Gemiddelde | Min | Max |
|---|---|---|---|
| 2003–2007 | 2,34% | 1,57 | 2,76 |
| 2008–2012 | 2,01% | **0,04** | 2,64 |
| 2013–2019 | 1,90% | 1,18 | 2,59 |
| 2020–2022 | 2,12% | 0,50 | 3,02 |
| 2023–2026 | 2,30% | 2,02 | 2,52 |

Hij schommelt rond 2% — vandaar dat ADF stationariteit vindt. Maar in november
2008 kelderde hij naar **0,04%** toen de markt deflatie inprijsde. Die
crisisbreuken zorgen ervoor dat KPSS verwerpt.

Dat is precies wat je verwacht van een marktverwachting met een anker (het
Fed-inflatiedoel van 2%) dat in een crisis tijdelijk losschiet. Geen probleem,
maar wel iets om te benoemen.

---

## Wat dit kost

Differentiëren lost de schijnregressie op, maar heeft een prijs: **je gooit
informatie over het niveau weg.**

Een verband als "goud is duur ten opzichte van de reële rente, dus de prijs zal
terugvallen" kun je in verschillen niet meer zien. Je ziet alleen nog
dag-op-dag-bewegingen.

Er bestaat een techniek die dat wél kan: **cointegratie**. Die zoekt naar een
langetermijnevenwicht tussen niet-stationaire reeksen. Voor goud en de reële
rente is dat inhoudelijk interessant — het arbitrage-argument uit fase 1 gaat
immers over niveaus, niet over veranderingen.

Dat is een mogelijke uitbreiding, geen onderdeel van het basismodel. Ik noem het
omdat een interviewer ernaar kan vragen: "waarom geen cointegratie?" is een
redelijke vraag, en "daar heb ik bewust niet voor gekozen omdat..." is een beter
antwoord dan een verbaasde blik.

---

## Wat je nu kunt zeggen in een gesprek

> "Voordat ik ging regresseren heb ik alle reeksen op stationariteit getoetst met
> ADF en KPSS. Tien van de twaalf waren niet-stationair op niveau, dus alles gaat
> als rendement of eerste verschil het model in. Ik heb ook laten zien waarom dat
> nodig is: op niet-stationaire data vindt een regressie in 92% van de gevallen
> een significant verband in pure toevalsruis."

Dat laatste getal is jouw eigen meting, niet een verwijzing naar een leerboek.

---

## Wat er hierna komt in fase 2

We weten nu in welke **vorm** de data het model in mag. De volgende stappen:

1. **Correlaties tussen de drivers** — en vooral: zijn ze stabiel door de tijd?
   Mijn verwachting is dat de veilige-havenrelatie met de VIX instort in maart
   2020, toen goud werd verkocht omdat beleggers cash nodig hadden voor margin
   calls. Als dat zo is, is dat een belangrijke bevinding voor je hedge.
2. **Autocorrelatie van de goudrendementen** (ACF/PACF) — zit er
   voorspelbaarheid in de richting? Fase 1 zei nee, dit toetst het formeel.
3. **Multicollineariteit** — de reële rente en de breakeven-inflatie zijn
   definitorisch verbonden. Hoe erg is dat hier?

Daarna fase 3: de eigenlijke regressies, met walk-forward validatie tegen een
random walk.

Draaien: `python scripts/fase2_stationariteit.py`
