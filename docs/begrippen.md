# Begrippenlijst

Elk begrip dat in dit project gebruikt wordt, met uitleg, de formule waar die
verheldert, en een link om verder te lezen. In de volgorde waarin je ze
tegenkomt.

De Investopedia-links zijn Engelstalig. Waar het Nederlandse en Engelse woord
verschillen, staat de Engelse term erbij — dat is ook wat je in een
sollicitatiegesprek zult horen.

---

## Verdeling en rendementen

### Log-rendement (*log return*, *continuously compounded return*)

De natuurlijke logaritme van de prijsverhouding tussen twee dagen:

```
r_t = ln(P_t / P_{t-1})
```

Twee redenen om dit boven het procentuele rendement te verkiezen:

1. **Optelbaar over tijd.** Het rendement over een week is de som van de vijf
   dagrendementen. Bij procenten moet je vermenigvuldigen.
2. **Symmetrisch.** Een prijs die halveert en weer verdubbelt geeft −50% en
   +100% in procenten, maar −0,69 en +0,69 in logs. Dezelfde beweging, en dat
   zie je terug in het getal.

Bij kleine dagbewegingen zijn ze bijna gelijk: een log-rendement van 0,01
komt overeen met 1,005%.

→ [Investopedia: Continuously Compounded Return](https://www.investopedia.com/terms/c/continuouscompounding.asp)

---

### Standaardafwijking (*standard deviation*)

De gemiddelde afstand tot het gemiddelde, in dezelfde eenheid als de data. In
de financiële wereld heet dit **volatiliteit** en het is dé maat voor risico.

```
σ = √( Σ(x − x̄)² / (n − 1) )
```

Goud heeft een dagelijkse standaardafwijking van ongeveer 1,15%. Op jaarbasis
wordt dat ongeveer 18%, want je vermenigvuldigt met √252 (het aantal
handelsdagen in een jaar). Die wortelregel volgt uit de aanname dat
dagrendementen onafhankelijk zijn — en die aanname is niet helemaal juist,
zoals de volatiliteitsclustering laat zien.

→ [Investopedia: Standard Deviation](https://www.investopedia.com/terms/s/standarddeviation.asp) ·
[Volatility](https://www.investopedia.com/terms/v/volatility.asp)

---

### Standaardscore / z-score (*standard score*)

Hoeveel standaardafwijkingen een waarneming van het gemiddelde af ligt:

```
z = (x − x̄) / σ
```

Handig omdat het eenheden wegneemt: een z van 3 betekent hetzelfde bij goud
als bij de S&P 500, ongeacht hoe volatiel elk van beide is. Alle
staartanalyses in dit project rekenen met z-scores.

→ [Investopedia: Z-Score](https://www.investopedia.com/terms/z/zscore.asp)

---

### Normale verdeling (*normal distribution*, *Gaussian*)

De klokvorm. Volledig bepaald door twee getallen: gemiddelde en
standaardafwijking. Onder een normale verdeling geldt:

| Binnen | Percentage van de waarnemingen |
|---|---|
| ±1σ | 68,3% |
| ±2σ | 95,4% |
| ±3σ | 99,7% |
| ±4σ | 99,994% |

Die laatste twee regels zijn waar het bij ons misgaat. Onder normaliteit komt
een beweging groter dan 3σ in 0,27% van de dagen voor: in 5.949 handelsdagen
verwacht je er 16. Goud had er **78**.

De normale verdeling is populair omdat ze wiskundig handelbaar is, niet omdat
financiële rendementen haar volgen. Dat onderscheid is het halve verhaal van
dit project.

→ [Investopedia: Normal Distribution](https://www.investopedia.com/terms/n/normaldistribution.asp)

---

### Kurtosis (*kurtosis*)

**Wat het meet:** hoe extreem de uitschieters zijn. Niet hoe breed de
verdeling is — dat is de standaardafwijking — maar hoe zwaar de staarten
wegen.

**De berekening, stap voor stap:**

1. Neem elke waarneming en trek het gemiddelde eraf.
2. Deel door de standaardafwijking. Je hebt nu per dag een z-score.
3. Verhef elke z tot de **vierde** macht.
4. Neem het gemiddelde van al die vierde machten.

```
kurtosis = (1/n) · Σ z⁴
```

**Waarom de vierde macht?** Omdat die extremen enorm zwaar laat wegen:

| z | z⁴ |
|---|---|
| 1 | 1 |
| 2 | 16 |
| 3 | 81 |
| 4 | 256 |
| 6 | 1.296 |

Een dag van 4 standaardafwijkingen telt 256 keer zo zwaar mee als een gewone
dag. Kurtosis wordt daardoor vrijwel volledig bepaald door de zeldzaamste
waarnemingen. In onze data levert **1% van de dagen 73% van de kurtosis**
(zie figuur 2).

**Exces-kurtosis.** Voor een normale verdeling komt er precies 3 uit. Bijna
iedereen trekt die 3 eraf en rapporteert *exces-kurtosis*, zodat 0 "normaal"
betekent. Pandas doet dat automatisch: `.kurtosis()` geeft exces-kurtosis.
Let op: `scipy.stats.kurtosis()` heeft een parameter `fisher=True` (de
standaard) die hetzelfde doet — bij `fisher=False` krijg je het ruwe getal
inclusief die 3.

**Voor goud: 6,50.** Een verdeling met een exces-kurtosis van 6,5 heeft
staarten die substantieel dikker zijn dan normaal.

**Veelgemaakte fout:** kurtosis wordt vaak omschreven als "hoe spits de piek
is". Dat is misleidend. Het gaat om de staarten; de hoge piek is een
bijverschijnsel, omdat de kansmassa uit het middengebied naar zowel het
midden als de uiteinden verschuift.

→ [Investopedia: Kurtosis](https://www.investopedia.com/terms/k/kurtosis.asp) ·
[Excess Kurtosis](https://www.investopedia.com/terms/e/excesskurtosis.asp)

---

### Dikke staarten (*fat tails*, *leptokurtic*)

Een verdeling met meer extreme waarnemingen dan de normale verdeling
voorspelt. Formeel: exces-kurtosis > 0, ook wel *leptokurtisch*.

Waarom dit voor risico belangrijker is dan het gemiddelde: als je uitrekent
hoeveel geld je moet aanhouden om een slechte dag te overleven, gaat die
berekening volledig over de staart. Reken je met een normale verdeling, dan
komt er een te laag bedrag uit — en je merkt dat pas op de dag dat het misgaat.

Dit is geen nieuw inzicht. Benoît Mandelbrot beschreef het in 1963 voor
katoenprijzen, en het is sindsdien in vrijwel elke markt bevestigd.

→ [Investopedia: Fat Tail](https://www.investopedia.com/terms/f/fat-tail.asp) ·
[Tail Risk](https://www.investopedia.com/terms/t/tailrisk.asp)

---

### Scheefheid (*skewness*)

**Wat het meet:** aan welke kant de uitschieters zitten.

Zelfde recept als kurtosis, maar met de **derde** macht:

```
scheefheid = (1/n) · Σ z³
```

Het verschil tussen een oneven en een even macht is de hele clou:

| | derde macht | vierde macht |
|---|---|---|
| z = −2 | −8 | +16 |
| z = +2 | +8 | +16 |

Bij een oneven macht behoudt een negatieve afwijking zijn minteken, dus
positieve en negatieve uitschieters heffen elkaar op. Bij een symmetrische
verdeling komt er 0 uit. Bij een even macht valt het teken weg en telt alleen
de grootte.

Daarom: **scheefheid meet de richting, kurtosis de grootte.**

- Negatief = scheef naar links: de grote dalingen zijn extremer dan de grote
  stijgingen.
- Positief = scheef naar rechts.

**Voor goud: −0,53.** Goud valt harder dan het stijgt. Voor aandelen is dat
patroon nog sterker en er is een economische verklaring voor: paniek verspreidt
zich sneller dan optimisme, en gedwongen verkopen (margin calls, stop-losses)
versterken dalingen op een manier die bij stijgingen geen tegenhanger heeft.

→ [Investopedia: Skewness](https://www.investopedia.com/terms/s/skewness.asp)

---

### Momenten van een verdeling (*moments*)

Scheefheid en kurtosis horen bij een familie. Het n-de gestandaardiseerde
moment is het gemiddelde van zⁿ:

| Moment | Naam | Wat het beschrijft |
|---|---|---|
| 1e | gemiddelde | waar het centrum ligt |
| 2e | variantie | hoe breed |
| 3e | scheefheid | hoe scheef |
| 4e | kurtosis | hoe dik de staarten |

Handig om te weten dat het één systeem is: elk volgend moment weegt de
extremen zwaarder.

→ [Investopedia: Moment](https://www.investopedia.com/terms/m/moment.asp)

---

## Toetsen

### Jarque-Bera-toets (*Jarque-Bera test*)

Toetst of scheefheid en kurtosis samen verenigbaar zijn met een normale
verdeling. De toetsingsgrootheid combineert beide:

```
JB = (n/6) · ( S² + (K−3)²/4 )
```

waarbij S de scheefheid is en K de ruwe kurtosis. Zijn beide precies normaal
(S = 0, K = 3), dan is JB nul. Hoe verder ervandaan, hoe groter.

**Hoe je de uitkomst leest.** De **p-waarde** is de kans om zulke afwijkende
scheefheid en kurtosis te zien *als* de data werkelijk normaal verdeeld was.
Is die kans heel klein, dan verwerp je de aanname van normaliteit. De
gebruikelijke grens is 0,05.

Voor goud komt er `0.00e+00` uit — kleiner dan wat een computer met dubbele
precisie kan weergeven. Normaliteit is uitgesloten.

**Belangrijke nuance voor een gesprek:** bij 5.949 waarnemingen verwerpt deze
toets vrijwel altijd, ook bij minieme afwijkingen. Dat is een eigenschap van
toetsen op grote steekproeven: statistische significantie zegt dan weinig over
de *grootte* van het effect. De toets bevestigt hier wat de QQ-plot al laat
zien; overtuigend is de plot, niet de p-waarde.

→ [Investopedia: Jarque-Bera Test](https://www.investopedia.com/terms/j/jarqueberatest.asp) ·
[P-Value](https://www.investopedia.com/terms/p/p-value.asp)

---

### QQ-plot (*quantile-quantile plot*)

Zet de waargenomen kwantielen uit tegen de kwantielen die een theoretische
verdeling voorspelt. Een **kwantiel** is een grenswaarde: het 5%-kwantiel is
de waarde waaronder 5% van de waarnemingen ligt.

Volgt de data de verdeling, dan liggen alle punten op een rechte lijn.
Afwijkingen aan de uiteinden betekenen dat de staarten niet kloppen.

Dit is de beste diagnostiek voor staartgedrag die er is, en beter dan een
histogram: in een histogram zijn de staarten vrijwel onzichtbaar omdat er
weinig waarnemingen zitten, terwijl elke waarneming in een QQ-plot een eigen
punt krijgt.

**Het patroon in figuur 4** — punten die aan de linkerkant onder de lijn
duiken en aan de rechterkant erboven uitkomen, samen een liggende S — is de
klassieke handtekening van dikke staarten.

→ [Investopedia: Q-Q Plot](https://www.investopedia.com/terms/q/qqplot.asp)

---

### Autocorrelatie (*autocorrelation*, *serial correlation*)

De correlatie van een reeks met zichzelf, een aantal periodes verschoven. De
autocorrelatie bij vertraging 1 beantwoordt: zegt de waarde van vandaag iets
over die van morgen?

**Waarom het hier zo belangrijk is.** Figuur 5 zet twee autocorrelaties naast
elkaar en het contrast is het hele punt:

- **Rendementen zelf:** vrijwel nul, binnen de toevalsgrenzen. Of goud morgen
  stijgt of daalt, kun je niet afleiden uit vandaag. Dat is de
  efficiënte-markthypothese in beeld — en het is precies wat je zou moeten
  verwachten, want anders was er gratis geld te verdienen.
- **Absolute rendementen:** duidelijk positief en het blijft weken doorlopen.
  Of morgen een onrustige dag wordt, weet je vandaag wél.

Kortom: de **richting** is onvoorspelbaar, de **grootte** niet.

De stippellijnen in de figuur staan op ±1,96/√n. Dat is de bandbreedte
waarbinnen autocorrelaties vallen als er in werkelijkheid geen samenhang is.

→ [Investopedia: Autocorrelation](https://www.investopedia.com/terms/a/autocorrelation.asp) ·
[Efficient Market Hypothesis](https://www.investopedia.com/terms/e/efficientmarkethypothesis.asp)

---

### Volatiliteitsclustering (*volatility clustering*)

Grote bewegingen worden gevolgd door grote bewegingen, kleine door kleine —
ongeacht de richting. Mandelbrot beschreef het al in 1963.

Waarom dit voor jouw margevraag uitmaakt: je hebt niet één volatiliteit, maar
een die verandert. Reken je met het langjarig gemiddelde, dan onderschat je
het risico juist in de onrustige periodes — precies wanneer een margin call
dreigt. Dat is de reden dat fase 4 GARCH gebruikt.

→ [Investopedia: Volatility Clustering](https://www.investopedia.com/terms/v/volatility.asp) ·
[Heteroskedasticity](https://www.investopedia.com/terms/h/heteroskedasticity.asp)

---

## Verdelingen voor de simulatie

### Student t-verdeling (*Student's t-distribution*)

Lijkt op de normale verdeling maar met dikkere staarten. Eén parameter regelt
hoe dik: de **vrijheidsgraden** (*degrees of freedom*, df).

| df | Gedrag |
|---|---|
| 1 | extreem dikke staarten (Cauchy; gemiddelde bestaat niet eens) |
| 4 | zeer dikke staarten |
| 10 | matig dik |
| 30+ | vrijwel niet van normaal te onderscheiden |

Wiskundig geldt: de kurtosis is eindig alleen als df > 4, en de variantie
alleen als df > 2.

**Voor goud is df op 3,6 geschat.** Dat is laag, en de QQ-plot rechts in
figuur 4 laat zien dat de data er veel beter bij past dan bij normaal.

Eén kanttekening om te kunnen maken: bij df = 3,6 is de theoretische kurtosis
niet eindig. Dat is een reden om in fase 4 zorgvuldig te zijn — de t-verdeling
past goed in het middengebied van de staart, maar extrapoleren naar zeer
extreme kwantielen vraagt om voorzichtigheid. Voor een 99%-VaR zitten we
ruim binnen het bereik waar de schatting betrouwbaar is.

→ [Investopedia: T-Distribution](https://www.investopedia.com/terms/t/tdistribution.asp) ·
[Degrees of Freedom](https://www.investopedia.com/terms/d/degrees-of-freedom.asp)

---

### GARCH

*Generalized AutoRegressive Conditional Heteroskedasticity.* Een model waarin
de volatiliteit van vandaag afhangt van de volatiliteit van gisteren en van de
schok van gisteren:

```
σ²_t = ω + α · ε²_{t−1} + β · σ²_{t−1}
```

In woorden: de verwachte onrust van morgen is een basisniveau (ω), plus een
deel van de klap van gisteren (α), plus een deel van de onrust van gisteren
(β). Zo bouwt het model volatiliteitsclustering rechtstreeks in.

*Heteroskedasticiteit* is het dure woord voor "de spreiding is niet constant".
*Conditional* betekent dat we de volatiliteit van morgen voorspellen gegeven
wat we vandaag weten.

Robert Engle kreeg in 2003 de Nobelprijs voor de voorloper (ARCH).

→ [Investopedia: GARCH](https://www.investopedia.com/terms/g/garch.asp)

---

### Geometrisch Brownse beweging (*geometric Brownian motion*, GBM)

Het standaardmodel voor koersen, en de basis onder Black-Scholes:

```
dS = μ·S·dt + σ·S·dW
```

Een prijs beweegt met een vaste drift (μ) plus toevallige schokken met een
vaste volatiliteit (σ). "Geometrisch" betekent dat de bewegingen
*proportioneel* zijn: een aandeel van €100 beweegt in euro's tien keer zoveel
als een van €10, maar procentueel evenveel. Daardoor kan de prijs nooit
negatief worden.

**De twee aannames die in onze data niet kloppen:**

1. Schokken zijn normaal verdeeld — weerlegd door kurtosis 6,50.
2. σ is constant — weerlegd door de volatiliteitsclustering.

Daarom bouwt fase 4 het in drie stappen op: eerst standaard-GBM als
referentie, dan t-verdeelde schokken, dan GARCH-volatiliteit. Zo kun je
per stap laten zien wat de verbetering oplevert.

→ [Investopedia: Geometric Brownian Motion](https://www.investopedia.com/articles/investing/102715/monte-carlo-simulation-basics.asp) ·
[Monte Carlo Simulation](https://www.investopedia.com/terms/m/montecarlosimulation.asp)

---

## Risicomaten

### Value-at-Risk (*VaR*)

"Met 99% zekerheid verlies ik morgen niet meer dan X." Oftewel: het
1%-kwantiel van de verliesverdeling.

**De bekende zwakte:** VaR zegt niets over hoe erg het wordt áls je door die
grens gaat. Een 99%-VaR van €10.000 is verenigbaar met een verlies van
€11.000 in het slechtste procent, maar ook met €500.000.

→ [Investopedia: Value at Risk](https://www.investopedia.com/terms/v/var.asp)

---

### Expected Shortfall (*ES*, *Conditional VaR*, *CVaR*)

Het gemiddelde verlies in de gevallen dat je de VaR-grens overschrijdt. Dit
repareert precies het gat hierboven: het kijkt naar de staart voorbij de
grens in plaats van alleen naar de grens zelf.

Sinds Basel III de voorkeursmaat voor banken, om die reden.

Voor jouw margevraag is ES eigenlijk relevanter dan VaR: je wilt niet alleen
weten hoe vaak je tekortkomt, maar ook hoeveel je dan tekortkomt.

→ [Investopedia: Conditional Value at Risk](https://www.investopedia.com/terms/c/conditional_value_at_risk.asp)

---

### Kupiec-toets (*Kupiec POF test*)

Toetst of je VaR-model klopt door overschrijdingen te tellen. Zeg je "99%
VaR", dan verwacht je dat 1% van de dagen de grens doorbreekt. Zie je er
veel meer, dan is je model te optimistisch; veel minder, dan is het te
conservatief en houd je onnodig veel kapitaal aan.

POF staat voor *proportion of failures*. Dit is de validatie die in fase 4
gaat vaststellen of de simulatie deugt — niet of hij mooie plaatjes maakt.

→ [Investopedia: Backtesting](https://www.investopedia.com/terms/b/backtesting.asp)

---

## Nog te behandelen in fase 2 en 3

Deze staan hier alvast zodat de lijst compleet is; de uitleg volgt wanneer we
ze gebruiken.

| Begrip | Waar | Link |
|---|---|---|
| Stationariteit | fase 2 | [Investopedia](https://www.investopedia.com/articles/trading/07/stationary.asp) |
| ADF-toets | fase 2 | [Investopedia](https://www.investopedia.com/terms/a/augmented-dickey-fuller-test.asp) |
| Schijnverband (*spurious regression*) | fase 2 | [Investopedia](https://www.investopedia.com/terms/s/spurious_correlation.asp) |
| Multicollineariteit | fase 3 | [Investopedia](https://www.investopedia.com/terms/m/multicollinearity.asp) |
| OLS-regressie | fase 3 | [Investopedia](https://www.investopedia.com/terms/l/least-squares-method.asp) |
| R-kwadraat | fase 3 | [Investopedia](https://www.investopedia.com/terms/r/r-squared.asp) |
| Newey-West standaardfouten | fase 3 | [Investopedia](https://www.investopedia.com/terms/h/heteroskedasticity.asp) |
| Random walk | fase 3 | [Investopedia](https://www.investopedia.com/terms/r/randomwalktheory.asp) |
| Overfitting | fase 3 | [Investopedia](https://www.investopedia.com/terms/o/overfitting.asp) |
| Look-ahead bias | overal | [Investopedia](https://www.investopedia.com/terms/l/lookaheadbias.asp) |
