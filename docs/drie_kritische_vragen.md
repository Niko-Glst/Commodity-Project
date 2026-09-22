# Drie vragen die een interviewer stelt

Drie vragen waarop een vaag antwoord het hele project onderuit haalt. Alle drie
zijn gemeten, niet aangenomen.

Zelf nagaan: `python scripts/verken_vintage.py`

---

## Vraag 1: gebruik je ALFRED-vintages of de herziene reeks?

### Het eerlijke antwoord: de herziene reeks

De ALFRED-machinerie is geïmplementeerd, maar **wordt in de analyses niet
aangeroepen**. Alle resultaten draaien op de huidige waarden.

Mijn rechtvaardiging daarvoor was: *"de kernreeksen zijn marktnoteringen en
worden niet herzien."* Die claim is toetsbaar, dus heb ik hem getoetst. **Hij is
fout.**

### Wat ALFRED zegt (kalenderjaar 2015)

| Reeks | Observaties | Records | Herzien |
|---|---|---|---|
| **DTWEXBGS** (brede dollarindex) | 261 | 1.260 | **261** |
| CPIAUCSL (inflatie) | 12 | 71 | 12 |
| INDPRO (industriële productie) | 12 | 186 | 12 |

**De dollarindex — de sterkste driver in het model — is wél herzien.** Van de 261
observaties uit 2015 hebben er 249 een andere numerieke waarde in een latere
vintage, met een gemiddelde afwijking van **1,36%**. Dat is ruim vier keer de
dagelijkse volatiliteit van 0,3%.

### Wat de oorzaak is

Geen statistische bijstelling maar een **herbasering**: de Fed heeft deze index
op 4 maart 2019 opnieuw geïndexeerd. Het hele niveau verschuift daardoor.

### Waarom dat hier grotendeels wegvalt

Het model draait op **log-rendementen**, niet op niveaus. Een herbasering is een
vermenigvuldiging met een constante, en die verdwijnt bij differentiëren:

```
log(c · Pₜ) − log(c · Pₜ₋₁) = log(Pₜ) − log(Pₜ₋₁)
```

De dagrendementen zijn dus vrijwel ongevoelig voor deze specifieke herziening.

### Maar de claim was toch fout

`config.py` zei `NEVER_REVISED` waar `REVISED_MILD` hoort. Dat is gecorrigeerd,
met de meting in het commentaar.

### Twee bugs die deze vraag blootlegde

1. **`fetch_vintage_series` faalde op echte data.** FRED weigert het verzoek als
   er te veel vintage-datums in het venster vallen — bij een dagelijkse reeks al
   snel. De functie was getest met verzonnen dataframes en had nooit tegen de
   API gedraaid. Nu opgevangen met een begrijpelijke foutmelding.
2. **`publication_lag_days` werd nergens gebruikt.** Fase 3 lagt met een
   hardgecodeerde `shift(1)` in plaats van het veld per reeks. Voor de huidige
   set maakt dat niets uit (alle FRED-reeksen hebben lag 1), maar het is geen
   point-in-time-implementatie.

### Wat er zou moeten gebeuren

Per voorspelmoment `fetch_as_known_on()` aanroepen in plaats van de huidige
reeks. Die functie is nu gebouwd; aansluiten op de walk-forward is de volgende
stap.

### Het antwoord dat ik zou geven

> "De herziene reeks. Ik heb met ALFRED gemeten hoe groot de herzieningen zijn —
> 1,4% op de dollarindex, door een herbasering in 2019 — en beargumenteerd
> waarom dat op log-rendementen grotendeels wegvalt. Point-in-time ophalen is
> geïmplementeerd maar niet aangesloten op de backtest. Dat is een bekende
> beperking, geen aanname."

Dat is verdedigbaar. *"Ik gebruik vintages"* zou dat niet zijn geweest.

---

## Vraag 2: wat is je N?

### Het nominale antwoord is misleidend

5.957 handelsdagen klinkt comfortabel. Twee correcties maken het
ongemakkelijker.

### Correctie 1: effectieve steekproefgrootte

Bij tijdreeksen draagt niet elke waarneming een volle eenheid informatie bij:

```
N_eff = N / (1 + 2 · Σ autocorrelaties)
```

| Reeks | N | N_eff | Ratio |
|---|---|---|---|
| goudrendement | 5.958 | 5.958 | 100% |
| **gerealiseerde volatiliteit** | **5.938** | **42** | **0,7%** |
| d.dollarindex | 5.192 | 4.871 | 94% |
| d.breakeven-inflatie | 5.933 | 5.165 | 87% |

**Dat tweede getal is het belangrijkste van dit document.** De volatiliteit heeft
effectief **42** onafhankelijke waarnemingen — en de volatiliteit is precies wat
fase 4 modelleert.

De GARCH-parameters (persistentie 0,9956, halfwaardetijd 156 dagen) rusten dus
niet op duizenden waarnemingen maar op enkele tientallen. Dat verklaart ook
waarom de persistentie zo dicht bij 1 ligt: met zo weinig effectieve informatie
is dat parameter slecht bepaald.

