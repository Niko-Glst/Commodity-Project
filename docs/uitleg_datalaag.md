# Hoe de datalaag werkt — stap voor stap

Dit document legt uit wat de code in fase 1 precies doet. Geen theorie, maar
gewoon: welk bestand doet wat, en in welke volgorde gebeurt het.

---

## Het idee in één alinea

Je wilt data van internet (goudprijzen, rentes) om mee te rekenen. Elke keer
opnieuw downloaden is traag en onbeleefd tegenover de servers. Dus: download
één keer, sla op je harde schijf op, en gebruik daarna die kopie. Alle code in
fase 1 is de uitwerking van dat idee, plus het netjes omgaan met dingen die
misgaan.

---

## De vijf bestanden en wat ze doen

```
src/goldmodel/
├── config.py           ← WELKE data willen we, en waarom
└── data/
    ├── fred_client.py  ← HOE haal je data bij FRED op
    ├── yahoo_client.py ← HOE haal je data bij Yahoo op
    ├── cache.py        ← HOE sla je het op je schijf op
    └── loader.py       ← DE BAAS: bepaalt de volgorde
```

Denk aan een restaurant: `config.py` is het menu, de twee clients zijn de
leveranciers, `cache.py` is de koelkast, en `loader.py` is de kok die bepaalt
of hij uit de koelkast pakt of iets bestelt.

---

## 1. `config.py` — de boodschappenlijst

Hier staat welke reeksen we willen. Elke reeks is een `SeriesSpec`, en dat is
gewoon een verzameling gegevens over één tijdreeks:

```python
SeriesSpec(
    code="DFII10",              # hoe FRED hem noemt
    name="real_rate_10y",       # hoe wij hem noemen
    source=Source.FRED,         # waar hij vandaan komt
    description="...",          # wat het meet
    rationale="...",            # WAAROM we hem willen
    expected_sign="-",          # wat we verwachten
    revision=NEVER_REVISED,     # wordt hij achteraf aangepast?
    publication_lag_days=1,     # hoeveel later is hij pas bekend?
    ...
)
```

Er staan 12 van die blokken in het bestand: 7 van FRED, 5 van Yahoo.

**Waarom zoveel velden per reeks?** De eerste vier zijn puur administratie.
De laatste drie zijn de interessante:

- `rationale` — Als je in een sollicitatiegesprek gevraagd wordt "waarom heb
  je die variabele meegenomen?", staat het antwoord hier. Ik heb er een test
  op gezet die faalt als een motivatie korter is dan 100 tekens. Dat klinkt
  flauw, maar het dwingt je om na te denken voordat je een variabele toevoegt.
  Zonder die discipline sleep je vanzelf van alles het model in dat toevallig
  correleert.

- `expected_sign` — Wat je *vooraf* verwacht: gaat goud omhoog of omlaag als
  deze variabele stijgt? Dit opschrijven vóór je de regressie draait, is een
  bescherming tegen jezelf. Vind je straks het omgekeerde teken, dan moet je
  het verklaren. Zonder deze regel verzin je achteraf een verhaal bij elk
  resultaat, en dat is geen onderzoek meer.

- `publication_lag_days` — Hoeveel dagen later de waarde pas openbaar was.
  Hier komen we bij het belangrijkste concept van fase 1.

### Het look-ahead probleem, in gewone taal

FRED publiceert de rente van maandag pas op dinsdag. Als je een model bouwt
dat zegt "de goudprijs van maandag hing af van de rente van maandag", dan
gebruik je een getal dat op maandag nog niet bestond.

In een analyse achteraf is dat prima — je beschrijft wat er samen bewoog. Maar
zodra je zegt "mijn model had dit kunnen voorspellen", is het vals spel. Je
model kende de toekomst.

Daarom staat bij elke FRED-reeks `publication_lag_days=1`. In fase 2 schuiven
we elke reeks met dat aantal dagen op voordat hij het model in gaat. Het getal
staat er nu al, zodat we het straks niet vergeten.

---

## 2. `cache.py` — de koelkast

Deze klasse doet vier dingen:

**Opslaan.** `cache.save("yfinance_GC_F", dataframe, ...)` schrijft je data
naar `data/cache/yfinance_GC_F.parquet`.

**Bijhouden wanneer.** Naast de databestanden staat `_manifest.json`, een
klein bestand dat per reeks noteert wanneer hij is opgehaald, hoeveel rijen
er in zitten, en van welke datum tot welke datum. Zonder dat zou je een
bestand moeten openen om te weten hoe oud het is.

**Versheid bepalen.** `cache.is_fresh("yfinance_GC_F", ttl_hours=12)` geeft
`True` als het bestand jonger is dan 12 uur. TTL staat voor *time to live*.
Twaalf uur betekent in de praktijk: hooguit één keer per werkdag downloaden.

**Teruglezen.** `cache.load("yfinance_GC_F")` geeft je het dataframe terug.

### Waarom Parquet en niet Excel of CSV

