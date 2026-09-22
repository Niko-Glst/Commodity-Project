# Wat claim ik eigenlijk?

Eén vraag die vooraf beantwoord moet worden, anders is elke backtest een
curve-fit met betere marketing:

> Welke inefficiëntie? Wie zit er aan de andere kant en waarom verliest die?
> Wat is het staartrisico?

---

## Het korte antwoord: ik claim geen inefficiëntie

Dit project doet **geen** uitspraak dat er geld te verdienen valt aan het
voorspellen van goudprijzen. Het doet het tegenovergestelde: het toont aan dat
dat niet kan, en meet vervolgens iets anders dat wél bruikbaar is.

Dat onderscheid is de kern, dus hieronder beide.

---

## Deel 1: wat ik NIET claim (en waarom niet)

### De inefficiëntie die ik zou kunnen claimen

*"Macro-economische variabelen — reële rente, dollarkoers, inflatieverwachting —
voorspellen goudrendementen, en dat verband wordt door de markt onvoldoende
ingeprijsd."*

### Waarom die claim niet houdbaar is

**Wie zou er aan de andere kant zitten?** Centrale banken, goudmijnen die hun
productie hedgen, ETF-beheerders, en elk macro-fonds ter wereld. Die kijken
allemaal naar dezelfde FRED-reeksen, die publiek en gratis zijn.

**Waarom zouden zij verliezen?** Daar is geen antwoord op. Er is geen
structurele reden waarom een partij met meer kapitaal, snellere data en betere
uitvoering systematisch de verkeerde kant van deze trade zou kiezen. Een
inefficiëntie heeft een verliezer nodig die om een aanwijsbare reden verliest —
een verplichte verkoper, een gedwongen hedger, een belegger met een ander
mandaat. Hier is die er niet.

**En de data zegt hetzelfde.** Uit fase 3, walk-forward gevalideerd over 12 jaar
en 3.024 handelsdagen:

| Maat | Waarde |
|---|---|
| Directional accuracy | **43,8%** (onder munt-opgooien) |
| Out-of-sample R² | **−0,04** (slechter dan nul voorspellen) |
| RMSE tegenover random walk | **+1,96%** (slechter) |
| Diebold-Mariano | geen significant verschil |

### De backtest die dat bevestigt

Ik heb er tóch een strategie op gebouwd — niet omdat het kansrijk is, maar om de
bevinding te kwantificeren.

| | Jaarrendement | Sharpe | Max drawdown |
|---|---|---|---|
| **Strategie (bruto)** | −0,02% | **−0,001** | −36,8% |
| **Strategie (netto)** | −1,83% | **−0,163** | −40,5% |
| Buy & hold | +6,56% | +0,382 | −42,7% |
| Niets doen | 0,00% | 0,000 | 0,0% |

**De brutoSharpe is −0,001.** Het signaal produceert exact nul vóór kosten. Na
kosten verliest de strategie 1,83% per jaar, bij een omzet van 181× per jaar.

En de drie controles die een backtest pas serieus maken:

- **Executie-lag van 1 dag**, afgedwongen in de code. `run_backtest` weigert
  een lag van nul met een foutmelding.
- **Sharpe-significantie:** bij 12 jaar data is de standaardfout 0,289, dus je
  hebt minstens **0,57** nodig om van nul te onderscheiden. De strategie haalt
  −0,163 (t = −0,57).
- **Placebo:** de posities 200× door de tijd geschud. Het echte resultaat ligt
  op het **39e percentiel** — midden in de toevalsverdeling.

### Wat je hieruit mag concluderen

Dat de markt efficiënt is ten opzichte van publieke macro-data op dagbasis. Dat
is geen verrassing, en het is precies de nulhypothese die het project vooraf
formuleerde.

**De kosten zijn de clou.** Zelfs als het brutosignaal nét positief was geweest,
verdampt dat bij een omzet van 181× per jaar. Dat is een algemene les: een
signaal moet niet alleen bestaan maar groot genoeg zijn om zijn eigen
handelskosten te dragen.

---

## Deel 2: wat ik WÉL claim

### De claim

*"De margebehoefte van een goudfutures-hedge is beter te bepalen met een
GARCH-model dan met een vast percentage, omdat volatiliteit persistent en dus
voorspelbaar is — ook als de richting dat niet is."*

### Waarom deze claim wél houdbaar is

**Er is geen tegenpartij nodig.** Dit is geen trade. Ik voorspel niet of goud
stijgt of daalt; ik schat hoe groot de beweging kan zijn. Daar zit niemand aan
de andere kant van, want er wordt niets verhandeld.

