"""Korte zelftoets over de vier bevindingen uit fase 1.

Geen examen: het doel is dat je zelf kunt zien wat al zit en wat nog niet.
Bij elk antwoord krijg je uitleg, ook als het goed was.

Gebruik:
    python scripts/zelftoets.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field

LINE = "=" * 72


@dataclass
class Question:
    """Eén meerkeuzevraag.

    Attributen:
        topic: Waar de vraag over gaat, voor de eindscore per onderwerp.
        text: De vraag zelf.
        options: De antwoordmogelijkheden.
        correct: Index van het juiste antwoord (0-gebaseerd).
        explanation: Uitleg die je altijd krijgt, goed of fout.
        why_wrong: Per fout antwoord waarom het niet klopt.
    """

    topic: str
    text: str
    options: list[str]
    correct: int
    explanation: str
    why_wrong: dict[int, str] = field(default_factory=dict)


QUESTIONS: list[Question] = [
    Question(
        topic="Dikke staarten",
        text=(
            "Goud beweegt op een gemiddelde dag 1,15% (de standaardafwijking).\n"
            "Als de rendementen een normale verdeling volgden, hoeveel van de\n"
            "5951 handelsdagen zouden dan meer dan 3 standaardafwijkingen\n"
            "bewegen? En hoeveel waren het er echt?"
        ),
        options=[
            "Verwacht 16, werkelijk 78",
            "Verwacht 78, werkelijk 16",
            "Verwacht 16, werkelijk 16 — het klopt precies",
            "Verwacht 300, werkelijk 78",
        ],
        correct=0,
        explanation=(
            "Onder een normale verdeling ligt 99,73% binnen 3 standaardafwijkingen,\n"
            "dus 0,27% erbuiten. Van 5951 dagen is dat 16. Er waren er 78 —\n"
            "bijna vijf keer zoveel.\n\n"
            "DIT IS BEVINDING 1: extreme dagen komen veel vaker voor dan de\n"
            "klokvorm voorspelt. Daarom gebruiken we in fase 4 geen normale\n"
            "verdeling maar een t-verdeling."
        ),
        why_wrong={
            1: "Omgekeerd: de werkelijkheid heeft MEER extreme dagen dan de theorie.",
            2: "Als het precies klopte, was er geen probleem met de normale verdeling.",
            3: "300 zou betekenen dat 5% van de dagen extreem is; zo vaak is het niet.",
        },
    ),
    Question(
        topic="Kurtosis",
        text="Wat meet kurtosis?",
        options=[
            "Hoe vaak extreme uitschieters voorkomen (de staarten)",
            "Hoe spits de piek in het midden is",
            "Of dalingen groter zijn dan stijgingen",
            "Hoe breed de verdeling is",
        ],
        correct=0,
        explanation=(
            "Kurtosis meet de STAARTEN: hoe extreem de uitschieters zijn.\n\n"
            "Je berekent hem door elke dag om te rekenen naar een z-score, die\n"
            "tot de VIERDE macht te verheffen, en daar het gemiddelde van te\n"
            "nemen. Die vierde macht laat extremen enorm zwaar wegen:\n"
            "  z = 1  telt als    1\n"
            "  z = 4  telt als  256\n\n"
            "Voor een normale verdeling komt er 3 uit; iedereen trekt die eraf\n"
            "en rapporteert 'exces-kurtosis', waarbij 0 dus normaal is.\n"
            "Goud zit op 6,5."
        ),
        why_wrong={
            1: (
                "Veelgemaakte fout, ook in leerboeken. De hoge piek is een\n"
                "   BIJVERSCHIJNSEL: kansmassa verschuift uit het middengebied naar\n"
                "   zowel het midden als de staarten. Het gaat om de staarten."
            ),
            2: "Dat is scheefheid (de DERDE macht, die het teken behoudt).",
            3: "Dat is de standaardafwijking.",
        },
    ),
    Question(
        topic="Scheefheid",
        text=(
            "Goud heeft een scheefheid van −0,53. Wat betekent dat?\n"
            "(Ter herinnering: 0 = symmetrisch)"
        ),
        options=[
            "De grote dalingen zijn extremer dan de grote stijgingen",
            "De grote stijgingen zijn extremer dan de grote dalingen",
            "Goud daalt vaker dan het stijgt",
            "De gemiddelde dag is negatief",
        ],
        correct=0,
        explanation=(
            "Negatieve scheefheid = scheef naar links = de linkerstaart is langer.\n"
            "De grootste dalingen zijn groter dan de grootste stijgingen.\n\n"
            "Let op het verschil met optie 3: het gaat niet over HOE VAAK goud\n"
            "daalt, maar over hoe EXTREEM de dalingen zijn als ze komen.\n"
            "Goud stijgt gemiddeld zelfs licht (+0,0425% per dag)."
        ),
        why_wrong={
            1: "Dat zou POSITIEVE scheefheid zijn.",
            2: (
                "Bijna, maar net niet: scheefheid gaat over de GROOTTE van de\n"
                "   uitschieters, niet over hoe vaak ze voorkomen."
            ),
            3: "Het gemiddelde is juist positief; scheefheid zegt daar niets over.",
        },
    ),
    Question(
        topic="Clustering",
        text=(
            "Onrustige periodes komen in blokken. Wat kun je daarmee\n"
            "WEL voorspellen?"
        ),
        options=[
            "Dat morgen waarschijnlijk ook onrustig is als vandaag onrustig is",
            "Of goud morgen stijgt of daalt",
            "Wanneer de volgende onrustige periode precies begint",
            "Wat de goudprijs over drie maanden is",
        ],
        correct=0,
        explanation=(
            "De GROOTTE van de beweging is voorspelbaar, de RICHTING niet.\n\n"
            "Dat zag je in figuur 5: de autocorrelatie van de rendementen zelf\n"
            "blijft binnen de toevalsgrenzen (richting = onvoorspelbaar), maar\n"
            "die van de absolute rendementen steekt er ver bovenuit en houdt\n"
            "weken aan (grootte = voorspelbaar).\n\n"
            "DIT IS BEVINDING 3, en het is de basis voor GARCH in fase 4."
        ),
        why_wrong={
            1: (
                "Was dat zo, dan was er gratis geld te verdienen. De richting is\n"
                "   niet voorspelbaar — dat is de efficiënte-markthypothese."
            ),
            2: (
                "Dat zou een CYCLUS zijn, en die is er niet (bevinding 4).\n"
                "   Onrust houdt aan zonder vast ritme."
            ),
            3: "Dat is precies wat dit project NIET doet en niet kan.",
        },
    ),
    Question(
        topic="Persistentie versus cyclus",
        text=(
            "Wat is het verschil tussen persistentie en een cyclus?"
        ),
        options=[
            "Persistentie houdt aan en dooft uit; een cyclus komt op vaste tijden terug",
            "Persistentie is sterker dan een cyclus",
            "Het is hetzelfde, alleen een ander woord",
            "Een cyclus geldt voor prijzen, persistentie voor rendementen",
        ],
        correct=0,
        explanation=(
            "PERSISTENTIE  hoog blijft hoog en zakt geleidelijk terug. Geen klok.\n"
            "CYCLUS        hoog wordt laag wordt hoog, met een vaste tussenpoos.\n\n"
            "Goudvolatiliteit is persistent, niet cyclisch. Je weet dus wel dat\n"
            "onrust morgen waarschijnlijk aanhoudt, maar niet wanneer de volgende\n"
            "onrustige periode begint.\n\n"
            "Daarom gebruiken we GARCH (een persistentiemodel) en geen sinus of\n"
            "Fourier-reeks (cyclusmodellen)."
        ),
        why_wrong={
            1: "Het is geen kwestie van sterkte maar van soort gedrag.",
            2: "Ze zijn echt verschillend — en het verschil bepaalt ons model.",
            3: "Beide begrippen kunnen op elke reeks slaan.",
        },
    ),
    Question(
        topic="Toepassing",
        text=(
            "Waarom is je huidige vuistregel — altijd 5 tot 10% aanhouden —\n"
            "niet ideaal?"
        ),
        options=[
            "Hij beweegt niet mee: in onrustige tijden heb je meer nodig dan in rustige",
            "Hij is altijd te laag",
            "Hij is altijd te hoog",
            "Hij houdt geen rekening met de goudprijs zelf",
        ],
        correct=0,
        explanation=(
            "Een vast percentage negeert dat de volatiliteit verandert — en die\n"
            "verandering is juist voorspelbaar (bevinding 3).\n\n"
            "In een rustige periode houd je met 10% te veel kapitaal vast dat\n"
            "niets opbrengt. In een crisis is 10% misschien te weinig.\n\n"
            "Dat is precies wat fase 4 gaat oplossen: een buffer die meebeweegt\n"
            "met de marktomstandigheden, met een onderbouwde zekerheidsmarge."
        ),
        why_wrong={
            1: "Soms is hij te laag, soms te hoog — dat is nu juist het punt.",
            2: "Zie hierboven: het hangt van de marktomstandigheden af.",
            3: (
                "Een percentage schaalt automatisch mee met de prijs; het probleem\n"
                "   zit in de volatiliteit, niet in het prijsniveau."
            ),
        },
    ),
]


def ask(question: Question, number: int, total: int, rng: random.Random) -> bool:
    """Stelt één vraag en geeft terug of het antwoord goed was.

    De antwoordvolgorde wordt per sessie door elkaar gehusseld. Zonder dat
    staat het juiste antwoord altijd op dezelfde plek en kun je de toets
    halen zonder na te denken — precies wat een zelftoets waardeloos maakt.
    """
    order = list(range(len(question.options)))
    rng.shuffle(order)
    shuffled = [question.options[i] for i in order]
    correct_position = order.index(question.correct)

    print(f"\n{LINE}")
    print(f"VRAAG {number} van {total}  —  {question.topic}")
    print(LINE)
    print(f"\n{question.text}\n")

    for index, option in enumerate(shuffled):
        print(f"  {index + 1}. {option}")

    while True:
        try:
            raw = input(f"\nJouw antwoord (1-{len(question.options)}, of 'q' om te stoppen): ")
        except (EOFError, KeyboardInterrupt):
            print("\n\nGestopt.")
            raise SystemExit(0)

        raw = raw.strip().lower()
        if raw in {"q", "quit", "stop"}:
            print("\nGestopt. Je kunt altijd opnieuw beginnen.")
            raise SystemExit(0)

        if raw.isdigit() and 1 <= int(raw) <= len(question.options):
            chosen_position = int(raw) - 1
            break
        print(f"  Vul een getal van 1 tot {len(question.options)} in.")

    # Vertaal de gekozen positie terug naar de oorspronkelijke optie-index,
    # want why_wrong is op die oorspronkelijke nummering gebaseerd.
    chosen = order[chosen_position]
    correct = chosen == question.correct
    print()
    if correct:
        print("GOED.")
    else:
        print(f"NIET HELEMAAL. Het juiste antwoord is {correct_position + 1}.")
        if chosen in question.why_wrong:
            print(
                f"\nWaarom {chosen_position + 1} niet klopt:"
                f"\n   {question.why_wrong[chosen]}"
            )

    print(f"\n{question.explanation}")
    return correct


def main() -> int:
    """Draait de zelftoets."""
    print(LINE)
    print("ZELFTOETS — DE VIER BEVINDINGEN UIT FASE 1")
    print(LINE)
    print(
        "\nZes vragen. Geen examen: bij elk antwoord krijg je uitleg, ook als\n"
        "het goed was. Fout antwoorden is nuttiger dan gokken.\n"
        "\nTyp 'q' om te stoppen."
    )

    if not sys.stdin.isatty():
        print(
            "\nLET OP: dit script heeft je toetsenbord nodig.\n"
            "Draai het rechtstreeks in de terminal:\n"
            "    python scripts/zelftoets.py"
        )
        return 1

    score = 0
    wrong_topics: list[str] = []
    rng = random.Random()
    for index, question in enumerate(QUESTIONS, start=1):
        if ask(question, index, len(QUESTIONS), rng):
            score += 1
        else:
            wrong_topics.append(question.topic)

    print(f"\n{LINE}")
    print(f"KLAAR — {score} van de {len(QUESTIONS)} goed")
    print(LINE)

    if score == len(QUESTIONS):
        print(
            "\nAlles goed. De basis van fase 1 zit.\n"
            "\nJe bent klaar voor fase 2: waarom je de goudprijs niet zomaar\n"
            "tegen de rente mag regresseren (stationariteit)."
        )
    elif score >= len(QUESTIONS) - 2:
        print(
            f"\nDe basis zit grotendeels. Kijk nog even naar: "
            f"{', '.join(wrong_topics)}.\n"
            "\nStaat in docs/START_HIER.md — dat is één pagina."
        )
    else:
        print(
            f"\nNog een paar onderwerpen om na te lezen: {', '.join(wrong_topics)}.\n"
            "\nLees docs/START_HIER.md nog eens door en draai deze toets daarna\n"
            "opnieuw. Het is één pagina, en de vier bevindingen staan er in\n"
            "dezelfde volgorde als de vragen."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
