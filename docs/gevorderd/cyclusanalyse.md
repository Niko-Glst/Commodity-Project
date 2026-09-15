# Zit er een cyclus in de volatiliteit?

Een onderzoeksvraag die met "nee" eindigt, en waarbij het pad naar dat antwoord
leerzamer is dan het antwoord zelf.

---

## De vraag

Figuur 5 laat zien dat rustige en onrustige periodes in blokken komen. De
natuurlijke vervolgvraag: zit daar een *ritme* in? Als onrust elke zoveel
maanden terugkomt, kun je dat met een sinus of Fourier-reeks vangen en
voorspellen.

## Het korte antwoord

Nee. Er is wél iets meetbaars rond een periode van 64 handelsdagen, maar het
verklaart 0,8% van de beweging en maakt voorspellingen **slechter**, niet beter.

Wat je in figuur 5 ziet is geen cyclus maar **persistentie**: onrust houdt aan
en dooft daarna uit, zonder vast ritme. Dat is wel degelijk voorspelbaar, maar
op een andere manier — en precies wat GARCH modelleert.

---

## Wat een Fourier-transformatie doet

Elke tijdreeks is te schrijven als een som van sinussen en cosinussen met
verschillende frequenties. De Fourier-transformatie rekent uit hoeveel van elke
frequentie erin zit. Het resultaat heet het **periodogram**: op de horizontale
as de periode, op de verticale as hoeveel "energie" de reeks daar heeft.

Een echte cyclus van 60 dagen geeft een scherpe piek bij periode 60.

### De valkuil

**Een periodogram van pure ruis is niet vlak.** Het schommelt fors, en de
hoogste schommeling ziet er altijd uit als een piek. Wie zonder referentie naar
een periodogram kijkt, vindt gegarandeerd cycli die er niet zijn.

Daarom vergelijk je het spectrum altijd met wat je zou zien als er *geen* cyclus
was. En welke referentie je kiest, bepaalt je antwoord.

---

## De fout die ik maakte, en waarom hij leerzaam is

Mijn eerste opzet gebruikte de intuïtieve referentie: **schud de waarnemingen
door elkaar**. Dat behoudt de verdeling exact — gemiddelde, spreiding, dikke
staarten — maar vernietigt de volgorde, en dus elke cyclus.

Dat klinkt waterdicht. Het resultaat:

> Sterkste piek: **1483 dagen**, ruim significant.
> 111 van de 590 frequenties boven de 95%-band (verwacht: 30).

Een cyclus van bijna zes jaar in goudvolatiliteit. Dat had een "bevinding"
kunnen worden.

**Het is een artefact.** Schudden vernietigt niet alleen de cyclus die je zoekt,
maar ook de **persistentie** die je al kent. En de volatiliteit is extreem
persistent: de autocorrelatie van dag op dag is **0,985**.

Een traag bewegende reeks heeft van nature veel energie op lage frequenties —
niet omdat er een cyclus is, maar omdat hij traag is. Tegen een geschudde
referentie steekt die energie er altijd bovenuit. De "cyclus van 1483 dagen" was
niets anders dan de trage drift van de reeks zelf.

### De juiste referentie

Simuleer een **AR(1)-proces**: even persistent als de echte reeks (zelfde
autocorrelatie, gemiddelde en residuele spreiding), maar zonder enige cyclus.
De autocorrelatie daalt exponentieel en wordt nooit negatief.

Zo toets je de goede vraag: *heeft de volatiliteit méér structuur op een
bepaalde frequentie dan een traag maar ritmeloos proces zou hebben?*

### Het verschil, gemeten

Op een gesimuleerde persistente reeks **zonder enige cyclus**, bij de 30 laagste
frequenties:

| Referentie | Gemarkeerd als "significant" |
|---|---|
| Geschud (naïef) | 26 van 30 — **87%** |
| AR(1) (behoudt persistentie) | 2 van 30 — **7%** |

