# Fase 3: verslaat een regressiemodel een random walk?

Draaien: `python scripts/fase3_regressie.py`

**Het antwoord is nee.** Hieronder hoe dat is vastgesteld, en waarom dat het
juiste resultaat is in plaats van een mislukking.

---

## De opzet

Afhankelijke variabele: het dagelijkse log-rendement van goud.

Drivers (vier, bewust beperkt):

- reële rente (DFII10)
- brede dollarindex (DTWEXBGS)
- breakeven-inflatie (T10YIE)
- VIX

Zilver zit er níet in. Dat is geen macro-driver maar vrijwel hetzelfde product;
met een correlatie van 0,78 zou het de rest van het model verbergen.

---

## Stap 1: OLS met Newey-West standaardfouten

### Waarom die correctie nodig is

Gewone OLS-standaardfouten maken twee aannames die in deze data geschonden
worden:

1. **Constante variantie van de fouten.** Fase 1 liet zien dat volatiliteit
   clustert: in onrustige periodes zijn de fouten groter.
2. **Geen autocorrelatie** in de fouten.

Bij overtreding zijn de standaardfouten te klein en lijkt alles significanter
dan het is.

> **Belangrijk:** Newey-West repareert de *standaardfouten*, niet de
> coëfficiënten. Die blijven identiek. Het model wordt er niet beter van; je
> krijgt alleen een eerlijker beeld van de onzekerheid.

### De resultaten

5.139 dagen.

| Driver | Coëfficiënt | SE gewoon | SE Newey-West | t | p | VIF |
|---|---|---|---|---|---|---|
| reële rente | −0,03400 | 0,00296 | 0,00496 | −6,85 | 0,0000 | 1,07 |
| dollarindex | −1,37148 | 0,04568 | 0,08283 | −16,56 | 0,0000 | 1,11 |
| breakeven | −0,01784 | 0,00468 | 0,00826 | −2,16 | 0,0307 | 1,16 |
| VIX | +0,00024 | 0,00008 | 0,00014 | +1,76 | 0,0779 | 1,14 |

**De correctie scheelt een factor 1,66 tot 1,81.** Zonder Newey-West zou je de
onzekerheid met 66 tot 81 procent onderschatten. Dat is geen detail: de VIX gaat
er van "significant" naar "niet significant" (p = 0,078).

**R² = 0,186.** De vier drivers verklaren 18,6% van de dagelijkse goudbeweging.
Dat is meer dan de losse correlaties uit fase 2 suggereerden, omdat de
dollarindex het grootste deel doet.

**VIF maximaal 1,16** — geen multicollineariteit. Dat komt doordat we bewust
maar één dollarmaatstaf hebben meegenomen; met DXY erbij zou dit oplopen (fase 2
bevinding 6).

### Eén teken klopt niet

| Driver | Verwacht | Gevonden | Klopt? |
|---|---|---|---|
| reële rente | − | − | ja |
| dollarindex | − | − | ja |
| **breakeven** | **+** | **−** | **nee** |
| VIX | + | + | ja (niet significant) |

De breakeven-inflatie heeft het verkeerde teken en is *wel* significant. Dat is
niet weg te wuiven als ruis.

De verklaring zit in fase 2 bevinding 3: de breakeven-correlatie met goud
**wisselt van teken door de tijd** (van −0,28 tot +0,36). Het vaste coëfficiënt
is dus een gemiddelde van tegengestelde regimes — en dat gemiddelde kan
makkelijk de verkeerde kant op uitvallen zonder iets over de economie te zeggen.

Dit is precies waarom we het verwachte teken vooraf opschreven.

---

## Stap 2: walk-forward validatie — de toets die telt

### De opzet

- Begin met 1.000 dagen trainingsdata
- Schat de modellen, voorspel de volgende dag
- Schuif 21 dagen op, herhaal — 145 vensters
- **Nooit** trainen op data van na de voorspelde dag

De drivers worden met **één dag gelagd**. Dat volgt uit fase 1: FRED publiceert
de waarde van dag *t* pas op werkdag *t+1*. Het rendement van vandaag verklaren
uit de rente van vandaag zou look-ahead bias zijn.