Een CSV is tekst. Een datum wordt er als `"2024-01-15"` in opgeslagen, en bij
het inlezen moet je hem weer omzetten naar een echte datum. Een leeg veld kan
`""` zijn, of `"NA"`, of `"NaN"` — en dan moet je code weten welke variant.

Parquet slaat het *type* mee op. Een datum blijft een datum, een ontbrekende
waarde blijft ontbrekend. Je schrijft weg en leest terug, en je krijgt exact
hetzelfde terug. Het is ook kleiner en sneller.

Er is één klein ding dat Parquet níet bewaart, en dat vond ik door een test
die faalde: het `freq`-label van een datumreeks. Als je in pandas een reeks
maakt met "elke dag", onthoudt pandas dat als een label. Parquet gooit dat
label weg — de datums zelf blijven perfect intact, alleen het label verdwijnt.
Voor echte beursdata maakt het niets uit (die staat op handelsdagen, dus daar
is sowieso geen vast ritme), maar het staat gedocumenteerd in de test zodat
we er in fase 2 niet over struikelen.

---

## 3. `fred_client.py` en `yahoo_client.py` — de leveranciers

Twee bestanden die hetzelfde doen voor verschillende bronnen: een verzoek
sturen over internet en het antwoord omzetten naar een pandas-dataframe.

Allebei geven ze precies hetzelfde formaat terug: een dataframe met datums als
index en een kolom die `value` heet. Dat is bewust. Doordat FRED en Yahoo
hetzelfde formaat opleveren, hoeft de rest van de code het verschil niet te
kennen.

**Wat de FRED-client extra doet.** Als een verzoek mislukt, probeert hij het
opnieuw — maar niet altijd. Bij een netwerkstoring wél (dat kan tijdelijk
zijn). Bij een foutmelding "deze reekscode bestaat niet" niet, want die code
gaat de tweede keer ook niet bestaan. Tussen pogingen wacht hij steeds langer:
1,5 seconde, dan 3, dan 6. Dat heet *exponential backoff*, en het voorkomt
dat je een server die het al moeilijk heeft, verder overspoelt.

**Wat de Yahoo-client extra doet.** Yahoo geeft afhankelijk van de versie van
`yfinance` verschillende kolomstructuren terug — soms platte kolommen, soms
een dubbellaags structuur. De client maakt dat glad. Ook haalt hij de tijdzone
van de datums af, want anders kun je Yahoo-data niet samenvoegen met
FRED-data (die geen tijdzone heeft) en krijg je een cryptische foutmelding.

### De vintage-functie

In `fred_client.py` staan twee functies die je nu nog niet gebruikt maar die
er klaar staan: `fetch_vintage_series` en `as_known_on`.

Sommige cijfers worden achteraf bijgesteld. Het Amerikaanse BBP over een
kwartaal wordt drie keer gepubliceerd, en de cijfers verschillen. Wil je
eerlijk backtesten, dan moet je weten wat er *toen* gepubliceerd was, niet wat
er nu in de database staat.

FRED heeft daar een archief voor (ALFRED). Daar staat bij elke waarde: "dit
getal was de officiële waarde van 29 april tot 27 mei". `as_known_on(data,
"2020-05-15")` filtert daarop en geeft je de reeks zoals hij op 15 mei 2020
bekend was.

**Waarom gebruiken we het nu niet?** Omdat je zes hoofdreeksen allemaal
*marktprijzen* zijn. Het TIPS-rendement van 3 maart 2020 was toen 0,58% en is
dat nog steeds — de markt sloot, de koers stond vast, er valt niets bij te
stellen. Voor die reeksen is het archief opvragen alleen maar trager zonder
dat het iets verandert.

Het staat klaar voor als we later inflatiecijfers of werkloosheidscijfers
toevoegen. Dáár worden getallen wel flink bijgesteld.

De uitgebreide versie hiervan staat in [vintage_data.md](vintage_data.md).

---

## 4. `loader.py` — de kok

Dit is waar alles samenkomt. Voor elke reeks doorloopt de loader vier stappen:

```
1. Staat er verse data in de cache (jonger dan 12 uur)?
   JA  → gebruik die, ga niet het internet op. Klaar.
   NEE → door naar stap 2.

2. Probeer te downloaden.
   LUKT     → sla op in de cache, geef terug. Klaar.
   MISLUKT  → door naar stap 3.

3. Staat er oude data in de cache?
   JA  → gebruik die, maar meld duidelijk dat het oude data is.
   NEE → door naar stap 4.

