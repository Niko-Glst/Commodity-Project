# Wat R² betekent, en waarom hij verandert

Dit document beantwoordt één vraag die makkelijk verwarrend is: er staan drie
verschillende R²-getallen in dit project (18,6% — 1,7% — −4%), en ze lijken met
elkaar in tegenspraak. Dat zijn ze niet. Ze meten verschillende dingen.

---

## Wat R² is

R² antwoordt op: **hoeveel van de beweging verklaart mijn model?**

Het is een breuk van twee getallen:

```
R² = 1 − RSS / TSS
```

- **TSS** (*total sum of squares*) — de totale beweging van goud: de som van
  (rendement − gemiddelde)², over alle dagen
- **RSS** (*residual sum of squares*) — wat het model **niet** verklaart: de som
  van de voorspelfouten²

Met jouw echte data:

```
TSS = 0,7129    de totale beweging
RSS = 0,5801    wat onverklaard blijft

R² = 1 − 0,5801/0,7129 = 1 − 0,8136 = 0,1864
```

Het model verklaart dus 18,6% en laat 81,4% onverklaard.

### Waarom kwadraten?

Twee redenen. Fouten kunnen positief of negatief zijn; zonder kwadrateren
zouden ze elkaar opheffen. En kwadrateren laat grote fouten zwaarder wegen — een
fout van 2% telt vier keer zo zwaar als een fout van 1%.

Dat is dezelfde reden als bij de standaardafwijking uit fase 1.

---

## De drie R²-getallen in dit project

Hier zit de verwarring, en hier is hij weg:

| # | Wat wordt gemeten | R² | Bruikbaar om te voorspellen? |
|---|---|---|---|
| 1 | goud vandaag ~ drivers **vandaag** | **+0,1864** | **nee** |
| 2 | goud vandaag ~ drivers **gisteren** | **+0,0174** | ja, maar nauwelijks signaal |
| 3 | idem, gemeten op **ongeziene data** | **−0,0055** | nee, slechter dan niets |

Elke stap omlaag heeft een concrete oorzaak. Die twee oorzaken zijn het hele
verhaal van fase 3.

---

## Sprong 1: van 18,6% naar 1,7% — het lagen van de drivers

### Wat er gebeurt

Model 1 verklaart het goudrendement van vandaag uit de driververanderingen van
**vandaag**. Dat werkt goed (18,6%), maar het is **onbruikbaar om te
voorspellen**: de dollarkoers van vandaag ken je pas aan het eind van vandaag.
Op het moment dat je een beslissing neemt, heb je dat getal niet.

Model 2 gebruikt de drivers van **gisteren**. Dat is de eerlijke vraag: kan ik
met informatie die ik écht heb, voorspellen wat goud morgen doet?

**Het antwoord: R² zakt van 0,1864 naar 0,0174. Een factor 11.**

### Waarom dat zo'n groot verschil is

Goud en de dollar bewegen op **dezelfde dag** samen. Dat is grotendeels een
mechanisch verband: goud wordt in dollars genoteerd, dus als de dollar 1% stijgt
daalt de dollarprijs van goud bijna automatisch mee.

Maar dat verband is **gelijktijdig, niet voorspellend**. De dollar van gisteren
zegt vrijwel niets over goud vandaag, want die informatie is al in de prijs
verwerkt. Dat is de efficiënte markt in actie.

### Waarom dit geen technisch detail is

Er is ook een harde reden om te lagen die los staat van de economie: **FRED
publiceert de waarde van dag *t* pas op werkdag *t+1*.** Je *kon* de rente van
vandaag niet kennen. Een model dat hem gebruikt, is look-ahead bias — dat was
bevinding uit fase 1.

> **Dit is de fout die de meeste "werkende" modellen maakt.** Rapporteer de
> gelijktijdige R² van 18,6% en het ziet eruit als een model. Maar je kunt er
> niks mee: op het beslismoment heb je de input niet.

---

## Sprong 2: van 1,7% naar −0,55% — in-sample versus out-of-sample

### Wat er gebeurt

**In-sample** betekent: schat het model op alle data, en meet hoe goed het past
op **diezelfde** data. Het model heeft de antwoorden al gezien.

**Out-of-sample** betekent: schat op de eerste 70%, en meet op de laatste 30% —
data die het model nooit heeft gezien.

```
in-sample      R² = +0,0174
out-of-sample  R² = −0,0055
```

### Wat een negatieve R² betekent

Dit lijkt onmogelijk, maar het is heel concreet:

```
RSS = 0,1656   de fouten van het model
TSS = 0,1647   de fouten van "voorspel altijd nul"
```

**RSS is groter dan TSS.** Je voorspelfouten zijn dus groter dan wanneer je
niets had gedaan. Het model maakt het actief slechter.

Let op dat de noemer hier anders is dan bij het gewone R². Bij out-of-sample
meten we tegen **"voorspel nul"** (de random walk), niet tegen het gemiddelde.
Dat is bewust: de vraag is of het model iets toevoegt aan "morgen is als
vandaag".

### Waarom in-sample altijd te optimistisch is

Een regressie zoekt de coëfficiënten die de fouten op de **beschikbare** data zo
klein mogelijk maken. Een deel van wat hij vindt is echt verband; een deel is
toevallig patroon in juist die dagen.

