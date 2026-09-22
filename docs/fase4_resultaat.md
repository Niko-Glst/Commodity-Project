# Fase 4: het antwoord op de margevraag

Draaien:

```powershell
python scripts/fase4_simulatie.py     # de simulatie en het antwoord
python scripts/fase4_figuren.py       # figuren + Kupiec-validatie
```

---

## Wat fase 4 doet, en waarom dat mag na fase 3

Fase 3 concludeerde: de **richting** van goud is onvoorspelbaar. Toch gaan we
simuleren. Dat is geen tegenspraak.

**Een simulatie voorspelt de richting ook niet.** Elk gesimuleerd pad is puur
toeval — de ene helft gaat omhoog, de andere omlaag. Wat we wél gebruiken is de
**grootte** van de bewegingen, en die is aantoonbaar voorspelbaar
(autocorrelatie van de volatiliteit 0,98).

Voor de margevraag is dat precies genoeg. Je hoeft niet te weten of goud stijgt
of daalt; je moet weten hoe groot de tegenbeweging kan zijn.

### Wat we per pad meten

Niet de eindwaarde. Voor een margin call telt de grootste **tussentijdse**
tegenbeweging: een pad dat halverwege 30% tegen je in staat en daarna terugkomt,
heeft je wel degelijk uitgestopt.

Dat heet de **maximum adverse excursion**.

---

## De input, uit de data geschat

| Parameter | Waarde | Herkomst |
|---|---|---|
| gemiddeld dagrendement | +0,0426% | 5.957 handelsdagen |
| dagelijkse volatiliteit | 1,1539% | idem (18,3% op jaarbasis) |
| t-vrijheidsgraden | 3,54 | QQ-plot fase 1 |
| GARCH alpha | 0,0363 | schok van gisteren |
| GARCH beta | 0,9593 | onrust van gisteren |
| **persistentie** | **0,9956** | alpha + beta |
| halfwaardetijd schok | **156 dagen** | volgt uit persistentie |

Die halfwaardetijd maakt bevinding 3 van fase 1 concreet: na 156 dagen is de
helft van een volatiliteitspiek weggeëbd. Dat is de clustering, nu als getal in
een model.

### Twee keuzes die het resultaat bepalen

**1. De drift staat op nul.**

Het gemiddelde dagrendement is +0,043%, oftewel +2,7% per kwartaal. Nemen we dat
mee, dan drijft elke prijs omhoog — en bij een short is omhoog de verkeerde kant.
De 99%-VaR stijgt er met ruim 3 procentpunt van.

Waarom we hem weglaten:

- Fase 3 toonde dat de richting onvoorspelbaar is. Een 23-jaars gemiddelde als
  voorspelling gebruiken is precies de aanname die daar weerlegd werd.
- De standaardfout van dat gemiddelde is 0,015% — een derde van de schatting
  zelf.
- Een drift inbouwen is stilletjes toch een puntvoorspelling doen, en dat belooft
  dit project expliciet niet.

**2. Er is een validatiestap die de simulatie naast de werkelijkheid zet.**

Zie hieronder. Dat is de belangrijkste toevoeging van fase 4.

---

## De drie modellen

| Model | 99%-VaN (kwartaal) | Repareert |
|---|---|---|
| GBM normaal | 26,0% | niets — de referentie |
| GBM t (df 3,5) | 26,4% | dikke staarten (fase 1) |
| **GARCH t** | **34,5%** | ook clustering (fase 1) |

*VaN = de grootste tussentijdse tegenbeweging, als percentage van de notionele
waarde.*

---

## De eerlijkheidscheck: simulatie tegenover werkelijkheid

Een simulatie produceert altijd getallen. Voordat we er iets mee doen, zetten we
ze naast wat er écht gebeurde in 23 jaar.

| Bron | p50 | p95 | p99 | Afwijking p99 |
|---|---|---|---|---|
| **historisch (echte data)** | 6,7% | 21,3% | **29,3%** | — |
| GBM normaal | 5,7% | 18,9% | 26,0% | **−3,3 pp** |
| GBM t | 5,3% | 18,6% | 26,4% | **−3,0 pp** |
| GARCH t | 6,1% | 22,3% | 34,5% | **+5,2 pp** |

**De constante-volatiliteitsmodellen onderschatten de staart; GARCH overschat
hem.** De werkelijkheid ligt ertussen.

### Waarom GARCH te hoog uitkomt

De geschatte persistentie is 0,9956 — bijna 1. Bij zo'n waarde is het model
bijna niet-stationair en is het langetermijnniveau slecht bepaald: GARCH schat de
langetermijnvolatiliteit op **20,8%** waar de data **18,3%** zegt. Over 63 dagen
tikt dat verschil flink aan.

Dat is geen bug maar een bevinding. Het eerlijke antwoord is dus een
**bandbreedte** en niet één getal.

---

## De Kupiec-validatie

Belooft het model 99%, en levert het dat ook? Zeg je 99%, dan verwacht je dat 1%
van de vensters de grens doorbreekt.

We toetsen over meerdere horizonnen, en dat is geen willekeur: bij een
kwartaalhorizon houd je met 23 jaar data maar 78 niet-overlappende vensters over,
en verwacht je slechts 0,8 overschrijdingen. De toets heeft dan vrijwel geen
kracht.

| Horizon | Vensters | Model | Overschrijdingen | Verwacht | p-waarde |
|---|---|---|---|---|---|
| **10 dagen** | **495** | GBM normaal | 9 | 5,0 | 0,101 |
| | | GBM t | 7 | 5,0 | 0,383 |
| | | **GARCH t** | **5** | **5,0** | **0,982** |
| 21 dagen | 236 | GBM normaal | 5 | 2,4 | 0,133 |
| | | GBM t | 4 | 2,4 | 0,329 |
| | | GARCH t | 4 | 2,4 | 0,329 |
| 63 dagen | 78 | GBM normaal | 1 | 0,8 | 0,810 |
| | | GBM t | 1 | 0,8 | 0,810 |
| | | GARCH t | 2 | 0,8 | 0,246 |