### De uitkomst

> **Deze tabel is gecorrigeerd.** Een eerdere versie rapporteerde een
> directional accuracy van 43,8% en een R² van −0,0396. Die kwamen uit een
> aanroep met `horizon=1, step=21`, waardoor er 145 LOSSE dagen werden
> voorspeld in plaats van 3.024 aaneengesloten. Zie
> [AUDIT.md](../AUDIT.md) sectie 9 en de uitleg onderaan.

| Model | RMSE | Directional accuracy | R² out-of-sample | vs. benchmark |
|---|---|---|---|---|
| **random_walk** | **0,010834** | n.v.t. | +0,0000 | — |
| historisch | 0,010834 | 52,2% | −0,0001 | +0,01% |
| **ols** | **0,010774** | **51,9%** | **+0,0110** | **−0,55%** |
| **ridge** | **0,010774** | **51,9%** | **+0,0110** | **−0,55%** |

*N = 3.024 out-of-sample dagen, 144 vensters, 2014-2026.*

Drie dingen om te lezen:

**OLS is 0,55% beter dan nul voorspellen — maar niet significant.** De
Diebold-Mariano-toets geeft p = 0,170. Bij 3.024 dagen is een verschil van
0,55% in RMSE niet van toeval te onderscheiden.

**Directional accuracy 51,9%** — nét boven de munt. Exact: 1.562 van 3.024
dagen correct. De binomiaaltoets tegen 50% geeft **p = 0,072**: niet
significant op 5%.

**Het "historisch" model doet niets.** Het gemiddelde dagrendement is ongeveer
0,04%, dus dat model voorspelt vrijwel nul. Het verschil met de random walk is
afrondingsruis.

**De conclusie is dus niet "slechter dan een munt" maar "niet te
onderscheiden van nul".** Dat is een zwakkere uitspraak dan de oude tabel
suggereerde, en een eerlijkere.

### Is het verschil significant? (Diebold-Mariano)

Een lagere RMSE kan toeval zijn. Deze toets kijkt of het verschil in
voorspelfouten systematisch is, met Newey-West standaardfouten omdat de
verschilreeks zelf geautocorreleerd is.

| Vergelijking | Statistiek | p-waarde | Conclusie |
|---|---|---|---|
| OLS vs. random walk | −1,37 | 0,170 | geen significant verschil |
| Ridge vs. random walk | −1,37 | 0,170 | geen significant verschil |

Het teken is nu negatief (OLS heeft een iets LAGERE fout), maar de p-waarde
is vrijwel hetzelfde als voorheen. Dat is het hele punt: de toets zei ook in
de oude versie al "geen significant verschil", en die conclusie staat
overeind. Alleen de richting van het niet-significante verschil is omgeklapt.

**Dat de p-waarde niet veranderde terwijl het teken wel omsloeg, is het
duidelijkste signaal dat er in beide gevallen ruis gemeten werd.**

---

## Stap 3: zijn langere horizonnen beter voorspelbaar?

Fase 2 vond zwakke dagcorrelaties, maar dat sluit sterkere verbanden op maand-
of kwartaalbasis niet uit: ruis dempt uit bij aggregatie terwijl een echt
signaal blijft staan.

Met **niet-overlappende** vensters, zodat de waarnemingen onafhankelijk zijn:

| Horizon | n | R² in-sample | R² out-of-sample |
|---|---|---|---|
| 1 dag | 5.139 | +0,0135 | +0,0045 |
| 1 week | 1.024 | +0,0123 | −0,0067 |
| 1 maand | 246 | +0,0228 | **+0,0727** |
| 1 kwartaal | 82 | +0,0358 | **+0,0801** |

De out-of-sample R² loopt op van 0,5% naar 8%. Dat is economisch logisch: het
arbitrage-argument over de reële rente gaat over maanden, niet over dagen.

**Maar let op de kolom n.** Bij een kwartaalhorizon houd je 82 waarnemingen over
voor 4 drivers. Dat is te weinig om een verschil van 8% verklaarde variantie te
onderscheiden van toeval.

