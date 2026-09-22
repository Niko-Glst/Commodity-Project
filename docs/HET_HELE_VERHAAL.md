# Het hele verhaal: van nul tot nu

Wat we bouwen, waarom, wat er tot nu toe uitkwam, en wat je eruit leert.

Eén pagina om het overzicht terug te krijgen. Elk onderdeel heeft een eigen
document met de details.

---

## 1. De vraag waar alles om begon

> Ik heb een short goudfutures-positie als hedge, een kwartaal lang. Hoeveel
> cash moet ik achterhouden zodat ik met 99% zekerheid geen margin call mis?

Je hedge-tool zegt nu **"5 tot 10%"**. Dat is een vuistregel. Het project
vervangt hem door een onderbouwd getal.

Om dat te kunnen moet je drie dingen weten:

1. **Hoe beweegt goud?** (fase 1)
2. **Waarom beweegt goud?** (fase 2 en 3)
3. **Hoe simuleer je wat er kan gebeuren?** (fase 4)

---

## 2. Waarom die vuistregel wringt

Eerst even wat marge is, want dat verklaart de hele vraag.

Een COMEX-goudcontract is 100 troy ounce. Bij $4.400 is dat **$440.000**
notionele waarde. Dat betaal je niet — je stort ongeveer 5% als **onderpand**.
Dat geld blijft van jou; het staat alleen vast zolang de positie loopt.

Daar zit een hefboom van 20× in. Beweegt goud 1%, dan is dat $4.400 winst of
verlies. Op je inleg van $22.000 is dat **20% — in één dag**.

**Elke dag wordt je positie herrekend** (mark-to-market). Beweegt de prijs tegen
je in, dan gaat dat bedrag die dag van je rekening af. Geen papieren verlies dat
je kunt uitzitten. Zakt je saldo onder een ondergrens, dan belt je broker:
bijstorten, of hij sluit je positie — meestal op het slechtste moment.

**Daar is je cash-buffer voor.** Niet om het verlies te voorkomen, maar om niet
uitgestopt te worden terwijl je hedge nog loopt.

### Wat de historie zegt

Doorgerekend over 23 jaar, hoeveel cash je op het diepste punt nodig had:

| Horizon | Mediaan | 99%-grens |
|---|---|---|
| 1 week | 0,0% | 2,2% |
| 1 maand | 0,0% | 10,2% |
| **1 kwartaal** | **1,7%** | **24,8%** |

En wat 5–10% dekt:

| Horizon | 5% dekt | 10% dekt |
|---|---|---|
| 1 week | 99,5% | 100% |
| 1 maand | 94,1% | 98,3% |
| **1 kwartaal** | **68,1%** | **86,1%** |

**Voor een week is je vuistregel uitstekend. Voor een kwartaal dekt 5% maar
tweederde van de gevallen.**

### Maar: een hedge is geen kale short

Belangrijke nuance. Bij een hedge heb je óók fysiek goud. Stijgt goud 25%, dan
verlies je op de futures én wint je onderliggende positie — **je vermogen blijft
intact, je hebt alleen cash nodig op het juiste moment.**

Dat maakt het een liquiditeitsprobleem, geen verliesprobleem. Een kredietlijn
tegen je onderpand doet hetzelfde werk als cash, en kost je geen rendement.

*Details: [marge_uitgelegd.md](marge_uitgelegd.md) en
[hoeveel_cash.md](hoeveel_cash.md)*

---

## 3. Fase 1 — hoe beweegt goud?

Vier bevindingen uit 5.950 handelsdagen.

### Extreme dagen komen veel vaker voor dan "normaal"

Onder een normale verdeling (de klokvorm) zou een beweging groter dan 3
standaardafwijkingen in 16 van de 5.950 dagen voorkomen. **In werkelijkheid: 78.**

Het getal dat dat samenvat heet **kurtosis**: 0 bij normaal, **6,5** bij goud.

Het scherpste voorbeeld: op 30 januari 2026 daalde goud 10,8% op één dag — **9,9
standaardafwijkingen**. Onder de normale verdeling is de kans daarop 1 op
5,9 × 10²² dagen. Het heelal bestaat 5 biljoen dagen. *De normale verdeling zegt
dus: dit kan niet. Het gebeurde vorig jaar.*

### Goud valt harder dan het stijgt

**Scheefheid −0,53**: de grote dalingen zijn extremer dan de grote stijgingen.

### Onrust komt in blokken

Rustige periodes worden gevolgd door rustige, onrustige door onrustige. Dat heet
**volatiliteitsclustering**, en het levert het belangrijkste onderscheid van het
hele project op:

