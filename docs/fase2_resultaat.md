# Fase 2: wat hebben we geleerd?

Fase 2 had drie stappen. Alle drie zijn nu af.

Draaien: `python scripts/fase2_stationariteit.py` en
`python scripts/fase2_correlaties.py`

---

## Bevinding 1: de data mag alleen als verandering het model in

Op **prijsniveaus** vindt een regressie in **92% van de gevallen** een
"significant" verband in pure toevalsruis. Op **veranderingen** is dat 4% —
precies wat het hoort te zijn.

Tien van je twaalf reeksen zijn niet-stationair op niveau; alle twaalf zijn het
wel na transformatie.

*Uitleg vanaf nul: [adf_kpss_vanaf_nul.md](adf_kpss_vanaf_nul.md)*

---

## Bevinding 2: drie drivers werken, de rest niet

Correlatie met het dagelijkse goudrendement, en wat elke driver los verklaart:

| Driver | Verwacht teken | Gevonden | Klopt? | Verklaart |
|---|---|---|---|---|
| zilver | + | **+0,784** | ja | **61,4%** |
| DXY (dollar) | − | **−0,404** | ja | **16,3%** |
| brede dollarindex | − | **−0,400** | ja | **16,0%** |
| reële rente | − | **−0,204** | ja | **4,1%** |
| fed funds rate | − | +0,049 | nee | 0,2% |
| high-yield spread | + | −0,048 | nee | 0,2% |
| breakeven-inflatie | + | +0,047 | ja | 0,2% |
| S&P 500 | ? | +0,028 | n.v.t. | 0,1% |
| VIX | + | −0,017 | nee | 0,0% |
| Fed-balans | + | −0,004 | nee | 0,0% |
| rentecurve | + | +0,002 | ja | 0,0% |

**De drie theoretisch belangrijkste drivers kloppen met de verwachting.** Zilver
beweegt sterk mee (het is deels hetzelfde metaal), de dollar beweegt tegen goud
in, en de reële rente ook — precies het arbitrage-argument uit fase 1.

### Over de vier "foute" tekens

Vier drivers hebben een ander teken dan verwacht. Maar kijk naar de laatste
kolom: ze verklaren allemaal **0,0% tot 0,2%**. Dat is geen weerlegging van de
theorie, dat is ruis. Bij bijna 6.000 waarnemingen wordt een correlatie van
0,03 al "significant", terwijl hij niets betekent.

Dat onderscheid is precies waarom we het verwachte teken vooraf opschreven: nu
kun je zeggen *"vier tekens weken af, maar alle vier verwaarloosbaar klein"* in
plaats van achteraf een verhaal te verzinnen.

### En de belangrijkste beperking

**Zelfs de sterkste macro-driver verklaart maar 16% van de dagelijkse
goudbeweging.** (Zilver laat ik buiten beschouwing — dat is geen macro-driver
maar vrijwel hetzelfde product.)

Dat is niet een tekortkoming van de data. Dat is de werkelijkheid: dagelijkse
goudbewegingen zijn voor het overgrote deel niet uit macro-data te verklaren.

*Figuur: `output/figures/17_correlaties.png`*

---

## Bevinding 3: de verbanden zijn niet stabiel — dit is de belangrijkste

Voortschrijdende correlatie met goud, venster van één jaar:

| Driver | Gemiddeld | Min | Max | Spreiding | Wisselt teken? |
|---|---|---|---|---|---|
| S&P 500 | +0,021 | −0,333 | +0,430 | 0,763 | **ja** |
| VIX | −0,001 | −0,382 | +0,305 | 0,686 | **ja** |
| breakeven-inflatie | +0,030 | −0,281 | +0,357 | 0,638 | **ja** |
| reële rente | −0,246 | −0,558 | +0,042 | 0,600 | **ja** |
| brede dollarindex | −0,429 | −0,648 | −0,086 | 0,562 | nee |

**Vier van de vijf drivers wisselen van teken door de tijd.** In sommige
periodes beweegt goud mét een driver mee, in andere periodes ertegen in.

### Waarom dit zo belangrijk is

Een regressie schat één vast coëfficiënt per driver. Wisselt het echte verband
van teken, dan is dat coëfficiënt **een gemiddelde van tegengestelde regimes —
een getal dat in geen enkele periode klopt.**

Alleen de dollar houdt consistent hetzelfde teken. En dat is ook de driver met
de sterkste verklaring: goud wordt in dollars genoteerd, dus er zit een deels
mechanisch verband in. Dat is stabieler dan een gedragsverband.

*Figuur: `output/figures/18_rolling_correlaties.png` — vergelijk paneel 2
(dollar, blijft onder nul) met paneel 5 (S&P 500, slingert heen en weer)*

---

## Bevinding 4: goud is op dagbasis géén veilige haven

Dit ging tegen mijn eigen verwachting in, en het resultaat is scherper dan wat
ik dacht te vinden.

Ik verwachtte dat het veilige-havenverband met de VIX zou **instorten** in maart
2020, toen beleggers goud verkochten voor cash. Gemeten per periode:

| Periode | Correlatie goud–VIX |
|---|---|
| 2003–2007 | −0,031 |
| financiële crisis 2008–2009 | +0,010 |
| 2010–2019 | +0,009 |
| covid-jaar 2020 | −0,065 |
| covid-crash (8 weken) | −0,069 |
| 2021–2026 | −0,072 |
| **hele periode** | **−0,024** |

**Het verband is niet ingestort — het was er nooit.** In elke subperiode is de
correlatie vrijwel nul.

