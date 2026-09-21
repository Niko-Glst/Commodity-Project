# LEG 3B — Refined products (crack spread)

**Status:** voorgesteld, niet ingebouwd. Voorlopige verkenning gedaan.
**Zelf nagaan:** `python scripts/verken_crack_spread.py`
**Timing:** ná fase 3, niet ervoor. Onderbouwing onderaan.
**Voorgesteld door:** Nikolay
**Vastgelegd:** 21 september 2026

---

## Het voorstel (oorspronkelijke formulering)

> - Compute 3-2-1 crack daily: `(2*RB + 1*HO)*42 - 3*CL) / 3`, and the diesel
>   crack (`HO*42 - CL`) separately. Intraday from RB=F/HO=F/CL=F; daily history
>   from FRED.
> - Test whether the diesel crack explains T10YIE (breakeven) changes BETTER than
>   crude alone. Extend the mediation test: `gold ~ crude` vs
>   `gold ~ crude + diesel crack + breakeven`. If products dominate crude,
>   replace crude as the oil leg.
> - Flag explicitly: there are essentially two high-crack regimes in the sample
>   (2022 and 2026). Do NOT build a mean-reversion strategy on the crack spread
>   itself — N is too small. Treat it as an explanatory feature only.

---

## Wat een crack spread is

De **crack spread** is de winstmarge van een raffinaderij: het verschil tussen
wat geraffineerde producten opbrengen en wat de ruwe olie kostte.

De **3-2-1** verhouding benadert een typische Amerikaanse raffinaderij: uit 3
vaten ruwe olie komen ongeveer 2 vaten benzine en 1 vat stookolie/diesel. De
factor 42 zet gallons om naar vaten (1 vat = 42 gallon), want RB=F en HO=F
noteren in dollar per gallon terwijl CL=F in dollar per vat noteert.

De **diesel crack** is de smallere variant: alleen stookolie tegen ruwe olie.

### Waarom dit voor een goudmodel relevant zou kunnen zijn

De economische gedachte achter het voorstel: **diesel is een directere
inflatiedriver dan ruwe olie.** Vrachtvervoer, landbouw en industrie lopen op
diesel, dus dieselprijzen werken door in de consumentenprijzen op een manier die
ruwe olie niet doet. Als de markt inflatie inprijst via de breakeven-rente, zou
de dieselmarge daar meer over moeten zeggen dan de ruwe-olieprijs.

En breakeven-inflatie is al een driver in het model. Dus: kan de crack spread de
olie-leg verbeteren?

---

## Voorlopige verkenning — de data is er

Alle drie de futures-reeksen zijn over de volledige periode beschikbaar via
yfinance:

| Reeks | Ticker | Waarnemingen | Periode |
|---|---|---|---|
| Ruwe olie (WTI) | CL=F | 5.961 | 2003-01-02 tot nu |
| Benzine (RBOB) | RB=F | 5.964 | idem |
| Stookolie/diesel | HO=F | 5.962 | idem |

Berekende spreads:

| Spread | Gemiddeld | Mediaan | Maximum |
|---|---|---|---|
| 3-2-1 crack | $19,10 | $17,50 | $75,31 |
| Diesel crack | $22,57 | $20,51 | $117,92 |

Technisch kan het dus. Geen FRED nodig — yfinance dekt de hele historie.

---

## Jouw waarschuwing getoetst: hij klopt, en scherper dan geformuleerd

Je schreef dat er "essentially two high-crack regimes" zijn. Nagerekend, met het
95e percentiel van de diesel crack ($54,21/vat) als drempel:

| Jaar | Dagen boven de drempel |
|---|---|
| 2020 | 1 |
| **2022** | **139** |
| 2023 | 18 |
| **2026** | **140** |

**279 van de 298 dagen (94%) zitten in twee jaren.**

Een script dat aaneengesloten blokken samenvoegt (met een tussenruimte van
minder dan 60 dagen als "dezelfde episode") vindt formeel **4 episodes**:

| Episode | Van | Tot | Duur |
|---|---|---|---|
| 1 | 2020-04-20 | 2020-04-20 | 1 dag |
| 2 | **2022-03-08** | **2023-01-31** | **329 dagen** |
| 3 | 2023-08-25 | 2023-09-14 | 20 dagen |
| 4 | **2026-03-03** | **heden** | **202 dagen, nog open** |

Twee dingen die dat blootlegt en die ik met de hand over het hoofd zag:

1. **De 2022-episode loopt door tot januari 2023.** Het is niet "2022 en 2023"
   als twee gebeurtenissen maar één aaneengesloten crisis van bijna elf
   maanden — de energiecrisis na de Russische inval in Oekraïne, met
   dieseltekorten in Europa.
2. **De huidige episode is nog niet afgelopen.** Sinds maart 2026 zit de diesel
   crack boven de drempel, en vandaag nog. Dat betekent dat we geen enkele
   waarneming hebben van hoe deze episode *eindigt*.

Effectief heb je dus **twee grote episodes waarvan één nog loopt** — niet
N = 298, en zelfs niet N = 4 in enige bruikbare zin.

Dat maakt je waarschuwing tegen een mean-reversion-strategie niet alleen juist
maar dwingend, en om een reden die scherper is dan "N is te klein":

**Van de ene afgeronde grote episode weet je hoe hij eindigde; van de lopende
niet.** Een mean-reversion-model heeft precies dat nodig — de snelheid waarmee
een hoge crack terugvalt. Je hebt daar één observatie van. Een backtest zou dat
ene herstelpad fitten en rapporteren als een patroon.

> Dit is dezelfde fout die ik eerder in dit project bijna maakte bij de
> cyclusanalyse: een periodogram vond een "significante piek" die niets anders
> was dan twee crisisperiodes. Zie `docs/gevorderd/cyclusanalyse.md`.

---

## De kernvraag alvast getest

De mediatietest is uitvoerbaar met de data die er nu is. Voorlopige uitkomst op
4.611 overlappende dagen:

### Verklaart de diesel crack de breakeven beter dan olie alleen?

| Model | R² |
|---|---|
| breakeven ~ olie | 0,0832 |
| breakeven ~ olie + crack | 0,0839 |

**Verbetering: 0,07 procentpunt.** Verwaarloosbaar.

### Voegt de crack iets toe aan het goudmodel?

| Model | R² | Aangepaste R² |
|---|---|---|
| goud ~ olie | 0,0266 | 0,0263 |
| goud ~ olie + crack | 0,0280 | 0,0276 |
| goud ~ olie + crack + breakeven | 0,0280 | 0,0274 |

**Verbetering: 0,14 procentpunt.** Ook verwaarloosbaar. En let op de laatste
regel: de *aangepaste* R² gaat omláág als je breakeven toevoegt — het extra
coëfficiënt kost meer aan vrijheidsgraden dan het oplevert.

### Conclusie van de verkenning

De voorwaarde in je eigen voorstel is **"if products dominate crude, replace
crude as the oil leg"**. Producten domineren ruwe olie niet. De crack spread
komt dus niet in de plaats van olie.

Dat maakt het voorstel niet waardeloos — zie hieronder — maar het verlaagt de
prioriteit aanzienlijk.

---

## Waarom ná fase 3 en niet ervoor

Drie redenen, in volgorde van belang.

### 1. Er is nog geen basismodel om tegen af te zetten

"Verbetert de crack spread het model?" is alleen te beantwoorden als er een
model is. Fase 3 bouwt dat: OLS met Newey-West, walk-forward gevalideerd tegen
een random walk.

Voeg je nu een driver toe, dan meet je de R² van een model dat nog niet
gevalideerd is. Een hogere in-sample R² zegt niets — dat is precies de fout die
dit project probeert te vermijden.

### 2. Olie zit nog niet eens in het model

Dit is het praktische punt: **ruwe olie is momenteel geen driver.** De huidige
set is reële rente, dollar, breakeven-inflatie, fed funds, rentecurve,
high-yield spread, Fed-balans, plus VIX/S&P/zilver.

