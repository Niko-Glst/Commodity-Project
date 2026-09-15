# Drie vragen beantwoord

1. Waar komt de 5-10%-vuistregel vandaan?
2. Wat betekent de rechte lijn in een QQ-plot?
3. Wat is het verschil tussen de t-verdeling en de normale verdeling?

Ze hangen samen: vraag 3 verklaart waarom vraag 1 een probleem is.

Figuren maken: `python scripts/uitleg_figuren.py`

---

## 1. Waar komt de 5-10%-vuistregel vandaan?

### Eerst: wat is marge eigenlijk?

Bij een futures-contract koop of verkoop je niet de goederen zelf, maar een
*afspraak* over de prijs. Je legt daarvoor niet de volle waarde neer — je stort
een onderpand. Dat heet **marge**.

Een COMEX-goudcontract is 100 troy ounce. Bij een goudprijs van $4.343 is dat:

```
100 × $4.343 = $434.300 notionele waarde
```

Zoveel geld heb je niet nodig. De beurs vraagt ongeveer 5% — zo'n $21.700 — als
**initial margin**: het bedrag dat op je rekening moet staan om te mogen
handelen.

### Waar de beurs die 5% op baseert

De beurs (CME) wil één ding: dat jouw verlies gedekt is tot ze je positie kunnen
sluiten. Dat kost hooguit een dag of twee. Ze rekenen dus uit hoeveel de prijs in
één à twee dagen kan bewegen, met een ruime marge, en dat wordt het
margepercentage.

**Daar komt de 5% vandaan.** Het is geen risicomodel voor jouw situatie, maar een
beursvereiste, afgeleid van kortetermijnvolatiliteit. En die wordt aangepast:
na een onrustige periode verhoogt de beurs de marge.

De extra 5% in "5 tot 10%" is een veiligheidsmarge die handelaren zelf
aanhouden, zodat ze niet bij de eerste tegenbeweging moeten bijstorten.

### Wat er gebeurt als de prijs tegen je in beweegt

Je hebt een **short** positie: je verdient als goud daalt, je verliest als het
stijgt.

Elke dag wordt je positie herrekend (*mark-to-market*). Stijgt goud 2%, dan gaat
$8.686 van je rekening af. Zakt je saldo onder de **maintenance margin**, dan
krijg je een **margin call**: bijstorten, of de beurs sluit je positie — vaak op
het slechtst denkbare moment.

Dat wil je voorkomen. Vandaar je vraag: hoeveel moet ik achterhouden?

### Wat de data zegt

Voor een short positie is het gevaar een *stijging*. Over 23 jaar goudhistorie:

| Horizon | 99%-grens | Ergste ooit |
|---|---|---|
| 1 dag | 3,0% | 9,0% |
| 1 week | 6,3% | 20,4% |
| 2 weken | 9,3% | 18,4% |
| 1 maand | 13,7% | 22,4% |
| 1 kwartaal | **23,7%** | **37,2%** |

Lees de middelste kolom als: in 99 van de 100 gevallen blijft de stijging
hieronder.

### Wat hier misgaat

**De vuistregel dekt alleen één dag.** Op een daghorizon is 5-10% ruim genoeg —
de 99%-grens is 3,0%. Maar jouw hedge loopt een kwartaal, en dan is de 99%-grens
**23,7%**. Ruim vier keer de 5%.

Twee kanttekeningen die je erbij moet maken:

1. **Je hebt niet het volle bedrag nodig.** Je hoeft alleen genoeg te hebben om
   bij te storten als het misgaat, niet om het hele verlies vooraf te dekken.
   Maar 5% als *buffer* voor een kwartaal is aantoonbaar te krap.
2. **Het getal hangt af van de marktomstandigheden.** Die 23,7% is een
   gemiddelde over 23 jaar. In een rustige markt is de werkelijke behoefte veel
   lager, in een crisis hoger.

Punt 2 is precies waar fase 4 over gaat. De vuistregel staat **vast**, terwijl de
volatiliteit verandert — en die verandering is voorspelbaar (bevinding 3). Een
buffer die meebeweegt is zowel veiliger als goedkoper: in rustige tijden houd je
minder dood kapitaal vast.

*Zie: `output/figures/12_margeregel.png`*

---

## 2. Wat betekent de rechte lijn in een QQ-plot?

### Wat de plot doet

Een QQ-plot beantwoordt: **volgt mijn data deze verdeling?**

Het recept:

1. Sorteer je waarnemingen van laag naar hoog.
2. Bereken voor elke positie wat je zou *verwachten* als de verdeling klopte.
   De kleinste van 9 waarnemingen hoort rond het 6%-punt te liggen, de middelste
   rond 50%.
3. Zet werkelijk (verticaal) tegen verwacht (horizontaal) uit.

### De lijn is geen model

Dit is de kern van je vraag. De streepjeslijn is **niet** een lijn die door de
punten is gefit. Hij zegt:

> "Als de verdeling perfect klopte, zouden alle punten hier liggen."

Werkelijk = verwacht, dus de lijn loopt onder 45 graden. Hij ligt er al voordat
je naar de data kijkt.

### Wat afwijkingen betekenen

