# Backlog: voorstellen die nog niet ingebouwd zijn

Hier staan uitbreidingen die zijn bedacht maar bewust niet (nog) in het
hoofdpad zitten. Elk voorstel heeft een eigen bestand met:

- wat het idee is
- wat een voorlopige verkenning opleverde
- **waarom het nu niet gebeurt**, en wanneer wel

Dat laatste is het punt van deze map. Een idee dat je opschrijft met de reden
waarom het wacht, is geen uitgestelde taak maar een gedocumenteerde keuze — en
dat is iets wat je in een gesprek kunt verdedigen.

---

## Openstaande voorstellen

| Voorstel | Herkomst | Timing | Status |
|---|---|---|---|
| [Crack spread als olie-leg](leg3b_crack_spread.md) | eigen voorstel, sep 2026 | na fase 3 | verkend; verbetering blijkt verwaarloosbaar |
| Cointegratie goud ↔ reële rente | volgt uit fase 2 stap 1 | na fase 3 | niet verkend |
| Regimeafhankelijke coëfficiënten | volgt uit fase 2 bevinding 3 | fase 3 of daarna | niet verkend |
| Langere horizon (maand/kwartaal) | volgt uit fase 2 bevinding 2 | in fase 3 meenemen | niet verkend |
| Vintage data voor CPI/INDPRO | volgt uit fase 1 | zodra zo'n reeks nodig is | machinerie al gebouwd |

---

## Waarom deze map bestaat

Tijdens het werken komen er steeds ideeën bij. Twee manieren om daarmee om te
gaan:

**Fout:** het idee meteen inbouwen. Dan groeit het project onbeheerst, en elke
nieuwe driver verhoogt de kans dat je iets vindt wat er niet is. Bij instabiele
verbanden — wat fase 2 aantoonde — is meer variabelen toevoegen
overfitting-brandstof.

**Beter:** het idee opschrijven met een eerste verkenning en een expliciete
reden waarom het wacht. Dan is het niet vergeten, en de afweging is
terugleesbaar.

De meeste voorstellen hier zullen nooit ingebouwd worden. Dat is geen falen:
het vastleggen waarom iets níet gebeurt, is onderdeel van een verdedigbare
methodologie.

---

## Een voorstel toevoegen

Nieuw bestand in deze map, en een regel in de tabel hierboven. Behandel het
minstens op deze punten:

1. **Wat is het idee**, in je eigen woorden, en welk economisch argument zit
   erachter?
2. **Is de data er?** Even ophalen en het aantal waarnemingen tellen.
3. **Een snelle verkenning.** Meestal is één regressie genoeg om te zien of het
   de moeite waard is.
4. **Hoeveel onafhankelijke waarnemingen zijn er echt?** Bij regime-achtige
   variabelen (spreads, crisisindicatoren) is het aantal *dagen* vaak veel
   hoger dan het aantal *episodes*. Dat onderscheid bepaalt of je er iets op
   kunt bouwen.
5. **Waarom nu niet**, en wat moet er eerst gebeuren?