Dat is het fundamentele verschil met Deel 1. Een voorspelling van de *richting*
concurreert met de hele markt. Een schatting van de *spreiding* is een
risicoberekening voor je eigen positie.

**De onderbouwing is gemeten, niet aangenomen:**

| Bevinding | Bewijs |
|---|---|
| Richting onvoorspelbaar | R² out-of-sample −0,04 |
| **Grootte wél voorspelbaar** | **GARCH-persistentie 0,9956; halfwaardetijd 156 dagen** |
| Dikke staarten | kurtosis 6,05; 79 dagen buiten 3σ waar normaal 16 voorspelt |
| Model correct gekalibreerd | Kupiec: 5 overschrijdingen tegen 5 verwacht (p = 0,98) |

**Het resultaat:** voor een kwartaal-hedge is 26–34% van de notionele waarde
nodig voor 99% zekerheid, tegenover een vuistregel van 5–10% die 44% tot 69% van
de paden dekt.

### Het staartrisico van deze claim

Dit is de vraag die het vaakst overgeslagen wordt, dus expliciet:

**1. Het model onderschat de staart in een regimebreuk.**
GARCH schat zijn parameters op historische data. Een gebeurtenis die zich
fundamenteel anders gedraagt dan de afgelopen 23 jaar — een goudstandaard, een
verkoopgolf van centrale banken, een exchange die sluit — zit er per definitie
niet in.

**2. De effectieve steekproef is klein.**
5.957 handelsdagen klinkt veel, maar de gerealiseerde volatiliteit heeft na
correctie voor autocorrelatie een effectieve steekproefgrootte van **42**. De
GARCH-parameters rusten daarop. Voor de kwartaalvraag zijn er **94**
niet-overlappende vensters met hooguit twee echte stressperiodes.

**3. Een te lage buffer heeft een asymmetrische uitkomst.**
Kom je tekort, dan word je gedwongen uitgestopt — en dat gebeurt per definitie
op het slechtste moment, want dat is precies wanneer de marge tekortschiet. Je
hedge valt dan weg terwijl je hem het hardst nodig hebt.

Daarom rapporteer ik een **bandbreedte** (26–34%) met GARCH als bovengrens, en
noem ik expliciet dat GARCH de staart met ~5 procentpunt overschat ten opzichte
van de historie. Bij een asymmetrisch risico is de conservatieve kant de juiste
— mits je weet dát hij conservatief is.

**4. Het is een liquiditeitsvraag, geen verliesvraag.**
Bij een hedge stijgt je fysieke goud evenveel als de futures verliezen. Je
vermogen blijft intact; je hebt alleen cash nodig op het juiste moment. Een
kredietlijn tegen het onderpand doet daarom hetzelfde werk als cash. Dat
verandert de vraag van *"heb ik 34% liggen?"* naar *"kan ik 34% opvragen?"* —
een veel makkelijkere eis.

---

## Waarom ik Deel 1 niet heb weggelaten

Een voor de hand liggende vraag: waarom een backtest tonen die verliest?

Omdat het weglaten ervan het project zwakker maakt, niet sterker. Drie redenen:

1. **Het is het bewijs bij de claim.** Deel 2 stelt dat richting onvoorspelbaar
   is en grootte wel. Deel 1 is de meting die het eerste deel van die uitspraak
   ondersteunt.

2. **De kostenanalyse is op zichzelf een resultaat.** Een brutoSharpe van −0,001
   die netto −0,163 wordt, laat precies zien hoe groot een signaal moet zijn om
   zijn eigen kosten te dragen.

3. **Het is de eerlijkheidstest.** Iedereen kan een backtest tonen die wint. Een
   die verliest tonen, met de placebo en de significantiedrempel erbij, laat
   zien dat de infrastructuur werkt — ook als de uitkomst ongunstig is.

---

## Samengevat in drie zinnen

**Wat ik niet claim:** dat macro-data goudrendementen voorspelt. Getest,
weerlegd, met de kostenanalyse erbij.

**Wat ik wel claim:** dat volatiliteit persistent genoeg is om een margebuffer
op te baseren die beter is dan een vuistregel.

**Het staartrisico:** die buffer rust op 42 effectieve waarnemingen en kent geen
regimebreuk die nog niet gebeurd is — daarom een bandbreedte en geen enkel
getal.

---

*Zelf nagaan: `python scripts/pipeline.py` — schrijft een manifest met seed,
git-commit en pakketversies weg in `output/runs/`.*