### Wat je hier wel en niet uit mag concluderen

**Wel:** alle drie de modellen halen de toets. Geen enkel model belooft
aantoonbaar meer zekerheid dan het levert.

**Wel:** GARCH is het best **gekalibreerd**. Op de scherpste toets (10 dagen, 495
vensters) verwacht je 5 overschrijdingen; GARCH komt op precies 5, GBM-t op 7,
GBM-normaal op 9.

**Niet:** *"het normale model is verworpen."* Dat had ik eerst wel opgeschreven,
op basis van een run met 1.500 paden waar p = 0,045 uitkwam. Bij 3.000 paden is
het 0,101, en bij een ander toevalszaad ook. **Die p-waarde lag pal op de
0,05-grens en flipte met het zaad: het was ruis in de simulatie zelf, geen
bevinding.** Het aantal paden staat nu op 3.000 zodat de uitkomst van de *toets*
niet afhangt van de ruis in de *simulatie*.

### De echte les over deze toets

De Kupiec-toets is hier **zwak**. Zelfs bij 495 vensters verwacht je maar 5
overschrijdingen, en het verschil tussen 5 en 9 is statistisch niet hard te
maken. Om de modellen echt te scheiden zou je meer dan 23 jaar data nodig hebben.

Dat is een eerlijke beperking, geen fout in de opzet — en precies waarom de
vergelijking met de historische verdeling er óók staat. Die is informatiever dan
een toets die bijna niets kan afwijzen.

---

## Het antwoord

Bij een goudprijs van $4.379 is één contract (100 ounce) **$437.940** notioneel.

| Zekerheid | Buffer | In dollars |
|---|---|---|
| 50% | 6,1% | $26.554 |
| 90% | 17,9% | $78.520 |
| 95% | 22,3% | $97.751 |
| **99%** | **34,5%** | **$151.108** |
| 99,9% | 57,6% | $252.443 |

En de **Expected Shortfall** bij 99%: als je die grens tóch doorbreekt, is het
gemiddelde tekort 44,9% ($196.478). Dat getal repareert de bekende zwakte van
VaR — een 99%-VaN van 34,5% is verenigbaar met 36% in het slechtste procent, maar
ook met 80%. ES vertelt je welke van de twee het is.

### Vergelijking met je vuistregel

| | Bedrag | Dekt |
|---|---|---|
| jouw 5% | $21.897 | 44% van de paden |
| jouw 10% | $43.794 | 69% van de paden |
| model bij 99% | $151.108 | 99% |

### De bandbreedte, eerlijk gerapporteerd

Gegeven dat de modellen uiteenlopen:

- **ondergrens** (constante volatiliteit): ~26%
- **historisch gemeten**: 29,3%
- **bovengrens** (GARCH, best gekalibreerd): 34,5%

Voor een buffer is de bovengrens de conservatieve keuze — en GARCH is óók het
model dat de Kupiec-toets het best doorstaat. Maar je moet weten *dat* hij
conservatief is, en waarom.

---

## De belangrijke nuance die alles relativeert

Dit is een **liquiditeitsbehoefte, geen verlies.**

Bij een hedge stijgt je fysieke goud evenveel als je futures verliezen; je
vermogen blijft intact. Je hebt het geld alleen nodig **op het moment** dat de
broker belt.

Een kredietlijn tegen je onderpand doet dus hetzelfde werk als cash, en kost je
geen rendement. Dat maakt 34,5% "toegang tot" een heel ander vereiste dan 34,5%
"in cash".

---

## Wat fase 4 heeft opgeleverd

1. **Een onderbouwd getal** in plaats van een vuistregel: 34,5% voor 99%
   zekerheid over een kwartaal, met 26% als ondergrens.
2. **Het staartrisico gequantificeerd**: het verschil van 8,5 procentpunt tussen
   het normale model en GARCH is wat de klokvorm niet ziet.
3. **Een getal dat meebeweegt met de markt**, doordat GARCH begint bij de
   volatiliteit van vandaag (21,8%) in plaats van het gemiddelde van 23 jaar
   (18,3%).
4. **Een toets die vaststelt of die 99% ook echt 99% is** — en het eerlijke
   verhaal over hoe zwak die toets is bij deze hoeveelheid data.

---

## De volledige keten

| Fase | Bevinding | Gevolg |
|---|---|---|
| 1 | dikke staarten (kurtosis 6,5) | t-verdeling nodig |
| 1 | volatiliteit clustert (ACF 0,98) | GARCH nodig |
| 1 | geen vast ritme | geen Fourier |
| 2 | verbanden zwak en instabiel | geen vertrouwen in drivers |
| 3 | richting onvoorspelbaar (R² out-of-sample −0,04) | niet op richting mikken |
| 4 | grootte wél voorspelbaar | margebuffer berekenen |

**Elke keuze in fase 4 is onderbouwd met een meting uit een eerdere fase.** Dat
is wat het verdedigbaar maakt — niet dat het antwoord indrukwekkend is, maar dat
je van elk getal kunt zeggen waar het vandaan komt.

---

## De figuren

| Figuur | Wat het toont |
|---|---|
| `19_fan_chart.png` | de band van mogelijke paden — een verdeling, geen lijn |
| `20_modellen_vergeleken.png` | simulatie naast de werkelijke historie |
| `21_buffercurve.png` | buffer tegen zekerheid; de afweging zichtbaar |
| `22_kupiec_validatie.png` | haalt het model de toets, en hoe sterk is die toets |