Dat tweede deel — de **overfit** — helpt niet op nieuwe data en schaadt zelfs.
Met vier drivers en 5.000 waarnemingen is het effect klein (1,7% → −0,55%), maar
het is er.

Bij een model met veel variabelen en weinig data wordt het dramatisch. Dat is
ook waarom fase 3 waarschuwt bij de kwartaalhorizon: 82 waarnemingen voor 4
drivers geeft een in-sample R² van 3,6% die grotendeels overfit kan zijn.

---

## Nog een reden waarom R² kan veranderen: de steekproef

Een derde oorzaak die makkelijk over het hoofd wordt gezien.

In fase 2 vond ik dat de brede dollarindex los 16,0% verklaart. In fase 3 haalt
het hele model met vier drivers 18,6%. Waarom voegen drie extra drivers maar 2,6
procentpunt toe?

Twee redenen:

1. **De dollar doet het meeste werk.** De andere drivers voegen weinig toe, wat
   consistent is met fase 2: reële rente 4,1%, breakeven 0,2%, VIX 0,0%.
2. **Het aantal waarnemingen verschilt.** Fase 2 rekende per driver op alle
   overlappende dagen; fase 3 heeft alleen de 5.139 dagen waarop *alle vier* de
   drivers beschikbaar zijn. Andere steekproef, ander getal.

Dat laatste is een algemene les: **R²-waarden zijn alleen vergelijkbaar op
dezelfde steekproef.** Daarom rekent
[`compare_models()`](../src/goldmodel/models.py) altijd op dezelfde rijen.

---

## Aangepaste R² (adjusted R²)

Nog één variant die je in de output ziet staan.

Het probleem: **R² stijgt altijd als je een variabele toevoegt**, ook een
volstrekt nutteloze. Dat is een rekenkundige eigenschap van OLS, geen bevinding.

Aangepaste R² straft extra variabelen af:

```
R²_adj = 1 − (1 − R²) · (n − 1)/(n − k − 1)
```

waarbij *n* het aantal waarnemingen is en *k* het aantal drivers.

Voegt een driver minder toe dan hij "kost" aan vrijheidsgraden, dan gaat de
aangepaste R² **omlaag**. Dat is precies wat gebeurde bij de
crack-spread-verkenning:

| Model | R² | Aangepaste R² |
|---|---|---|
| goud ~ olie + crack | 0,0280 | **0,0276** |
| goud ~ olie + crack + breakeven | 0,0280 | **0,0274** |

De gewone R² blijft gelijk, de aangepaste zakt. Dat is het signaal dat de extra
driver niets toevoegt.

**Vuistregel: bij het vergelijken van modellen met een verschillend aantal
variabelen kijk je naar de aangepaste R², niet naar de gewone.**

### Maar de aangepaste R² is geen harde bewaker

Getest op de echte data door kolommen pure toevalsgetallen toe te voegen:

| Model | R² | Aangepaste R² |
|---|---|---|
| vier echte drivers | 0,1864 | 0,1858 |
| + 1 kolom ruis | 0,1868 | 0,1860 |
| + 10 kolommen ruis | 0,1891 | 0,1869 |
| + 50 kolommen ruis | 0,1964 | **0,1879** |
| + 200 kolommen ruis | **0,2192** | 0,1869 |

De gewone R² stijgt bij élke toevoeging — 200 kolommen ruis "verklaren"
schijnbaar meer dan de vier echte drivers. Dat is pure overfit.

Maar de aangepaste R² *stijgt ook nog* tot 50 kolommen, en zakt pas daarna. Bij
5.139 waarnemingen kost een variabele zo weinig aan vrijheidsgraden dat de straf
klein is.

**De echte les: aangepaste R² is een correctie, geen oplossing.** Het enige
betrouwbare antwoord tegen overfit is out-of-sample meten. Daarom rust fase 3
daarop en niet op een van deze twee getallen.

---

## Samengevat

| Soort R² | Wat het meet | Val |
|---|---|---|
| **Gelijktijdig** | bewogen ze samen op dezelfde dag | je kent de input niet op het beslismoment |
| **Gelagd, in-sample** | past het model op bekende data | bevat overfit |
| **Gelagd, out-of-sample** | werkt het op nieuwe data | *dit is de enige die telt* |
| **Aangepast** | gecorrigeerd voor aantal variabelen | gebruik bij modellen vergelijken |

En de getallen uit dit project:

```
18,6%   gelijktijdig          -> ziet eruit als een model
 1,7%   gelagd, in-sample     -> bijna niets over
-0,55%  gelagd, out-of-sample -> slechter dan niets doen
```

**Dat is geen tegenspraak maar een afpelling.** Elke stap haalt een vorm van
zelfbedrog weg, en wat overblijft is het eerlijke antwoord.

---

## Wat je hiermee in een gesprek kunt

> "Mijn model haalt 18,6% R², maar dat is de gelijktijdige regressie en die is
> onbruikbaar — op het beslismoment ken ik de drivers van vandaag niet, en FRED
> publiceert ze pas de volgende werkdag. Met de drivers gelagd zakt het naar
> 1,7%, en out-of-sample naar −0,55%. Dat laatste getal betekent dat het model
> slechter voorspelt dan altijd nul voorspellen."

Iemand die dat kan uitleggen, heeft het begrepen. Iemand die alleen "18,6%"
noemt, heeft het niet.

*Zelf nagaan: `python scripts/uitleg_r2.py`*
