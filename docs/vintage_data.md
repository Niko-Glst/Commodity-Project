# Vintage data, revisies en look-ahead bias

Dit document beantwoordt één vraag: **als ik backtest met de FRED-data die ik
vandaag ophaal, gebruik ik dan informatie die op dat moment nog niet bestond?**

Het korte antwoord voor dit project: voor de zes kernreeksen niet in de
*waarden*, wel in de *timing*. Hieronder staat waarom, en wat we eraan doen.

---

## 1. Wat revisies zijn

Veel macro-economische statistieken worden na publicatie bijgesteld. Het
Amerikaanse BBP over een kwartaal kent bijvoorbeeld:

| Publicatie | Moment | Wat er verandert |
|---|---|---|
| Advance estimate | ~30 dagen na kwartaaleinde | eerste schatting, veel geëxtrapoleerd |
| Second estimate | ~60 dagen | meer bronbestanden binnen |
| Third estimate | ~90 dagen | vollediger |
| Annual update | jaarlijks in september | nieuwe seizoensfactoren, bronrevisies |
| Comprehensive revision | elke ~5 jaar | definitiewijzigingen, herbasering |

Het verschil is niet cosmetisch. De advance estimate voor Q4 2008 was −3,8%
op jaarbasis; de uiteindelijke waarde werd −8,9%. Wie een model backtest met
de huidige waarde, laat het model in januari 2009 "weten" dat de krimp bijna
drie keer zo groot was als wat toen gepubliceerd werd. Elk signaal dat het
model daaruit haalt, is onbereikbaar voor een echte belegger.

Dit is **look-ahead bias**: het model heeft toegang tot informatie die op het
beslismoment niet bestond. Het is de meest voorkomende manier waarop een
backtest er goed uitziet zonder dat het model iets waard is.

---

## 2. Hoe ALFRED dat oplost

ALFRED (*Archival* FRED) bewaart elke versie van elke observatie. Waar FRED
per observatiedatum één waarde geeft, geeft ALFRED er meerdere, elk met een
geldigheidsvenster:

| date (observatie) | realtime_start | realtime_end | value |
|---|---|---|---|
| 2020-01-01 | 2020-04-29 | 2020-05-27 | -4.8 |
| 2020-01-01 | 2020-05-28 | 2020-06-24 | -5.0 |
| 2020-01-01 | 2020-06-25 | 2020-09-29 | -5.0 |
| 2020-01-01 | 2020-09-30 | 9999-12-31 | -5.1 |

Lees dit als: "de waarde voor Q1 2020 was tussen 29 april en 27 mei
gepubliceerd als −4,8; daarna werd hij bijgesteld."

Om te weten wat op een bepaalde dag bekend was, filter je op het venster dat
die dag omvat:

```
realtime_start <= peildatum <= realtime_end
```

Dat is precies wat [`as_known_on`](../src/goldmodel/data/fred_client.py) doet.
In een walk-forward backtest roep je die functie aan met de datum van elk
voorspelmoment, niet één keer met vandaag. Observaties die op de peildatum nog
niet gepubliceerd waren, verdwijnen dan volledig uit het paneel — en dat hoort
zo, want die kende je toen niet.

Een tweede, subtieler punt: ALFRED laat ook zien dat een cijfer op de
peildatum er nog helemaal niet was. Het BBP over Q1 2020 bestond op 15 april
2020 niet; de eerste publicatie kwam pas op 29 april. Een naïeve backtest die
"de laatste beschikbare waarde" gebruikt, pakt dan stilzwijtend een waarde uit
de toekomst. Vintage-data maakt dat onmogelijk in plaats van iets waar je aan
moet denken.

---

## 3. Waarom het voor déze reeksen beperkt speelt

De zes kernreeksen zijn allemaal **marktnoteringen**, geen statistische
schattingen:

| Reeks | Wat het is | Wordt herzien? |
|---|---|---|
| DFII10 | TIPS-rendement, uit marktkoersen | Nee |
| DTWEXBGS | Dollarindex, uit wisselkoersen | Nee |
| T10YIE | Nominaal minus TIPS, beide marktkoersen | Nee |
| DFF | Gerealiseerde transacties in de fed funds-markt | Nee |
| T10Y2Y | Verschil van twee marktrendementen | Nee |
| BAMLH0A0HYM2 | ICE-index uit obligatiekoersen | Nee |

