# ADF en KPSS, vanaf nul

Doorlopen met uitleg en figuren: `python scripts/uitleg_adf_kpss.py`

---

## Eerst: wat jij al weet

Je samenvatting was correct. Fase 1 leverde dit op:

- Dalingen zijn extremer dan stijgingen (**scheefheid** −0,53)
- 4- en 5-sigma dagen komen veel vaker voor dan de klokvorm voorspelt
  (**kurtosis** 6,5), dus een **t-verdeling** past beter
- Volatiliteit **clustert**: onrustige dag vandaag betekent grote kans op een
  onrustige dag morgen
- Maar zonder vast ritme, dus je kunt er geen timing op zetten

Dat is compleet. Daar hoeft niets bij.

---

## De sprong die ik oversloeg

Alles hierboven gaat over **goud alleen**. Eén reeks.

Fase 2 kijkt naar **twee reeksen tegelijk**: beweegt goud mee met de rente? Met
de dollar?

Dat is een andere vraag. En er komt een probleem bij kijken dat bij één reeks
niet bestaat. **ADF en KPSS zijn gereedschap voor dat probleem** — dat is de
hele reden dat ze plots opduiken.

---

## Het probleem, zonder statistiek

Twee dingen die allebei zijn gegroeid sinds 2003:

| Jaar | NL bevolking (mln) | Netflix-abonnees (mln) |
|---|---|---|
| 2003 | 16,2 | 1,5 |
| 2009 | 16,7 | 73,5 |
| 2015 | 17,2 | 145,5 |
| 2021 | 17,6 | 217,5 |

**Correlatie: +1,000.** Perfect. Volgens de statistiek het sterkst mogelijke
verband dat bestaat.

Groeit Netflix door de Nederlandse bevolking? Natuurlijk niet.

### Wat er misgaat

De twee delen maar één ding: **de tijd**. Beide gaan omhoog naarmate de jaren
verstrijken. Een correlatie meet "bewegen ze samen", en het antwoord is ja — maar
niet omdat het één het ander beweegt.

Dat heet een **schijnverband**. En het is geen randgeval: bij twee reeksen die
allebei een trend hebben, gebeurt dit vrijwel altijd.

---

## Waarom dit bij goud speelt

De goudprijs ging van $346 in 2003 naar $4.423 nu. Een trend van 23 jaar omhoog.

Elke andere reeks die in die periode ook omhoog ging, correleert daarmee.
Ongeacht of er een verband is.

Dus als ik de goudprijs tegen de rente zet en een sterk verband vind, weet ik
niet of dat komt doordat:

- **A)** goud echt reageert op de rente, of
- **B)** ze in dezelfde periode toevallig dezelfde kant op liepen

Dat onderscheid moet ik kunnen maken, anders is fase 3 waardeloos.

---

## De oplossing

In plaats van:

> "de goudprijs is $4.423 en de rente is 2,6%"

kijk je naar:

> "goud ging vandaag +0,8% en de rente +0,03 punt"

Waarom dat werkt: **een trend zit in de niveaus, niet in de dagelijkse
veranderingen.** De goudprijs loopt 23 jaar omhoog, maar de dagelijkse
verandering schommelt rond nul — vandaag omhoog, morgen omlaag.

Door naar veranderingen te kijken haal je de trend eruit. Wat overblijft is:
bewegen ze op *dezelfde dagen* dezelfde kant op? En dat is de vraag die je
eigenlijk wilde stellen.

> **En dit deed je al.** In fase 1 heb je nooit met prijzen gerekend, altijd met
> rendementen. Dat is precies dezelfde stap. Je deed het goed; nu weet je waarom.

---

## Wat ADF en KPSS dan zijn

Twee toetsen die **één** vraag beantwoorden:

> Heeft deze reeks een vast niveau waar hij naar terugkeert, of loopt hij weg?

Het vakwoord voor "heeft een vast niveau" is **stationair**.

| | Betekenis | Gevolg |
|---|---|---|
| **Stationair** | het gemiddelde is hetzelfde in 2005 en in 2025 | veilig om te regresseren |
| **Niet stationair** | het gemiddelde loopt weg over tijd | gevaar voor schijnverbanden |

Dat is alles. De toetsen zijn een formele check op iets dat je vaak ook gewoon
kunt zien.

### Kijk zelf, zonder toets

