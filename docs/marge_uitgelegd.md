# Hoe marge werkt bij een futures-positie

Twee vragen beantwoord:

1. Je betaalt maar 5% — hoe werkt die dynamiek precies?
2. Wat betekent "de 99%-grens"?

Zelf doorlopen: `python scripts/uitleg_marge.py`

---

## Deel 1: wat je eigenlijk koopt

Een COMEX-goudcontract is **100 troy ounce**. Bij een goudprijs van $4.343:

```
100 ounce × $4.343 = $434.300
```

Dat heet de **notionele waarde**. Dit bedrag betaal je *niet*. Het is alleen de
maatstaf waarover je winst en verlies wordt berekend.

Om de positie te openen stort je de **initial margin**, ongeveer 5%:

```
5% × $434.300 ≈ $21.700
```

Belangrijk: dit is **geen aanbetaling en geen kostenpost**. Het geld blijft van
jou. Het staat alleen vast als onderpand, en je krijgt het volledig terug als je
de positie zonder verlies sluit.

### De hefboom

Je hebt dus voor $434.300 aan goud in beweging met $21.700 op je rekening. Dat
is een hefboom van **20×**.

Daar zit meteen het risico. Beweegt goud 1%, dan is dat $4.343 winst of verlies.
Op een inleg van $21.700 is dat **20% van je geld — in één dag**.

---

## Deel 2: de dynamiek, stap voor stap

Elke handelsdag gebeurt hetzelfde:

### Stap 1 — Mark-to-market

De beurs herrekent je positie tegen de slotkoers. Beweegt de prijs tegen je in,
dan gaat dat bedrag **die dag** van je rekening af.

Dit is het punt dat mensen het vaakst verkeerd hebben: het is **geen papieren
verlies** dat je kunt uitzitten. Het geld verdwijnt echt, elke dag opnieuw.

### Stap 2 — Controle op de ondergrens

Er is een **maintenance margin**: een ondergrens, meestal rond 90% van de
initial margin. Blijft je saldo daarboven, dan gebeurt er niets.

### Stap 3 — De margin call

Zakt je saldo eronder, dan belt je broker: bijstorten, meestal binnen één dag.

Let op een detail dat vaak verrast: **je moet aanvullen tot de initial margin,
niet tot de ondergrens**. Een margin call vraagt dus altijd méér dan het tekort
dat je op dat moment hebt.

### Stap 4 — Als je niet stort

De broker sluit je positie gedwongen. Je verlies wordt definitief, en dat gebeurt
meestal op het slechtste moment: precies wanneer de markt tegen je in is
doorgeschoten.

> **Daar is je cash-buffer voor.** Niet om het verlies te voorkomen — dat gebeurt
> sowieso — maar om te kunnen bijstorten, zodat je niet wordt uitgestopt terwijl
> je hedge nog loopt.

### Een extra draai die vaak vergeten wordt

De margevereiste is een *percentage van de notionele waarde*, en die beweegt mee
met de prijs. Bij een short positie werkt dat **dubbel** tegen je: goud stijgt,
dus je verliest geld **én** de eis wordt hoger.

---

## Deel 3: een echt voorbeeld — september 2008

De zwaarste periode voor een short goudpositie in de hele reeks. Lehman Brothers
viel om op 15 september 2008, en beleggers vluchtten naar goud.

Stel je gaat op 11 september short in 1 contract. Instapprijs $741,30, notionele
waarde $74.130, initial margin $3.706.

| Datum | Prijs | Dagresultaat | Saldo | Ondergrens | Bijstorten |
|---|---|---|---|---|---|
| 12 sep | 760 | −1.900 | 1.806 | 3.421 | **1.995** |
| 15 sep | 783 | −2.280 | 1.522 | 3.524 | **2.394** |
| 16 sep | 776 | +660 | 4.575 | 3.494 | 0 |
| 17 sep | 847 | −7.010 | **−2.435** | 3.810 | **6.668** |
| 18 sep | 893 | −4.610 | −377 | 4.017 | **4.841** |
| 19 sep | 861 | +3.210 | 7.674 | 3.873 | 0 |
| 22 sep | 904 | −4.330 | 3.343 | 4.068 | **1.176** |
| 23–25 sep | 878 | — | 7.140 | 3.950 | 0 |

Kijk naar 17 september: je saldo werd **negatief** (−2.435). Je stond niet alleen
op nul, je stond in het rood, en moest $6.668 storten om weer aan de eis te
voldoen.

### Twee getallen die je uit elkaar moet houden

**1. Wat je beschikbaar moest hebben: $16.260** (21,9% van de notionele waarde)

Dit is wat je buffer moet dekken. Kon je dit niet ophoesten, dan was je
uitgestopt.

**2. Wat je uiteindelijk kwijt bent: $13.640** (18,4%)

Lager, want een deel van wat je stortte staat nog op je rekening ($7.140). Dat
krijg je terug bij sluiten.

Merk op dat getal 2 exact de prijsbeweging is: goud steeg 18,4%, en dat is wat je
verloor. Alles daarboven was tijdelijk.

**Voor jouw vraag telt getal 1.** Je wilt niet uitgestopt worden, en daarvoor
moet het geld *er zijn* op het moment dat de broker belt — ook al krijg je een
deel later terug.

### Wat dit zegt over de vuistregel

| Buffer | Bedrag | Genoeg? |
|---|---|---|
| 5% | $3.706 | Nee |
| 10% | $7.413 | Nee |
| Werkelijk nodig | $16.260 | 21,9% |