| Waar | Betekenis |
|---|---|
| Punten **op** de lijn | De verdeling klopt |
| **Linksonder, onder de lijn** | De slechtste dagen zijn slechter dan voorspeld |
| **Rechtsboven, boven de lijn** | De beste dagen zijn beter dan voorspeld |

Samen geeft dat een **liggende S-vorm** — de handtekening van dikke staarten.

Voor jouw margevraag telt vooral de linkeronderhoek (of bij een short: de
rechterbovenhoek). Daar zitten de dagen die een margin call veroorzaken.

### Waarom dit beter werkt dan een histogram

In een histogram zijn de staarten vrijwel onzichtbaar: daar zitten maar een
handvol waarnemingen, dus de balkjes zijn nauwelijks hoger dan nul. In een
QQ-plot krijgt **elke waarneming een eigen punt**, dus juist de extreme dagen
zijn het best zichtbaar.

*Zie: `output/figures/10_qq_uitgelegd.png` — vier panelen, van simpel naar echt*

---

## 3. Wat is het verschil tussen de t-verdeling en de normale verdeling?

### Kort

Ze lijken sterk op elkaar in het midden. Het verschil zit volledig in de
**staarten**: de t-verdeling geeft extreme uitkomsten een veel grotere kans.

### De vrijheidsgraden

De t-verdeling heeft één instelknop: de **vrijheidsgraden** (df).

| df | Staarten |
|---|---|
| 2 | extreem dik |
| 4 | zeer dik |
| 10 | matig dik |
| 30+ | niet meer van normaal te onderscheiden |

Weinig vrijheidsgraden = dikke staarten. Bij oneindig veel vrijheidsgraden *is*
de t-verdeling de normale verdeling.

**Voor goud is df op 3,6 geschat** — dat is laag, dus dikke staarten.

### Waarom "vrijheidsgraden"?

De naam komt uit de oorsprong van de verdeling. William Gosset ontdekte hem in
1908 bij Guinness, waar hij bierkwaliteit testte met kleine steekproeven. Hij
publiceerde onder het pseudoniem "Student" omdat Guinness publicaties verbood —
vandaar *Student's t-distribution*.

Zijn probleem: bij een kleine steekproef ken je de werkelijke spreiding niet, je
schat hem. Die onzekerheid maakt extreme uitkomsten waarschijnlijker dan de
normale verdeling zegt. Hoe kleiner de steekproef, hoe minder vrijheidsgraden,
hoe dikker de staarten.

Wij gebruiken hem om een andere reden — niet vanwege een kleine steekproef, maar
omdat financiële rendementen nu eenmaal dikke staarten hebben. De vorm past; de
oorspronkelijke motivatie is hier niet van toepassing. Dat is eerlijk om te
zeggen in plaats van te doen alsof het hetzelfde is.

### Het verschil in getallen

Kans op een beweging groter dan:

| | Normale verdeling | t met df=3,6 | Factor |
|---|---|---|---|
| 2 sd | 1 op 22 dagen | 1 op 8 | 3× |
| 3 sd | 1 op 370 | 1 op 22 | 17× |
| 4 sd | 1 op 15.787 | 1 op 50 | 313× |
| 5 sd | 1 op 1.744.278 | 1 op 102 | **17.139×** |

Let op hoe snel dat oploopt. Bij 2 standaardafwijkingen is het verschil een
factor 3; bij 5 standaardafwijkingen een factor zeventienduizend.

### Het scherpste voorbeeld uit jouw data

Op 30 januari 2026 daalde goud **10,8%** op één dag. Dat is **9,9
standaardafwijkingen**.

Onder de normale verdeling is de kans daarop ongeveer 1 op
59.000.000.000.000.000.000.000 dagen. Het heelal bestaat pas zo'n 5 biljoen
dagen.

**De normale verdeling zegt dus: dit kan niet gebeuren. Het gebeurde vorig jaar.**

Dat is het hele argument in één zin.

### Waarom dit voor je marge uitmaakt

Je vraag is: hoeveel buffer heb ik nodig om met 99% zekerheid geen margin call te
krijgen?

Dat is per definitie een vraag over de staart. En daar zit de normale verdeling
er met een factor honderd tot duizend naast. Reken je met de klokvorm, dan komt
er een te laag bedrag uit — en dat merk je precies op de dag dat het misgaat.

*Zie: `output/figures/11_t_versus_normaal.png`*

---

## Hoe de drie samenhangen

1. De **QQ-plot** (vraag 2) is het gereedschap waarmee je ziet dat de normale
   verdeling niet past.
2. De **t-verdeling** (vraag 3) is wat er in plaats daarvan wél past.
3. Daardoor kun je de **vuistregel** (vraag 1) vervangen door een onderbouwd
   getal — en dat is fase 4.

---

## Wat je hiervan moet onthouden

Drie zinnen:

- De 5% is een **beursvereiste** voor één dag, geen risicomodel voor jouw
  kwartaalhedge.
- De lijn in een QQ-plot is **geen fit** maar "hier zouden de punten liggen als
  het klopte".
- De t-verdeling verschilt van de normale **alleen in de staarten** — en precies
  daar gaat een margeberekening over.
