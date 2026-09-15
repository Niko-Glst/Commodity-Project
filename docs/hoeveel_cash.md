# Hoeveel cash heb ik echt nodig?

Het korte antwoord op "moet ik 30% achterhouden": **nee**. Dat getal klopte niet,
en de vraag zelf mist een belangrijk onderscheid.

Dit document corrigeert allebei.

---

## Correctie 1: mijn getal was te hoog

In de vorige tabel stond 30,3% voor een kwartaal. Dat was fout gerekend.

Ik telde **alle stortingen bij elkaar op** over het hele kwartaal. Maar stort je
in week 2 bij, en zit de prijs in week 5 weer mee, dan staat dat geld gewoon
terug op je rekening. Die tweede storting hoefde dus niet uit verse cash te
komen.

Wat je echt wilt weten is de **piek van de netto-inleg**: hoeveel geld zat er op
het diepste punt in deze positie?

| Horizon | Mediaan | 95% | 99% | Ergste ooit |
|---|---|---|---|---|
| 1 week | 0,0% | 0,0% | 2,2% | 6,9% |
| 1 maand | 0,0% | 5,9% | 10,2% | 14,5% |
| **1 kwartaal** | **1,7%** | **16,3%** | **24,8%** | 28,5% |

Als percentage van de notionele waarde, **bovenop** de initial margin die je toch
al gestort had.

Dat is fors lager dan wat ik eerst rapporteerde. De mediaan zakte van 6,9% naar
1,7%.

---

## Correctie 2: een hedge is geen losse short

Dit is het belangrijkere punt, en het verandert hoe je naar dat getal moet
kijken.

Alle berekeningen hierboven gaan over een **kale short**: je verkoopt goudfutures
en verder niets. Stijgt goud, dan verlies je, punt.

Maar jij hedget. Dat betekent dat je de short aanhoudt *tegenover* iets anders —
fysiek goud, een voorraad, of een andere long exposure. En dan gebeurt er iets
anders:

| | Goud stijgt 25% |
|---|---|
| Je short futures | −25% (verlies, direct cash) |
| Je onderliggende positie | +25% (winst, meestal niet liquide) |
| **Netto vermogen** | **≈ 0** |

**Je verliest geen geld. Je hebt een timingprobleem.**

De futures rekenen dagelijks af in cash. Je fysieke goud niet — dat wordt meer
waard op papier, maar daar kun je de margin call niet mee betalen.

### Waarom dat de vraag verandert

Die 24,8% is dus geen verlies dat je moet kunnen dragen. Het is **liquiditeit die
je op het juiste moment beschikbaar moet hebben**, terwijl je vermogen intact
blijft.

Dat opent oplossingen die bij een echt verlies niet bestaan:

- **Een kredietlijn** tegen je fysieke goud als onderpand. Je hoeft de cash niet
  te bezitten, alleen te kunnen opvragen.
- **Deels liquide aanhouden.** Een ETF of een deel van je positie dat je snel
  kunt verkopen om marge te voldoen.
- **Kleiner hedgen.** Dek 70% van je exposure in plaats van 100%; dan is je
  margebehoefte navenant lager.
- **Gespreid doorrollen** in plaats van één groot contract.

Bij een kale short heb je die opties niet — daar is het verlies echt.

---

## Dus: hoeveel?

Het eerlijke antwoord heeft drie lagen.

### Als je een kale short hebt

Dan is 24,8% voor een kwartaal het getal bij 99% zekerheid, en dat is veel. Je
zou je moeten afvragen of een kwartaal vasthouden wel verstandig is.

### Als je hedget (jouw geval)

Dan heb je **toegang tot** 24,8% nodig, niet per se 24,8% in cash op een
spaarrekening. Een kredietlijn tegen je onderliggende positie doet hetzelfde werk
en kost je geen rendement.

### Als je een lagere zekerheid accepteert

| Zekerheid | Kwartaal | Betekenis |
|---|---|---|
| 50% | 1,7% | de helft van de tijd genoeg |
| 95% | 16,3% | 1 op 20 keer tekort |
| 99% | 24,8% | 1 op 100 keer tekort |

Let op hoe scheef dat loopt. Van 50% naar 95% kost je 14,6 procentpunt; van 95%
naar 99% nog eens 8,5. Die laatste stap is duur, en of hij het waard is hangt af
van wat er gebeurt als je tekortkomt.

Komt een margin call jou uit op een kredietlijn? Dan is 95% ruim voldoende. Word
je gedwongen uitgestopt en valt je hele hedge weg? Dan wil je 99% of hoger.

---

## Wat je huidige 5-10% wel en niet dekt

| Horizon | 5% dekt | 10% dekt | 15% dekt |
|---|---|---|---|
| 1 week | 99,5% | 100% | 100% |
| 1 maand | 94,1% | 98,3% | 100% |
| **1 kwartaal** | **68,1%** | **86,1%** | 94,7% |

**Voor korte periodes is je vuistregel prima.** Voor een week dekt 5% al 99,5%
van de gevallen.

Voor een kwartaal wordt het anders: 5% dekt maar tweederde van de gevallen, en
zelfs 10% laat je in ruim 1 op de 7 gevallen zonder buffer zitten.

Of dat erg is, hangt af van wat je dan doet. Heb je een kredietlijn achter de
hand, dan is het een ongemak. Heb je die niet, dan is het het einde van je hedge
op het slechtst denkbare moment.

---

## De kanttekening bij al deze getallen

Dit zijn **historische** cijfers: ze kennen alleen scenario's die echt gebeurd
zijn. De ergste 23 jaar zeggen niets over volgend jaar.

Ook zijn het **gemiddelden over de hele periode**. In een rustige markt is de
werkelijke behoefte veel lager dan 24,8%, in een crisis hoger. Een vast
percentage — of het nu 5% of 25% is — negeert dat.

Fase 4 lost beide op: simuleren met een t-verdeling (ook ongeziene scenario's) en
met GARCH (een buffer die past bij de markt van vandaag).

---

## Samengevat

1. Mijn 30,3% was te hoog; de juiste berekening geeft **24,8%** bij 99%
   zekerheid over een kwartaal.
2. Voor een **hedge** is dat geen verlies maar een **liquiditeitsbehoefte** — je
   vermogen blijft intact, je hebt alleen cash nodig op het juiste moment.
3. Daarom telt "toegang tot" meer dan "bezitten": een kredietlijn tegen je
   onderliggende positie doet hetzelfde werk.
4. Je huidige 5-10% is prima voor korte horizonnen en te krap voor een heel
   kwartaal — maar hoeveel dat uitmaakt hangt af van je alternatieven.
