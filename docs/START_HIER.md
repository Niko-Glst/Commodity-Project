# Start hier

Het hele project in vier bevindingen. Verder niets.

De andere documenten zijn naslagwerk — je hoeft ze niet te lezen om verder te
kunnen. Dit is wat je moet weten.

---

## Waar we naartoe werken

> Ik heb een short goudfutures-positie. Hoeveel geld moet ik achterhouden
> zodat ik met 99% zekerheid geen margin call krijg?

Je hedge-tool zegt nu "5 tot 10%". Dit project vervangt die vuistregel door
een onderbouwd getal.

Om dat te kunnen, moeten we weten hoe goudprijzen zich gedragen. Dat is wat
fase 1 heeft uitgezocht.

---

## Bevinding 1: extreme dagen komen veel vaker voor dan "normaal"

Als goudrendementen een normale verdeling volgden (de klokvorm), zou een
beweging groter dan 3 standaardafwijkingen in 16 van de 5951 dagen voorkomen.

**In werkelijkheid: 78 dagen.** Bijna vijf keer zoveel.

Het getal dat dit samenvat heet **kurtosis**. Voor een normale verdeling is die
0; voor goud is hij **6,5**.

> **Waarom dit ertoe doet voor jouw vraag:** "met 99% zekerheid geen margin
> call" gaat per definitie over de zeldzame, extreme dagen. En daar zit de
> normale verdeling er het verst naast. Reken je met een klokvorm, dan komt er
> een te laag bedrag uit — en dat merk je pas op de dag dat het misgaat.

*Zie: `output/figures/01_verdeling_vs_normaal.png` en `04_qq_plot.png`*

---

## Bevinding 2: goud valt harder dan het stijgt

De grote dalingen zijn extremer dan de grote stijgingen. Het getal daarvoor
heet **scheefheid**: 0 is symmetrisch, goud zit op **−0,53** (negatief = scheef
naar links).

> **Waarom dit ertoe doet:** bij een *short* positie verlies je als de prijs
> stijgt. De scheefheid werkt dus in jouw voordeel — maar je moet weten dat hij
> er is in plaats van symmetrie aan te nemen.

*Zie: `output/figures/03_scheefheid.png`*

---

## Bevinding 3: onrust komt in blokken

Rustige periodes worden gevolgd door rustige, onrustige door onrustige. Dat
heet **volatiliteitsclustering**.

Twee dingen die je uit elkaar moet houden:

| | Voorspelbaar? |
|---|---|
| **Richting** (stijgt of daalt goud morgen?) | **Nee.** Niet af te leiden uit vandaag. |
| **Grootte** (wordt het een onrustige dag?) | **Ja.** Als vandaag onrustig is, morgen waarschijnlijk ook. |

> **Waarom dit ertoe doet:** je marge-buffer moet meebewegen met de markt. In
> een rustige periode heb je minder nodig dan in een onrustige. Eén vast
> percentage — zoals je huidige 5-10% — negeert dat.

*Zie: `output/figures/05_volatiliteitsclustering.png`*

---

## Bevinding 4: er zit geen vast ritme in

Je vroeg of de onrustige periodes op een klok lopen, zodat je kunt voorspellen
wanneer de volgende komt. **Dat is niet zo.**

Onrust *houdt aan* en dooft daarna uit, maar zonder vast ritme. Dat is het
verschil tussen:

- **Persistentie** — "het is nu onrustig, dus morgen waarschijnlijk ook" ✅
- **Cyclus** — "over 64 dagen komt de volgende onrustige periode" ❌

Bevinding 3 is persistentie. Een cyclus is er niet.

> **Waarom dit ertoe doet:** het bepaalt welk model we in fase 4 gebruiken.
> GARCH modelleert persistentie, en dat is de juiste keuze. Een model dat op
> een ritme mikt, zou hier niets vinden.

*De uitgebreide analyse staat in `docs/gevorderd/` — lees die pas als je er
zin in hebt, niet omdat het moet.*

---

## Wat dit samen betekent

Voor fase 4 weten we nu welk model we nodig hebben:

| Bevinding | Gevolg voor het model |
|---|---|
| Dikke staarten (kurtosis 6,5) | Geen normale verdeling; we gebruiken een **t-verdeling** |
| Scheef naar links (−0,53) | Dalingen en stijgingen niet symmetrisch behandelen |
| Onrust clustert | Geen vaste volatiliteit; we gebruiken **GARCH** |
| Geen cyclus | Geen sinus of Fourier — persistentie modelleren |

Elk van die keuzes is nu onderbouwd met een getal uit jouw eigen data. Dat is
precies wat je in een sollicitatiegesprek wilt kunnen zeggen: niet "zo doet men
dat", maar "ik heb het gemeten en dit kwam eruit".

---

## Vragen die hierbij horen

Drie vragen die je stelde, uitgebreid beantwoord in
[drie_vragen.md](drie_vragen.md):

- Waar komt de 5-10%-vuistregel vandaan? (en waarom hij voor een kwartaal te
  krap is)
- Wat betekent de rechte lijn in een QQ-plot?
- Wat is het verschil tussen de t-verdeling en de normale verdeling?

Figuren daarbij: `python scripts/uitleg_figuren.py`

---

## De commando's die je nodig hebt

```powershell
python scripts/check_setup.py         # werkt alles nog?
python scripts/fetch_data.py          # data ophalen
python scripts/plot_distributions.py  # de zes figuren maken
python scripts/uitleg_figuren.py      # figuren bij de drie vragen
python scripts/zelftoets.py           # zes vragen met uitleg
```

Meer is er niet. De rest is naslagwerk.

---

## Waar we nu staan

**Fase 1 is af.** We weten hoe goudprijzen zich gedragen.

**Fase 2 is de volgende stap:** kunnen we die bewegingen verklaren uit
macro-economische data — de rente, de dollar, de inflatieverwachting?

Dat begint bij één vraag, en dat is de enige waar we het de volgende keer over
hebben:

> Waarom mag je de goudprijs niet zomaar tegen de rente regresseren?

Het antwoord heet **stationariteit**, en het is de belangrijkste valkuil in de
hele econometrie. Eén begrip, één figuur, geen zijpaden.