De naïeve referentie geeft vals alarm op bijna elke lage frequentie. De
AR(1)-referentie blijft bij de 5% die je bij toeval verwacht. Dit staat vast in
`tests/test_spectral.py::test_shuffle_null_flags_persistence_as_cycle`, zodat de
fout niet stilletjes terug kan komen.

---

## De vier toetsen op de echte data

### 1. Het spectrum met een eerlijke referentieband

| | Frequenties boven de band | Verwacht bij toeval |
|---|---|---|
| Geschudde referentie | 109 | 30 |
| AR(1)-referentie | 53 | 30 |

Sterkste afwijking: **periode van 64 handelsdagen**, op 2,3× de grens. Dat is
ongeveer drie kalendermaanden.

Er is dus *iets*. Maar 53 tegen 30 verwacht is een factor 1,8 — en bij het
toetsen van honderden frequenties tegelijk vind je er altijd een paar die
significant lijken (het **meervoudig-toetsen-probleem**). Een handvol
overschrijdingen zonder scherpe, geïsoleerde piek is geen cyclus.

De best passende sinus van 64 dagen heeft **R² = 0,0085**: hij verklaart 0,8%
van de beweging in de volatiliteit.

### 2. Het Slutsky-Yule-effect

Voordat je een piek serieus neemt, moet je uitsluiten dat je hem zelf gemaakt
hebt.

De volatiliteitsreeks is een **voortschrijdend gemiddelde**. En een
voortschrijdend gemiddelde van pure ruis vertoont golven — niet door de data
maar door het filter, dat korte schommelingen wegdrukt en lange laat staan.

Figuur 8 toont het: onafhankelijke ruis zonder enige structuur, gladgestreken
met hetzelfde 21-daagse venster, en de golven verschijnen.

Slutsky beschreef dit in 1927, Yule onafhankelijk rond dezelfde tijd. Het is een
van de klassieke manieren waarop onderzoekers cycli "vonden" in economische data
die er niet waren.

### 3. Persistentie is geen cyclus

Dit is het begripsmatige onderscheid dat de hele vraag beantwoordt.

| | Gedrag | Voorspelling |
|---|---|---|
| **Persistentie** | hoog blijft hoog, dooft geleidelijk uit | "het is nu onrustig, dus morgen waarschijnlijk ook" |
| **Cyclus** | hoog wordt laag wordt hoog, vast ritme | "over 64 dagen komt de volgende piek" |

Je ziet het verschil in de autocorrelatie:

- Bij **persistentie** daalt de curve langzaam naar nul en blijft positief.
- Bij een **cyclus** gaat de curve dóór nul, wordt negatief, en komt weer
  omhoog. Een golf.

De autocorrelatie van goudvolatiliteit daalt van 0,985 naar 0,00 over 250 dagen
en wordt nergens duidelijk negatief. Dat is het profiel van persistentie.

De kleine bulten waar de curve boven de AR(1)-lijn uitkomt (rond lag 100 en 185)
zijn de 64-daagse structuur. Zichtbaar, maar veel te zwak om op te sturen.

### 4. De beslissende test: voorspelt het iets?

Walk-forward: train op alles tot tijdstip t, voorspel de volgende 21 dagen,
schuif op. Nooit trainen op data die na de voorspelde periode ligt.

**234 vensters, RMSE in volatiliteitspunten:**

| Model | RMSE |
|---|---|
| Laatste waarde (naïef) | **3,63** |
| Gemiddelde laatste 21 dagen | 4,43 |
| Historisch gemiddelde | 5,99 |
| Alleen de constante (geen golf) | 5,99 |
| Sinus van 64 dagen | 6,03 |

De sinus is **66% slechter** dan simpelweg de laatste waarde herhalen. En de
golf voegt **−0,71%** toe bovenop een kale constante: hij maakt het actief
slechter.

Dat de sinus exact gelijk presteert aan het historisch gemiddelde is het
verklikkertje: alle voorspelkracht zit in de constante term, niet in het ritme.

#### Een tweede fout, ook leerzaam

Mijn eerste walk-forward voorspelde blokken van ~540 dagen in één keer. Toen
"versloeg" de sinus de naïeve benchmark met 28%.