### Correctie 2: onafhankelijke vensters

Voor de kwartaalvraag waar het project om draait:

| Horizon | Dagen | Niet-overlappend |
|---|---|---|
| 1 week | 5.958 | 1.191 |
| 1 maand | 5.958 | 283 |
| **1 kwartaal** | **5.958** | **94** |

**94 onafhankelijke kwartalen**, waarvan hooguit twee echte stressperiodes (2008
en 2020).

Dat verklaart direct waarom de Kupiec-toets zo zwak is: bij 78 vensters verwacht
je 0,8 overschrijdingen bij 99%. Daarmee kun je vrijwel geen model afwijzen.

### Het antwoord dat ik zou geven

> "Nominaal 5.957 dagen. Maar voor de kwartaalvraag zijn het 94 onafhankelijke
> vensters met twee echte stressperiodes. En de volatiliteit — wat ik in fase 4
> modelleer — heeft een effectieve steekproefgrootte van ongeveer 42. Dat is de
> reden dat ik een bandbreedte rapporteer in plaats van een puntschatting, en dat
> ik de zwakte van de Kupiec-toets expliciet benoem."

Dat antwoord is minder indrukwekkend dan een Sharpe-ratio, en veel sterker.

---

## Vraag 3: hoe weet je dat het niet toeval is?

### Het antwoord is een placebo-run

Draai exact dezelfde analyse op data waarin per constructie géén verband zit, en
kijk hoe vaak je dan toch "iets" vindt. Dat getal is je werkelijke
foutenpercentage.

### Placebo 1: nep-drivers met dezelfde persistentie

Vervang de macro-drivers door toevalsreeksen die er statistisch hetzelfde
uitzien — zelfde persistentie, zelfde spreiding.

*Waarom niet gewoon witte ruis:* de echte drivers zijn sterk persistent. Een
placebo van witte ruis zou een te makkelijke tegenstander zijn. De referentie
moet alles delen met de echte data **behalve** het verband dat je toetst. (Dat is
dezelfde les als bij de spectraalanalyse, waar een geschudde referentie een
"cyclus" van 1.483 dagen zou hebben gevonden.)

| | R² |
|---|---|
| **echte data** | **0,1864** |
| placebo mediaan | 0,0007 |
| placebo 95e percentiel | 0,0018 |
| placebo maximum | 0,0033 |

De echte uitkomst ligt op het **100e percentiel** van de placeboverdeling —
hoger dan élke van de 200 nepruns.

**Foutenpercentage op placebodata: 5,0%** tegen een nominale 5%. De toets is dus
correct gekalibreerd.

### Placebo 2: geschudde uitkomst

Drivers intact, goudrendement door elkaar geschud. Dat vernietigt elk verband in
de tijd terwijl de verdeling identiek blijft.

| | R² |
|---|---|
| **echte data** | **0,1864** |
| placebo mediaan | 0,0007 |
| placebo 95e percentiel | 0,0020 |

Ook hier: 100e percentiel, foutenpercentage 6,5%.

### Wat dit wél en niet zegt

**Wel:** de gelijktijdige samenhang tussen goud en de drivers is echt. Geen
enkele van de 400 placeboruns komt in de buurt.

Dat is ook niet verrassend — het dollarverband is deels mechanisch, want goud
wordt in dollars genoteerd.

**Niet:** dat je er iets mee kunt voorspellen. Fase 3 liet zien dat diezelfde
relatie out-of-sample nul oplevert: R² zakt van 18,6% naar −0,04 zodra je de
drivers lagt en op ongeziene data meet.

**Een echt verband hebben en er niets mee kunnen voorspellen is geen
tegenspraak.** Het is precies wat een efficiënte markt voorspelt: de informatie
zit al in de prijs.

### Het antwoord dat ik zou geven

> "De gelijktijdige samenhang overleeft een placebo-run met nep-drivers die
> dezelfde persistentie hebben: de echte R² van 0,186 ligt boven élke van 200
> nepruns, waarvan de hoogste 0,003 haalde. En het foutenpercentage van de toets
> op placebodata is 5,0% tegen een nominale 5%, dus de opzet is correct
> gekalibreerd. De vóórspelkracht overleeft de walk-forward niet — en dat
> rapporteer ik als het resultaat, niet als een probleem."

---

## Waarom deze drie samen

Ze toetsen alle drie hetzelfde: **weet je waar je getal vandaan komt, en wat het
niet betekent?**

| Vraag | Zwakke versie | Sterke versie |
|---|---|---|
| Vintages | "ja, point-in-time" | "herziene reeks, hier is de meting van hoeveel dat uitmaakt" |
| N | "bijna 6.000 dagen" | "94 onafhankelijke kwartalen, N_eff van 42 op de volatiliteit" |
| Toeval | "p < 0,05" | "placebo-run met 5,0% foutenpercentage tegen nominaal 5%" |

Alle drie de eerlijke antwoorden maken het project **zwakker** dan een
enthousiaste versie zou klinken. Dat is het punt: een interviewer kan ze
natrekken, en dan moet het kloppen.