De eerlijke formulering is dus: **op dagbasis geen signaal; op kwartaalbasis
mogelijk wel, maar te weinig data om het vast te stellen.** Dat is een aanwijzing
voor vervolgonderzoek, geen conclusie.

---

## Waarom dit het juiste resultaat is

Dit is wat de efficiënte-markthypothese voorspelt. Waren goudrendementen uit
publieke macro-data te voorspellen, dan zou iedereen die dat wist erop handelen
tot het verband verdween.

Een project dat correct concludeert dat er weinig signaal is, is verdedigbaar.
Een project met een mooie in-sample R² die out-of-sample instort, is dat niet.

### Het contrast dat het hele project samenvat

| | Voorspelbaar? |
|---|---|
| **Richting** van de goudprijs | **Nee** — R² out-of-sample negatief |
| **Grootte** van de beweging | **Ja** — autocorrelatie volatiliteit 0,98 |

Dat contrast is de kern. En het goede nieuws voor jouw vraag: **voor een
margeberekening heb je de richting niet nodig.** Je moet weten hoe groot de
beweging kan zijn, niet welke kant hij op gaat.

Daarom bouwt fase 4 op GARCH: dat modelleert de voorspelbare volatiliteit, niet
de onvoorspelbare richting.

---

## Hoe je dit in een gesprek brengt

> "Ik heb een OLS-model gebouwd met vier macro-drivers, met Newey-West
> standaardfouten omdat de residuen clusteren — die correctie blies de
> standaardfouten met 66 tot 81 procent op, en één driver ging daardoor van
> significant naar niet-significant. In-sample haalde het model een R² van 18,6%.
>
> Maar walk-forward gevalideerd tegen een random walk is het 2% *slechter* op
> RMSE, met een negatieve out-of-sample R². Diebold-Mariano zegt: geen
> significant verschil. Het model voegt dus niets toe aan 'morgen is als
> vandaag'.
>
> Dat is wat je verwacht in een efficiënte markt. Wat wél voorspelbaar is, is de
> volatiliteit — en dat is precies wat ik nodig heb voor de margevraag waar het
> project om begon."

---

## Wat er methodologisch in zit

Voor de volledigheid, omdat dit de onderdelen zijn die een interviewer kan
natrekken:

| Onderdeel | Waarom |
|---|---|
| Newey-West standaardfouten | residuen zijn heteroskedastisch en geautocorreleerd |
| Drivers met één dag gelagd | FRED publiceert met een werkdag vertraging |
| Walk-forward, nooit vooruit trainen | anders look-ahead bias |
| Random walk als benchmark | de nulhypothese die je moet verslaan |
| Out-of-sample R² tegen nul | meet direct of het model iets toevoegt |
| Diebold-Mariano | onderscheidt een echt verschil van toeval |
| VIF per driver | maakt multicollineariteit zichtbaar |
| Niet-overlappende vensters bij horizonnen | anders lijkt n groter dan hij is |
| Ridge naast OLS | test of regularisatie de instabiliteit opvangt |

### Twee positieve controles in de tests

De validatie zelf is getest, want "het model verslaat de benchmark niet" is
waardeloos als je niet weet dat je code een signaal *zou* vinden:

- `test_walk_forward_finds_a_real_signal` — bouwt data waarin de driver van
  gisteren het rendement van vandaag voorspelt. De validatie moet dat vinden
  (R² out-of-sample > 0,5, directional accuracy > 80%).
- `test_walk_forward_lags_the_drivers` — bouwt een driver die alleen
  *gelijktijdig* samenhangt. Die mag out-of-sample niets opleveren, want dan
  zou de lag niet werken.

Plus een test die de reeks na dag 1500 door onzin vervangt en controleert dat de
voorspellingen van vóór dat punt **identiek** blijven. Veranderen ze, dan traint
het model op toekomstige data.

---

## Iets wat ik onderweg verkeerd had

Bij het schrijven van de tests ging ik ervan uit dat clusterende volatiliteit
altijd tot grotere Newey-West standaardfouten leidt. Dat is niet zo.