Ook artefact. Over zo'n lange horizon keert de volatiliteit terug naar haar
gemiddelde, dus wint automatisch elk model dat het gemiddelde voorspelt. Dat
meet **mean reversion**, niet cycliciteit. De naïeve benchmark (één waarde 540
dagen lang herhalen) was een stroman.

Met een realistische horizon van 21 dagen draait het beeld volledig om.

**De les:** de opzet van je backtest bepaalt je antwoord. Een oneerlijke
benchmark of een onrealistische horizon maakt elk model goed.

---

## Waarom dit het verwachte antwoord is

Als de volatiliteit van goud een voorspelbaar ritme had, zou iedereen die dat
weet opties kopen vóór de piek en verkopen erna. Dat handelen zou het ritme
wegconcurreren. Een gratis lunch die twintig jaar blijft liggen op een van de
meest liquide markten ter wereld is onwaarschijnlijk.

**Maar volatiliteit is niet onvoorspelbaar.** Alleen op een andere manier:

- **Niet:** "over 64 dagen komt de volgende onrustige periode"
- **Wel:** "het is nu onrustig, dus morgen waarschijnlijk ook"

Een autocorrelatie van 0,985 is enorm. Daar zit echte voorspelkracht in — en dat
is precies wat GARCH modelleert. GARCH is geen cyclusmodel maar een
persistentiemodel, en dat is de juiste keuze voor deze data.

Voor de margeberekening in fase 4 is dat zelfs bruikbaarder: je wilt weten
hoeveel buffer je **nu** nodig hebt gegeven de huidige marktomstandigheden, niet
wanneer de volgende crisis komt.

---

## Wanneer Fourier wél zinvol is

Deze technieken zijn niet nutteloos, ze passen alleen niet bij deze vraag. Ze
werken wanneer een cyclus door iets **buiten de markt** wordt opgelegd:

- **Seizoenspatronen in grondstoffen.** Aardgasvraag piekt elke winter; dat
  wordt aangedreven door het weer, niet door handelsgedrag.
- **Intraday-patronen.** Handelsvolume en volatiliteit vormen een U over de dag,
  omdat beurzen op vaste tijden openen en sluiten.
- **Dag-van-de-week-effecten.** Maandagen wijken af omdat het weekendnieuws zich
  opstapelt.
- **Aankondigingscycli.** FOMC-vergaderingen liggen op een vaste kalender.

Het patroon: waar de kalender de structuur oplegt, is er iets te vinden. Waar de
structuur uit handelsgedrag zou moeten komen, concurreert de markt hem weg.

Voor goud zou je het kunnen proberen op dag-van-de-week of rond FOMC-data. Het
laatste is inhoudelijk het interessantst, maar dat is een *event study*, geen
spectraalanalyse.

---

## Reproduceren

```powershell
python scripts/analyse_cycles.py
python scripts/analyse_cycles.py --window 63   # ander volatiliteitsvenster
```

Figuren: `output/figures/07` tot `09`.

---

## Hoe je dit in een gesprek verdedigt

De sterke formulering is niet "ik heb geen cyclus gevonden", maar:

> "Ik vond eerst een cyclus van 1483 dagen tegen een permutatiereferentie.
> Die bleek een artefact: permutatie vernietigt de persistentie, en de
> volatiliteit heeft een autocorrelatie van 0,985. Tegen een AR(1)-referentie
> die de persistentie behoudt, blijft er structuur op 64 dagen over, maar die
> verklaart 0,8% en presteert out-of-sample 66% slechter dan een naïeve
> benchmark. Wat eruitziet als cycliciteit is persistentie — en dat is precies
> wat GARCH modelleert."

Dat laat drie dingen zien: je kent het verschil tussen persistentie en
cycliciteit, je weet dat de keuze van de nulhypothese het antwoord bepaalt, en
je toetst een bevinding out-of-sample voordat je hem gelooft.

Dat is waardevoller dan een gevonden cyclus.