| | Voorspelbaar? |
|---|---|
| **Richting** (stijgt of daalt goud morgen?) | **Nee** |
| **Grootte** (wordt het een onrustige dag?) | **Ja** |

### Maar er zit geen vast ritme in

Je vroeg of de onrustige periodes op een klok lopen — met een Fourier-analyse te
vinden. Getest: **nee**. Onrust *houdt aan* en dooft uit, zonder ritme.

Dat is het verschil tussen **persistentie** ("het is nu onrustig, dus morgen
waarschijnlijk ook") en een **cyclus** ("over 64 dagen komt de volgende").
Bevinding 3 is persistentie.

### Wat dit betekent voor het model

| Bevinding | Gevolg |
|---|---|
| Dikke staarten (kurtosis 6,5) | geen normale verdeling → **t-verdeling** |
| Scheef naar links | dalingen en stijgingen niet symmetrisch |
| Onrust clustert | geen vaste volatiliteit → **GARCH** |
| Geen cyclus | geen sinus of Fourier |

*Details: [START_HIER.md](START_HIER.md), figuren 01–06*

---

## 4. Fase 2 — waarom beweegt goud?

### Eerst: de valkuil wegnemen

Fase 1 keek naar goud alleen. Fase 2 vergelijkt goud met andere reeksen, en daar
ontstaat een nieuw probleem.

Twee dingen die allebei groeien, lijken samen te hangen ook als er niets is. De
Nederlandse bevolking en Netflix-abonnees hebben een correlatie van **+1,000** —
ze delen alleen de tijd.

Gemeten met toevalsreeksen: **op prijsniveaus vindt een regressie in 92% van de
gevallen een "significant" verband dat er niet is.** Op veranderingen 4% —
precies wat het hoort te zijn.

De oplossing: kijk naar **veranderingen** in plaats van niveaus. Dat deed je in
fase 1 al (rendementen, geen prijzen). **ADF** en **KPSS** zijn de formele check:
tien van je twaalf reeksen zijn niet-stationair op niveau.

*Details: [adf_kpss_vanaf_nul.md](adf_kpss_vanaf_nul.md)*

### Drie drivers werken, de rest niet

| Driver | Verwacht | Gevonden | Verklaart |
|---|---|---|---|
| zilver | + | +0,784 | 61,4% |
| dollarindex | − | −0,400 | 16,0% |
| reële rente | − | −0,204 | 4,1% |
| *overige 8* | | −0,05 tot +0,05 | 0,0–0,2% |

De drie theoretisch belangrijkste kloppen qua teken. **Maar zelfs de sterkste
macro-driver verklaart maar 16%** van de dagelijkse beweging.

### De belangrijkste bevinding: de verbanden zijn niet stabiel

Rolling correlatie met goud, venster van één jaar:

| Driver | Min | Max | Wisselt teken? |
|---|---|---|---|
| S&P 500 | −0,333 | +0,430 | **ja** |
| VIX | −0,382 | +0,305 | **ja** |
| breakeven-inflatie | −0,281 | +0,357 | **ja** |
| reële rente | −0,558 | +0,042 | **ja** |
| dollarindex | −0,648 | −0,086 | nee |

**Vier van de vijf wisselen van teken door de tijd.** Een regressie schat één
vast coëfficiënt — wisselt het echte verband van teken, dan is dat coëfficiënt
een gemiddelde van tegengestelde regimes: **een getal dat in geen enkele periode
klopt.**

Alleen de dollar houdt consistent hetzelfde teken. Dat is ook de driver met een
deels mechanisch verband (goud wordt in dollars genoteerd), en mechanisch is
stabieler dan gedrag.

### En iets waar ik het mis had

Ik verwachtte dat het veilige-havenverband met de VIX zou *instorten* in maart
2020. Gemeten: de correlatie is −0,024 over de hele periode, en blijft vrijwel
nul in élke subperiode.

**Het verband stortte niet in — het was er nooit.** Op dagbasis is goud geen
veilige haven tegen aandelenvolatiliteit.

*Details: [fase2_resultaat.md](fase2_resultaat.md)*

---

## 5. Fase 3 — verslaat een model een random walk?

### De toets die telt

Niet de R². Een model met genoeg variabelen past altijd wel iets. De eerlijke
test: schat op data tot dag *t*, voorspel dag *t+1*, en vergelijk met een
benchmark die niets weet — de **random walk** ("morgen is als vandaag").

### Wat OLS in-sample doet

Met vier drivers op 5.139 dagen: **R² = 18,6%**.

Newey-West standaardfouten (nodig omdat de residuen clusteren) blazen de
onzekerheid met **1,66 tot 1,81 keer** op. Eén driver gaat daardoor van
significant naar niet-significant.

Eén teken klopt niet: de breakeven-inflatie is negatief waar theorie positief
voorspelt. Verklaring: dat is precies de driver die van teken wisselt door de
tijd, dus het vaste coëfficiënt is een gemiddelde van regimes.

### Wat er out-of-sample gebeurt

145 vensters, drivers met één dag gelagd (want FRED publiceert met een werkdag
vertraging):

| Model | RMSE | Directional accuracy | R² out-of-sample | vs. benchmark |
|---|---|---|---|---|
| **random_walk** | 0,010081 | n.v.t. | +0,0000 | — |
| **ols** | **0,010279** | **43,8%** | **−0,0396** | **+1,96%** |
| ridge | 0,010279 | 43,8% | −0,0396 | +1,96% |

**Het model is 2% slechter dan nul voorspellen.** De out-of-sample R² is
negatief: je was beter af met niets doen. De richting raden lukt in 43,8% van de
gevallen — onder munt-opgooien.

Diebold-Mariano: geen significant verschil. Het model is dus niet *aantoonbaar*
slechter, maar zeker niet beter.

### Eén aanwijzing voor later

Over langere horizonnen loopt de out-of-sample R² op: van +0,005 (dag) naar
+0,080 (kwartaal). Economisch logisch — het arbitrage-argument over de reële
rente gaat over maanden.

Maar bij een kwartaalhorizon houd je 82 niet-overlappende waarnemingen over voor
4 drivers. Te weinig om vast te stellen. **Eerlijke formulering: op dagbasis geen
signaal; op kwartaalbasis mogelijk wel, maar te weinig data.**

*Details: [fase3_resultaat.md](fase3_resultaat.md)*

---

## 6. Waar we nu staan

| Fase | Wat | Status |
|---|---|---|
| 1 | Datalaag + verdelingsanalyse | **klaar** |
| 2 | Stationariteit, correlaties, stabiliteit | **klaar** |
| 3 | Regressie + walk-forward validatie | **klaar** |
| 4 | Monte Carlo, VaR, margebehoefte | **klaar** |

### De rode draad, in één tabel

| | Voorspelbaar? | Bewijs |
|---|---|---|
| **Richting** van goud | **Nee** | R² out-of-sample −0,04; directional accuracy 43,8% |
| **Grootte** van de beweging | **Ja** | autocorrelatie volatiliteit 0,98, houdt maanden aan |

**Dat is het resultaat van drie fases werk**, en het is een ongemakkelijke
uitkomst die precies daarom waardevol is. Je hebt onderbouwd dat goudrendementen
niet voorspelbaar zijn uit publieke macro-data — wat een efficiënte markt
voorspelt.

### En het goede nieuws voor je oorspronkelijke vraag

**Voor een margeberekening heb je de richting niet nodig.** Je moet weten hoe
groot de beweging kan zijn, niet welke kant hij op gaat.

Dat is precies het deel dat wél voorspelbaar is.

---

## 7. Fase 4 — het antwoord

Volledig in [fase4_resultaat.md](fase4_resultaat.md). De kern:

**Waarom simuleren mag na fase 3:** een simulatie voorspelt de richting ook
niet. Elk pad is toeval. We gebruiken alleen de *grootte*, en die is
voorspelbaar.

**Drie modellen, elk onderbouwd met een eerdere meting:**

| Model | 99%-buffer (kwartaal) |
|---|---|
| GBM normaal | 26,0% |
| GBM t (df 3,5) | 26,4% |
| **GARCH t** | **34,5%** |

**De eerlijkheidscheck** — simulatie naast de werkelijke historie:

| Bron | p99 | Afwijking |
|---|---|---|
| historisch | 29,3% | — |
| constante volatiliteit | 26% | −3 pp |
| GARCH | 34,5% | +5 pp |

De constante modellen onderschatten de staart, GARCH overschat hem. Oorzaak:
persistentie van 0,9956 is bijna niet-stationair, waardoor GARCH de
langetermijnvolatiliteit op 20,8% schat waar de data 18,3% zegt.

**De Kupiec-validatie:** alle drie halen de toets, maar GARCH is het best
gekalibreerd — op de scherpste toets (495 vensters) precies 5 overschrijdingen
tegen 5 verwacht, tegenover 9 voor het normale model.

**Het antwoord:** 34,5% van de notionele waarde voor 99% zekerheid over een
kwartaal, met 26% als ondergrens. Je 5%-regel dekt 44% van de paden, 10% dekt
69%.

**Maar:** het is een liquiditeitsbehoefte, geen verlies. Bij een hedge stijgt je
fysieke goud evenveel. Een kredietlijn doet hetzelfde werk als cash.

---

## 8. Wat de oorspronkelijke opzet van fase 4 was

Drie stappen, elk onderbouwd met een bevinding uit fase 1–3:

**1. Geometrisch Brownse beweging als referentie**
Het standaardmodel. Twee aannames die we al weerlegd hebben: normale schokken
(kurtosis 6,5 zegt nee) en constante volatiliteit (clustering zegt nee). We
beginnen ermee om te kunnen laten zien wat de verbeteringen opleveren.

**2. t-verdeelde schokken**
Onderbouwd met de QQ-plot uit fase 1: de t-verdeling met 3,6 vrijheidsgraden past
de data veel beter dan normaal.

**3. GARCH-volatiliteit**
Onderbouwd met bevinding 3: volatiliteit is persistent, dus voorspelbaar. Een
buffer die meebeweegt met de markt van vandaag in plaats van met het gemiddelde
van 23 jaar.

**Plus validatie:** een Kupiec-toets op de VaR-overschrijdingen. Zeg je 99%, dan
moet het ook echt 99% zijn. Een simulatie die mooie getallen geeft maar de toets
niet haalt, is waardeloos.

### Wat het eindresultaat moet zijn

Geen puntvoorspelling, maar een verdeling. En daaruit één getal dat je kunt
verdedigen:

> "Gegeven de huidige marktvolatiliteit heb ik voor een kwartaal X% buffer nodig
> om met 99% zekerheid geen margin call te missen — en hier is de toets die
> aantoont dat die 99% ook echt 99% is."

---

## 9. Wat je hiervan leert (los van goud)

Dit is het deel dat overdraagbaar is naar elk ander kwantitatief project.

**In-sample R² zegt niets.** Fase 3 haalde 18,6% in-sample en −4% out-of-sample.
Wie alleen het eerste getal rapporteert, rapporteert niets.

**Kies je benchmark vóór je begint.** "Verslaat het de random walk" is een
scherpe vraag. "Heeft het een hoge R²" is er geen.

**Schrijf je verwachting vooraf op.** Elke driver in dit project heeft een
`expected_sign` die vast lag voor we de data zagen. Daardoor kun je zeggen "dit
teken klopte niet, en dit is waarom" in plaats van achteraf een verhaal te
verzinnen.

**Test je eigen gereedschap met een positieve controle.** "Het model vindt geen
signaal" is waardeloos als je niet weet dat je code een signaal *zou* vinden.
Beide controles zitten in de tests.

**Onderscheid "significant" van "bruikbaar".** Met 6.000 waarnemingen wordt bijna
alles significant. De autocorrelatie op dag 6 is significant en verklaart 0,14%
van morgen.

**Tel episodes, niet dagen.** Bij de crack-spread-verkenning leken er 298
waarnemingen te zijn; het waren er effectief twee. Dezelfde fout zat bijna in de
cyclusanalyse.

**Een correctie verandert je conclusie, niet je model.** Newey-West raakt de
standaardfouten, niet de coëfficiënten. En het blaast ze alleen op als *zowel*
de driver *als* de fout gecorreleerd zijn — iets waar ik zelf in trapte bij het
schrijven van de tests.

**Een negatief resultaat is een resultaat.** Drie fases werk leidden tot "dit is
niet voorspelbaar". Dat is verdedigbaar in een gesprek. Een mooi model dat je
niet kunt uitleggen, is dat niet.

---

## 10. Alles draaien

```powershell
python scripts/check_setup.py           # werkt alles?
python scripts/fetch_data.py            # data ophalen
python scripts/plot_distributions.py    # fase 1: de zes figuren
python scripts/fase2_stationariteit.py  # fase 2: ADF/KPSS
python scripts/fase2_correlaties.py     # fase 2: correlaties + stabiliteit
python scripts/fase3_regressie.py       # fase 3: OLS + walk-forward
python scripts/uitleg_marge.py          # margemechaniek dag voor dag
python scripts/zelftoets.py             # zes vragen met uitleg
python -m pytest tests/ -q              # alle tests
```

### Leesvolgorde

1. **Dit document** — het overzicht
2. [START_HIER.md](START_HIER.md) — fase 1 in vier bevindingen
3. [adf_kpss_vanaf_nul.md](adf_kpss_vanaf_nul.md) — fase 2 vanaf nul
4. [fase2_resultaat.md](fase2_resultaat.md) — de zes bevindingen
5. [fase3_resultaat.md](fase3_resultaat.md) — de validatie
6. [begrippen.md](begrippen.md) — naslagwerk per term, met links
7. [backlog/](backlog/README.md) — ideeën met de reden waarom ze wachten