4. Sla deze ene reeks over. Ga door met de rest.
```

Stap 3 en 4 zijn het belangrijkste deel. Als Yahoo vanmiddag plat ligt, wil je
niet dat je hele werkdag stilvalt — je had gisteren nog data. En als één reeks
niet op te halen is, moeten de andere elf gewoon binnenkomen.

Maar: **stil terugvallen op oude data is gevaarlijker dan een foutmelding.**
Je zou uren kunnen werken met verouderde cijfers zonder het te weten. Daarom
rapporteert de loader per reeks precies wat er gebeurd is, en dat zie je terug
in de tabel die het script afdrukt:

```
reeks           status              toelichting
gold_futures    opgehaald
vix             verse cache         3.2u oud
sp500           verlopen cache      bron onbereikbaar, cache van 48.1u oud
real_rate_10y   mislukt             Geen FRED API-sleutel beschikbaar.
```

### Het paneel bouwen

Aan het eind plakt `build_panel` alle reeksen aan elkaar tot één tabel, met
datums als rijen en reeksen als kolommen.

Die tabel zit vol gaten. FRED heeft geen waarde op Amerikaanse feestdagen,
Yahoo niet in het weekend, en de Fed-balans komt maar één keer per week. In
pandas verschijnen die gaten als `NaN` (*not a number*).

**Die gaten vullen we niet op, en dat is een bewuste keuze.**

De verleiding is om het laatste bekende getal door te trekken (*forward
fill*). Maar bij een wekelijkse reeks krijg je dan vijf identieke waarden op
rij. In een regressie ziet dat eruit als een heel stabiel, sterk verband,
terwijl je in werkelijkheid vier keer hetzelfde getal hebt gekopieerd. Je
statistische toetsen worden daardoor te optimistisch: ze denken dat je meer
onafhankelijke waarnemingen hebt dan echt zo is.

Dat is een modelleerbeslissing met gevolgen, en die hoort zichtbaar in fase 2
thuis — niet stilletjes in de datalaag.

---

## 5. De twee scripts

**`scripts/check_setup.py`** — controleert je installatie: Python-versie,
pakketten, of `.env` bestaat en een sleutel bevat, of beide API's bereikbaar
zijn, en of de cachemap schrijfbaar is. Bij elk probleem staat erbij wat je
moet doen. Draai dit als eerste, en als er iets niet werkt.

**`scripts/fetch_data.py`** — haalt alles op en drukt vijf secties af:

1. Laadrapport — per reeks: opgehaald, uit cache, of mislukt
2. Dekking — van wanneer tot wanneer, hoeveel waarnemingen
3. Niveaus — gemiddelde, spreiding, minimum, maximum
4. Rendementen — de dagelijkse veranderingen, met de staartanalyse
5. Correlaties — hoe de reeksen samenhangen

---

## Wat de cijfers je nu al vertellen

Sectie 4 van het script gaf dit (goud, ~5.900 handelsdagen sinds 2003):

```
                   n  gem_dag_%  std_dag_%  scheefheid  kurtosis_exces
gold_futures    5918     0.0430     1.1506     -0.5322          6.5438
```

Drie dingen om te lezen:

**`std_dag_% = 1.15`** — Een gemiddelde dag beweegt goud iets meer dan 1%.
Omgerekend naar jaarbasis is dat ongeveer 18% volatiliteit.

**`scheefheid = -0.53`** — De verdeling is scheef naar links. Grote dalingen
zijn extremer dan grote stijgingen. Goud valt harder dan het stijgt.

**`kurtosis_exces = 6.54`** — Dit is het belangrijkste getal. Bij een normale
verdeling (de klokvorm) is dit 0. Boven 0 betekent: extreme dagen komen véél
vaker voor dan de klokvorm voorspelt.

Het script maakt dat concreet:

```
           reeks    n  waargenomen_>3sd  verwacht_normaal  ratio
    gold_futures 5918                77           16.0000 4.8000
```

Er waren 77 dagen waarop goud meer dan drie standaardafwijkingen bewoog. Als
de rendementen normaal verdeeld waren, hadden dat er 16 moeten zijn. Bijna
vijf keer zoveel.

### Waarom dit voor jouw margevraag uitmaakt

Je wilt weten: hoeveel geld moet ik achterhouden zodat ik met 99% zekerheid
geen margin call krijg?

Dat is per definitie een vraag over de staart van de verdeling — over de
zeldzame, extreme dagen. En precies daar zit de normale verdeling er het
verst naast. Reken je met een klokvorm, dan komt er een te laag bedrag uit, en
je merkt het pas op de dag dat het misgaat.

Dat is de reden dat fase 4 met t-verdeelde schokken werkt in plaats van
normale. Het mooie is dat die keuze nu onderbouwd is met een getal uit je
eigen data (77 tegenover 16), niet met "zo doet men dat".

---

## Wat je nu kunt doen

```powershell
# Controleer of alles klopt
python scripts/check_setup.py

# Haal de data op
python scripts/fetch_data.py

# Kijk wat er in de cache staat
python scripts/fetch_data.py --cache-info

# Forceer opnieuw downloaden
python scripts/fetch_data.py --refresh

# Draai de tests
python -m pytest tests/ -q
```

Zelf rondkijken in de data kan zo:

```python
import sys
sys.path.insert(0, "src")

from goldmodel.data.loader import DataLoader
from goldmodel.config import ALL_SERIES

loader = DataLoader()
report = loader.load_all(ALL_SERIES)
panel = DataLoader.build_panel(report)

print(panel.tail(10))              # laatste tien dagen
print(panel["gold_futures"].describe())
```