Newey-West blaast de fouten alleen op als **zowel de driver als de fout**
gecorreleerd zijn over de tijd. Bij een witte-ruis-driver heffen de kruistermen
elkaar op, ook al zijn de fouten sterk geautocorreleerd en heteroskedastisch.

Gemeten op verzonnen data:

| Driver | Inflatiefactor |
|---|---|
| witte ruis | 0,95 (geen effect) |
| persistent (AR 0,95) | 2,21 |

In de echte data zijn rentes en de dollarindex sterk persistent, en daar komt de
gemeten 1,66–1,81 dus vandaan. Beide gevallen staan nu als test vastgelegd.

---

## En iets wat ik veel langer verkeerd had

De getallen bovenaan deze pagina zijn gecorrigeerd. De oude versie zei
directional accuracy **43,8%** en R² **−0,0396**, en daarop rustte de hele
claim "richting is niet voorspelbaar". Die getallen waren verkeerd.

### Wat er misging

De aanroep stond hier als:

```python
walk_forward_validate(target, drivers, min_train=1000, step=21)
```

Zonder `horizon` neemt de functie `horizon=1`. Dat betekent: voorspel één dag,
spring dan 21 dagen vooruit, voorspel weer één dag. Je houdt **145 losse
dagen** over, met tussen elke twee dagen een gat van drie weken.

Met `horizon=21, step=21` sluiten de vensters wél aan en krijg je **3.024
aaneengesloten dagen**.

| | n | R² | Accuracy | vs. random walk |
|---|---|---|---|---|
| `horizon=1, step=21` (fout) | 145 | −0,0396 | 43,8% | +1,96% |
| `horizon=21, step=21` (goed) | 3.024 | +0,0110 | 51,9% | −0,55% |

### Waarom het zo lang onopgemerkt bleef

Drie redenen, en ze zijn alle drie leerzaam:

1. **Niets crashte.** De functie deed precies wat hem gevraagd werd.
2. **Het getal was plausibel.** Een R² van −0,04 past perfect bij het verhaal
   dat ik aan het vertellen was. Een resultaat dat je verwacht, controleer je
   minder streng — en dat is precies waarom ik het niet zag.
3. **Het reproduceerde perfect.** Elke keer dat ik dit script draaide kwam er
   −0,0396 uit. Ik beschouwde dat als bevestiging, maar reproduceerbaarheid en
   correctheid zijn verschillende dingen. Een script dat zijn eigen fout
   betrouwbaar herhaalt, slaagt voor de eerste toets en zakt voor de tweede.

Het kwam pas boven toen `scripts/freeze_results.py` als onafhankelijke
implementatie andere getallen gaf. **Twee implementaties die het oneens zijn,
vinden fouten die één implementatie met honderd runs niet vindt.**

Ironisch detail: deze fout stond al in
[WALKTHROUGH.md](WALKTHROUGH.md) beschreven als voorbeeld van een bug die
*gevonden en opgelost* was. Hij was opgelost in `pipeline.py` en nooit in dit
script — en dit script maakte alle gepubliceerde fase 3-getallen.

### Wat de conclusie nu is

Richting blijft onvoorspelbaar, maar om een andere reden dan ik dacht:

- **oud:** "43,8% accuracy, slechter dan een munt opgooien"
- **nieuw:** "51,9% accuracy, p = 0,072; R² +0,011, Diebold-Mariano p = 0,170
  — niet te onderscheiden van nul"

De oude getallen **overdreven** het negatieve resultaat. Dat is in zekere zin
erger dan een te positief resultaat: ik had een sterkere conclusie dan mijn
data toestond, en die kwam uit een bug.

### Wat ik eraan veranderd heb

`walk_forward_validate` weigert nu `horizon < step` met een foutmelding, tenzij
je expliciet `allow_gaps=True` meegeeft. De standaardwaarde van `horizon` is
gelijkgetrokken met die van `step`. Drie tests leggen dat vast, waaronder één
die controleert dat de standaardinstellingen een doorlopende reeks opleveren.