| | 2003–2008 | 2021–2026 |
|---|---|---|
| Gemiddelde **goudprijs** | $566 | $2.572 |
| Gemiddeld **dagrendement** | +0,062% | +0,059% |

De prijs: 4,5 keer zo hoog. Weggelopen.
Het rendement: verschil van 0,003 procentpunt. Vrijwel gelijk.

Daar heb je geen toets voor nodig. **De toets geeft er een getal bij**, zodat je
het kunt opschrijven in plaats van "het lijkt me wel".

*Figuur: `output/figures/16_wat_toetsen_doen.png` — let op de twee stippellijnen
in elk linkerpaneel*

---

## Hoe je de uitkomst leest

Hier zit de verwarring, en het is echt verwarrend: **de twee toetsen stellen de
vraag precies omgekeerd.**

### ADF

Begint met aannemen: *"deze reeks is NIET stationair"* en kijkt of de data dat
tegenspreekt.

- Kleine p-waarde → de data spreekt het tegen → de reeks **is** stationair

### KPSS

Begint met aannemen: *"deze reeks IS stationair"* en kijkt of de data dat
tegenspreekt.

- Kleine p-waarde → de data spreekt het tegen → de reeks is **niet** stationair

**Dezelfde kleine p-waarde betekent bij de twee toetsen dus het
tegenovergestelde.** Dat is de enige moeilijkheid; de rest is simpel.

### Trucje om het te onthouden

Een kleine p-waarde betekent altijd: *"de aanname was fout"*. Je hoeft dus alleen
te weten met welke aanname elke toets begint:

- **ADF** begint pessimistisch (niet stationair)
- **KPSS** begint optimistisch (wel stationair)

### Waarom twee toetsen die elkaars tegenpool zijn?

Omdat ze elkaar dan kunnen controleren. Zeggen ze hetzelfde, dan ben je zeker.
Spreken ze elkaar tegen, dan is er iets bijzonders aan de hand — en dan wil je
dat weten in plaats van een getal geloven.

---

## Op jouw eigen data

### De goudprijs

| Toets | p-waarde | Zegt |
|---|---|---|
| ADF | 0,998 | niet stationair |
| KPSS | 0,010 | niet stationair |

Beide eens → **niet stationair**.

### Het goudrendement

| Toets | p-waarde | Zegt |
|---|---|---|
| ADF | 0,000 | wel stationair |
| KPSS | 0,100 | wel stationair |

Beide eens → **stationair**.

Precies wat je al zag zonder toets: de prijs loopt weg, het rendement niet.

---

## Wat dit verandert aan het project

Eigenlijk: **niets**. En dat is het punt.

Je werkte al met rendementen in plaats van prijzen. De toetsen bevestigen dat,
en nu kun je uitleggen waarom het goed was.

Wat het wel oplevert: een antwoord op een interviewvraag die zeker komt.

> **Vraag:** "Waarom heb je met rendementen gerekend en niet met prijzen?"
>
> **Antwoord:** "Omdat prijsreeksen niet-stationair zijn — getoetst met ADF en
> KPSS, tien van mijn twaalf reeksen. Op niet-stationaire data vindt een
> regressie schijnverbanden: ik heb het gemeten met toevalsreeksen en kreeg in
> 92% van de gevallen een significant verband waar er geen was."

Dat is een compleet, verdedigbaar antwoord — en het tweede deel is je eigen
meting, geen leerboekverwijzing.

---

## Samengevat in vier zinnen

1. Fase 1 keek naar goud alleen; fase 2 vergelijkt goud met andere reeksen.
2. Bij dat vergelijken ontstaat een nieuw probleem: twee reeksen die allebei een
   trend hebben, lijken samen te hangen ook als er niets is.
3. De oplossing is naar veranderingen kijken in plaats van naar niveaus — wat je
   al deed.
4. ADF en KPSS zijn de formele check daarop: heeft deze reeks een vast niveau,
   ja of nee.

---

## Nog niet duidelijk?

Zeg welk stuk. Er zijn drie plekken waar het meestal misgaat:

- **Waarom een trend een probleem is.** Dan is het Netflix-voorbeeld de beste
  ingang: figuur 15, paneel 1 en 2.
- **Wat "stationair" betekent.** Dan figuur 16: de twee stippellijnen per paneel.
- **De omgekeerde p-waarden.** Dan alleen het trucje onthouden: kleine p-waarde =
  aanname fout, en ADF begint pessimistisch, KPSS optimistisch.