Dat is een sterkere conclusie dan "de hedge faalt in een crisis": op **dagbasis**
is goud helemaal geen veilige haven tegen aandelenvolatiliteit. Het
veilige-havenverhaal gaat blijkbaar over langere horizonnen of over andere
soorten stress dan wat de VIX meet.

**Voor je hedge:** reken niet op een negatief verband met aandelen op dagbasis.
Dat is er niet.

---

## Bevinding 5: de richting is niet voorspelbaar uit het verleden

Autocorrelatie van goudrendementen, vertraging 1 tot 10 dagen. Twee van de tien
vallen buiten de toevalsgrens (dag 6 en 7), maar de sterkste is **0,0368**.

Gekwadrateerd verklaart dat **0,14%** van de beweging van morgen.

Statistisch aantoonbaar, praktisch waardeloos. Met 6.000 waarnemingen wordt
bijna alles significant — en dit is precies het onderscheid tussen "significant"
en "bruikbaar" dat je in een gesprek moet kunnen maken.

Dit bevestigt formeel wat je in fase 1 al zag: **de richting is onvoorspelbaar,
de grootte niet.**

---

## Bevinding 6: sommige drivers dubbelen elkaar

Paren met een correlatie boven 0,5:

| Driver A | Driver B | Correlatie |
|---|---|---|
| brede dollarindex | DXY | **+0,737** |
| VIX | S&P 500 | **−0,809** |
| high-yield spread | S&P 500 | −0,628 |
| high-yield spread | VIX | +0,556 |

Beide voorspelde probleemparen uit `config.py` komen uit. De VIX–S&P-correlatie
van −0,81 was te verwachten: **de VIX is letterlijk afgeleid van S&P-opties**,
dus dat is bijna een identiteit.

Dat heet **multicollineariteit**. Het gevolg: het model kan niet uitmaken welke
van twee gecorreleerde drivers het werk doet, dus de losse coëfficiënten worden
onbetrouwbaar — grote standaardfouten en tekens die omslaan bij kleine
wijzigingen in de data.

*Figuur: `output/figures/19_drivers_onderling.png`*

---

## Wat dit samen betekent

Zes bevindingen, en ze wijzen allemaal dezelfde kant op:

1. Data mag alleen als verandering het model in
2. Zelfs de beste macro-driver verklaart maar 16%
3. Vier van de vijf verbanden wisselen van teken door de tijd
4. Goud is op dagbasis geen veilige haven
5. De richting is niet voorspelbaar uit het verleden
6. Enkele drivers dubbelen elkaar

**Dit is een ongemakkelijke uitkomst, en precies daarom waardevol.** Je hebt nu
onderbouwd waarom je *niet* verwacht dat een regressiemodel goudrendementen kan
voorspellen. Dat is een sterkere positie dan een model presenteren dat mooi
lijkt maar niet houdbaar is.

---

## Hoe je dit in een gesprek brengt

> "In fase 2 heb ik de verbanden tussen goud en de macro-drivers onderzocht. De
> drie theoretisch belangrijkste drivers kloppen qua teken: de dollar en de reële
> rente bewegen tegen goud in, zoals het arbitrage-argument voorspelt. Maar
> zelfs de sterkste verklaart maar 16% van de dagelijkse beweging, en vier van de
> vijf verbanden wisselen van teken door de tijd. Daarom verwacht ik niet dat een
> regressie een random walk verslaat — en dat ga ik in fase 3 formeel toetsen in
> plaats van aannemen."

Dat is een antwoord dat laat zien dat je de data hebt laten spreken.

---

## Naar fase 3

Fase 2 leverde de nulhypothese: **goudrendementen zijn nauwelijks voorspelbaar.**
Fase 3 toetst dat formeel.

### Wat fase 3 gaat doen

**1. OLS met Newey-West standaardfouten**

Een regressie van het goudrendement op de drivers. Newey-West is nodig omdat
gewone standaardfouten twee aannames maken die hier geschonden worden:
constante variantie (nee — volatiliteit clustert, bevinding uit fase 1) en geen
autocorrelatie in de fouten. Zonder correctie zijn de standaardfouten te klein
en lijkt alles significanter dan het is.

**2. Walk-forward validatie tegen een random walk**

De kern van fase 3. Train op een venster, voorspel het volgende, schuif op —
nooit trainen op data die na de voorspelde periode ligt. En vergelijk met de
naïeve benchmark: "morgen is als vandaag".

**Verslaat het model die niet, dan is het geen model.**

**3. Ridge-regressie voor de multicollineariteit**

Ridge verdeelt het gewicht over gecorreleerde drivers in plaats van willekeurig
te kiezen. Dat lost het probleem uit bevinding 6 gedeeltelijk op.

**4. VAR voor wederzijdse beïnvloeding**

Een regressie veronderstelt dat de drivers goud beïnvloeden en niet omgekeerd.
Bij de dollar is dat discutabel. VAR behandelt alle reeksen symmetrisch.

### Mijn verwachting

Op basis van fase 2: **het model verslaat de random walk niet op dagbasis.** Als
dat zo blijkt, is dat het resultaat en zo rapporteren we het.

Wat wél kan werken is een langere horizon. De correlaties zijn zwak op dagbasis,
maar dat sluit niet uit dat ze op maand- of kwartaalbasis sterker zijn. Dat
toetsen we.

### Wat er daarna nog ligt

Eén ding uit fase 2 verdient nog aandacht voordat fase 4 begint: de
**instabiliteit** van de verbanden. Als vier van de vijf drivers van teken
wisselen, is een model met vaste coëfficiënten misschien het verkeerde
gereedschap. Een alternatief is een model dat per regime andere coëfficiënten
toestaat. Dat is een uitbreiding, geen basismodel — maar het is de logische
vervolgvraag op bevinding 3.