Het voorstel wil de "oil leg" vervangen, maar die bestaat nog niet. De logische
volgorde is dus:

1. Fase 3: basismodel bouwen en valideren
2. Dan: is olie een zinvolle toevoeging? (aparte vraag)
3. Pas dan: is de crack spread beter dan olie?

Stap 3 zonder stap 2 is een antwoord op een vraag die niemand stelde.

### 3. Fase 2 bevinding 3 maakt het urgenter om iets anders te doen

De belangrijkste uitkomst van fase 2 is dat **vier van de vijf drivers van teken
wisselen door de tijd**. Een vast coëfficiënt is dan een gemiddelde van
tegengestelde regimes.

Dat probleem oplossen (of in elk geval eerlijk rapporteren) is waardevoller dan
een dertiende driver toevoegen aan een model waarvan de bestaande twaalf al
instabiel zijn. Meer variabelen bij instabiele verbanden is
overfitting-brandstof.

---

## Wat er wél waardevol aan is

Twee dingen, en die overleven de verkenning hierboven.

### Het is een goede vraag om te kúnnen beantwoorden

"Heb je ook naar geraffineerde producten gekeken?" is een redelijke
interviewvraag voor iemand met een commodity-achtergrond. Nu is het antwoord:

> "Ja. De diesel crack zou theoretisch een directere inflatiedriver moeten zijn
> dan ruwe olie, omdat vracht en industrie op diesel lopen. Ik heb het getest:
> de crack verbetert het breakeven-model met 0,07 procentpunt R² en het
> goudmodel met 0,14. Dat is geen verbetering. Bovendien zitten 94% van de
> hoge-crack dagen in twee episodes (2022 en 2026), dus effectief N = 2 — te
> weinig om er iets op te bouwen."

Dat is een sterker antwoord dan "daar heb ik niet aan gedacht".

### De N=2-waarschuwing is generaliseerbaar

Het methodologische punt uit je voorstel — *"do NOT build a mean-reversion
strategy, N is too small"* — geldt breder dan de crack spread. Het is dezelfde
val als:

- een cyclus "vinden" die twee crisisperiodes is
- een correlatie schatten over een periode met één regimewisseling
- een VaR-model kalibreren op data zonder crash

Die discipline hoort in het project thuis, en het is de moeite waard om er in de
documentatie naar te verwijzen ongeacht of de crack spread er ooit komt.

---

## Als we het later oppakken: de concrete stappen

1. **Reeksen toevoegen aan `config.py`** met economische motivatie en verwacht
   teken, zoals elke andere driver. CL=F, RB=F, HO=F.
2. **Afgeleide reeksen in een nieuwe module** (`src/goldmodel/spreads.py`), niet
   in de datalaag — een crack spread is een berekening, geen databron.
3. **De mediatietest formeel**, met walk-forward validatie in plaats van
   in-sample R². Dat is de test die telt.
4. **De regimewaarschuwing hard maken**: een test die faalt als iemand een
   mean-reversion-model op de crack spread bouwt, of minstens een functie die
   het aantal onafhankelijke episodes rapporteert in plaats van het aantal
   dagen.
5. **Roll-effecten checken.** RB=F en HO=F hebben sterkere seizoenspatronen dan
   goud (zomerbenzine, winterdiesel), dus de continue-contract-sprongen zijn
   daar groter. Dat is een reële databron-kwestie die bij goud beperkt speelde.

---

## Verwante open punten in de backlog

- **Cointegratie** tussen goud en de reële rente (uit `docs/fase2.md`): het
  arbitrage-argument gaat over niveaus, en differentiëren gooit die informatie
  weg.
- **Regimeafhankelijke coëfficiënten** (uit fase 2 bevinding 3): belangrijker dan
  extra drivers.
- **Langere horizon** (uit `docs/fase2_resultaat.md`): zwakke dagcorrelaties
  sluiten sterkere maandcorrelaties niet uit.