Het TIPS-rendement van 3 maart 2020 was toen 0,58% en is dat nog steeds. Er
valt niets te herzien: de markt sloot, de koers stond vast. Voor deze reeksen
levert "huidige data" dus **geen vertekening in de waarden** op, en is het
volledige vintage-panel opvragen alleen maar duurder en trager.

Eén reeks in de configuratie is anders: **WALCL** (de Fed-balans) is als
`REVISED_MILD` gemarkeerd. De Fed corrigeert die af en toe marginaal. De reeks
is optioneel en zit niet in de kernset.

---

## 4. Wat er wél speelt: publicatievertraging

Ook zonder revisies is er een timingprobleem. FRED publiceert de waarde van
handelsdag *t* pas op werkdag *t+1*. De H.15-release met de rentes verschijnt
rond 16:15 ET de volgende werkdag; de dollarindex idem.

Wie in een regressie het goudrendement van dag *t* verklaart uit de reële
rente van dag *t*, gebruikt een getal dat pas de volgende dag op FRED stond.
Voor een *verklarende* analyse ("wat bewoog samen?") is dat verdedigbaar. Voor
een *voorspellende* backtest ("had ik hierop kunnen handelen?") is het look-ahead
bias.

Daarom heeft elke `SeriesSpec` een `publication_lag_days`. In fase 2, bij het
bouwen van de modelmatrix, wordt elke driver met dat aantal dagen gelagd
voordat hij op het goudrendement wordt aangesloten. Dat is een expliciete,
zichtbare stap in plaats van een impliciete aanname.

> **Nuance die je in een gesprek moet kunnen maken:** de FRED-publicatie loopt
> een dag achter, maar de onderliggende marktprijs was op dag *t* zelf al
> zichtbaar op een Bloomberg-terminal. Een echte handelaar had het TIPS-rendement
> intraday. De lag van één dag is dus conservatief ten opzichte van wat een
> professionele partij kon, en realistisch ten opzichte van wat je met gratis
> data kunt reproduceren. Conservatief is hier de goede kant om te falen.

---

## 5. Wat we nu bouwen en wat later

**Nu geïmplementeerd:**

- `RevisionBehaviour` per reeks in de configuratie, zodat de aanname
  expliciet en controleerbaar is in plaats van impliciet.
- `publication_lag_days` per reeks, klaar voor gebruik bij het lagen.
- `FredClient.fetch_vintage_series()` — haalt het volledige vintage-panel op.
- `as_known_on()` — reconstrueert de reeks zoals bekend op een peildatum.

De vintage-machinerie is dus *gebouwd en getest*, maar wordt voor de
kernreeksen niet gebruikt, omdat er niets te reconstrueren valt.

**Wanneer we omschakelen:** zodra we een reeks toevoegen met
`RevisionBehaviour.REVISED`. Kandidaten die inhoudelijk interessant zijn voor
een goudmodel:

- `CPIAUCSL` — gerealiseerde inflatie (sterk gereviseerd via seizoensfactoren)
- `INDPRO` — industriële productie (maandelijkse en jaarlijkse revisies)
- `PAYEMS` — werkgelegenheid (twee revisies plus jaarlijkse benchmark)

Zodra een van die reeksen in de kernset komt, moet de backtest per
voorspelmoment `as_known_on(vintage_frame, forecast_date)` aanroepen. De
walk-forward loop in fase 3 wordt daar nu al op ontworpen.

---

## 6. Hoe je dit verdedigt in een gesprek

De sterke formulering is niet "ik heb vintage data gebruikt" en ook niet "ik
heb het overgeslagen", maar:

> "Ik heb per reeks vastgelegd of hij gereviseerd wordt. De kernreeksen zijn
> dagelijkse marktnoteringen die niet herzien worden, dus daar levert huidige
> data geen bias in de waarden op. Wat wel speelt is de publicatievertraging
> van één werkdag, en die corrigeer ik expliciet met een lag per reeks. De
> ALFRED-ophaling is geïmplementeerd en klaar voor het moment dat ik een
> reeks als CPI toevoeg, waar revisies wél substantieel zijn."

Dat laat zien dat je het onderscheid begrijpt tussen *revisiebias* en
*publicatievertraging* — twee dingen die vaak op één hoop gegooid worden — en
dat de keuze onderbouwd is in plaats van weggelaten.