Maar let op: **dit is de ergste periode uit 23 jaar.** Altijd 22% aanhouden is
overdreven duur — dat kapitaal doet de rest van de tijd niets. Dat is precies de
afweging waar fase 4 over gaat.

---

## Deel 4: wat betekent "de 99%-grens"?

De 99%-grens is **geen voorspelling**. Het is een uitspraak over hoe vaak iets
voorkomt.

### Hoe je hem berekent

1. Neem alle 10-daagse periodes uit 23 jaar historie (dat zijn er 5.944).
2. Bereken voor elke periode hoeveel de prijs bewoog.
3. Sorteer die uitkomsten van laag naar hoog.
4. Pak de waarde waar 99% onder ligt.

### Wat eruit komt

| Percentiel | Stijging | Betekenis |
|---|---|---|
| 50% | 0,5% | de helft van de periodes blijft hieronder |
| 90% | 4,7% | 9 van de 10 |
| 95% | 6,0% | 19 van de 20 |
| **99%** | **9,3%** | **99 van de 100** |
| 99,9% | 15,0% | 999 van de 1000 |
| maximum | 18,4% | de ergste in 23 jaar |

"De 99%-grens is 9,3%" betekent dus: **in 99 van de 100 tiendaagse periodes bleef
de stijging onder 9,3%.** In 1 van de 100 was hij groter.

### Waarom 99% en niet 100%?

Omdat 100% niet bestaat. Er is altijd een scenario dat erger is dan wat je ooit
hebt gezien — dat is precies wat dikke staarten betekenen.

Je kiest dus bewust een zekerheidsniveau:

- **95%** — goedkoper, maar 1 op 20 keer kom je tekort
- **99%** — 1 op 100
- **99,9%** — veel duurder; dat kapitaal doet de rest van de tijd niets

Dat is een **afweging, geen technisch detail**. Meer zekerheid kost geld.

### De valkuil bij deze berekening

Deze percentages komen uit de historie. Ze kennen alleen scenario's die *echt
gebeurd zijn*. De ergste tien dagen uit 23 jaar zeggen niets over wat er volgend
jaar kan gebeuren.

Daarom simuleren we in fase 4 met een **t-verdeling**: die genereert ook
scenario's die nog niet voorkwamen, maar wel passen bij hoe goud zich gedraagt.
Dat is het verschil tussen *"wat gebeurde er"* en *"wat kán er gebeuren"*.

---

## Deel 5: hoeveel buffer had je echt nodig?

Nu doorgerekend over de hele historie: schuif een venster over de data, simuleer
de margerekening dag voor dag, kijk hoeveel je had moeten bijstorten.

Dit is dus niet "hoeveel bewoog de prijs" maar "hoeveel cash had ik nodig" —
inclusief het feit dat de margevereiste meestijgt.

> **Deze tabel is gecorrigeerd.** Een eerdere versie telde alle stortingen over
> de hele periode op, ook als het geld onderweg weer terugkwam. Zie
> [hoeveel_cash.md](hoeveel_cash.md) voor de uitleg.

| Horizon | Mediaan | 95% | 99% | Ergste |
|---|---|---|---|---|
| 1 week | 0,0% | 0,0% | 2,2% | 6,9% |
| 1 maand | 0,0% | 5,9% | 10,2% | 14,5% |
| **1 kwartaal** | **1,7%** | **16,3%** | **24,8%** | 28,5% |

Als percentage van de notionele waarde, bovenop de initial margin.

### Lees de mediaan en de 99%-grens naast elkaar

Voor een kwartaal: in de helft van de gevallen heb je **1,7%** nodig. In het
slechtste procent **24,8%**. Dat is een factor 15 verschil.

**Dat verschil ís het probleem met een vast percentage.** Je houdt bijna altijd
te veel aan — kapitaal dat niets opbrengt — en precies wanneer het ertoe doet te
weinig.

**Belangrijk voorbehoud:** deze cijfers gelden voor een **kale short**. Hedge je
tegenover fysiek goud, dan is dit geen verlies maar een liquiditeitsbehoefte —
je onderliggende positie wint immers evenveel. Zie
[hoeveel_cash.md](hoeveel_cash.md).

---

## Samenvatting

1. Je betaalt niet de volle waarde maar ~5% als **onderpand**. Dat geld blijft
   van jou.
2. Elke dag wordt je positie herrekend. Verlies gaat **die dag** van je rekening
   — geen papieren verlies.
3. Zakt je saldo onder de ondergrens, dan moet je aanvullen tot de **initial**
   margin. Doe je dat niet, dan word je gedwongen uitgestopt.
4. Je cash-buffer is er om te kunnen **bijstorten**, niet om het verlies te
   voorkomen.
5. De 99%-grens betekent: **in 99 van de 100 gevallen was dit genoeg.** Niet
   100%, want dat bestaat niet.
6. Een vast percentage negeert dat de markt verandert. Fase 4 maakt de buffer
   dynamisch.

---

## Wat fase 4 hieraan toevoegt

De tabel hierboven is een **historische simulatie**: eerlijk, maar hij kent
alleen het verleden. Fase 4 doet drie dingen extra:

1. **Simuleren met een t-verdeling** — ook scenario's die nog niet gebeurden
2. **Volatiliteit laten meebewegen** (GARCH) — een buffer die past bij de markt
   van vandaag, niet bij het gemiddelde van 23 jaar
3. **Toetsen of het klopt** (Kupiec) — zeg je 99%, dan moet het ook echt 99%
   zijn
