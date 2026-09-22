"""Van voorspelling naar positie.

Wat dit doet
------------
Een regressie geeft een verwacht rendement. Dat is nog geen positie: je moet
beslissen hoe groot je gaat, wanneer je niet handelt, en hoe je omgaat met een
signaal dat vrijwel nul is.

Deze module doet die vertaling, en houdt hem expliciet gescheiden van de
backtest. Reden: een positieregel is een keuze met vrijheidsgraden (drempel,
schaling, maximum), en elke vrijheidsgraad is een kans om te overfitten. Door
ze hier te isoleren zijn ze zichtbaar in plaats van verstopt in de backtest.

De waarschuwing die erbij hoort
-------------------------------
Fase 3 heeft al gemeten dat het onderliggende signaal geen voorspelkracht
heeft: directional accuracy 43,8%, out-of-sample R-kwadraat -0,04. Een
positieregel maakt dat niet beter. Wat deze module oplevert is dus geen
strategie maar een **meetinstrument**: het vertaalt "geen signaal" naar
"hoeveel geld kost het om er toch op te handelen".

Dat is een zinvolle uitkomst, maar het is iets anders dan wat een
tradingsysteem doet.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class SignalSettings:
    """Instellingen voor de vertaling van voorspelling naar positie.

    Attributen:
        method: Hoe de voorspelling naar een positie gaat.
            'sign'      +1 of -1, puur de richting
            'linear'    proportioneel aan de voorspelling, geschaald
            'threshold' alleen handelen boven een drempel, anders vlak
        max_position: Maximale absolute positie, als fractie van het
            kapitaal. 1,0 betekent voluit long of short.
        threshold_sigma: Bij 'threshold': hoeveel standaardafwijkingen de
            voorspelling moet afwijken van nul voordat je handelt. Deze
            drempel is een vrijheidsgraad — zie de waarschuwing hieronder.
        scale_by: Bij 'linear': door welke grootheid je deelt om de
            voorspelling naar een positie te schalen. 'prediction_std'
            gebruikt de spreiding van de voorspellingen zelf.

    Over de drempel
    ---------------
    De drempel is verleidelijk: hij onderdrukt ruis en verlaagt de kosten.
    Maar hij is ook een parameter die je kunt optimaliseren op dezelfde data
    waarop je test, en dan meet je je eigen keuzevrijheid in plaats van een
    signaal.

    In ``backtest.py`` wordt de drempel daarom NIET geoptimaliseerd; hij staat
    vast op een waarde die vooraf gekozen is, en de gevoeligheid ervoor wordt
    apart gerapporteerd.
    """

    method: str = "linear"
    max_position: float = 1.0
    threshold_sigma: float = 0.5
    scale_by: str = "prediction_std"


def predictions_to_positions(
    predictions: pd.Series,
    settings: SignalSettings | None = None,
    *,
    reference_std: float | None = None,
) -> pd.Series:
    """Zet voorspelde rendementen om in gewenste posities.

    Argumenten:
        predictions: Voorspeld rendement per dag. Moet al out-of-sample zijn:
            deze functie kijkt niet of dat zo is.
        settings: Positieregel.
        reference_std: Spreiding om mee te schalen. None berekent hem uit de
            voorspellingen zelf — let op dat dat strikt genomen informatie uit
            de hele reeks gebruikt. Voor een zuivere walk-forward geef je de
            spreiding uit de trainingsperiode mee.

    Geeft terug:
        Reeks met de gewenste positie per dag, tussen -max_position en
        +max_position. Dit is de positie die je WILT hebben op basis van de
        informatie van die dag; de executie-lag wordt in de backtest
        toegepast, niet hier.
    """
    settings = settings or SignalSettings()
    predictions = predictions.dropna()

    if settings.method == "sign":
        positions = np.sign(predictions) * settings.max_position

    elif settings.method == "linear":
        spread = (
            reference_std
            if reference_std is not None
            else float(predictions.std())
        )
        if spread == 0:
            positions = pd.Series(0.0, index=predictions.index)
        else:
            positions = (predictions / spread).clip(
                -settings.max_position, settings.max_position
            )

    elif settings.method == "threshold":
        spread = (
            reference_std
            if reference_std is not None
            else float(predictions.std())
        )
        if spread == 0:
            positions = pd.Series(0.0, index=predictions.index)
        else:
            standardised = predictions / spread
            positions = np.sign(standardised) * settings.max_position
            positions = positions.where(
                standardised.abs() >= settings.threshold_sigma, 0.0
            )

    else:
        raise ValueError(
            f"Onbekende methode: {settings.method!r}. "
            "Kies 'sign', 'linear' of 'threshold'."
        )

    return pd.Series(positions, index=predictions.index, name="position")


def turnover(positions: pd.Series) -> pd.Series:
    """Hoeveel de positie per dag verandert.

    Dit bepaalt de transactiekosten: elke verandering is een transactie. Een
    strategie met een omzet van 2,0 per dag draait haar hele boek twee keer
    om, en betaalt dat ook.
    """
    return positions.diff().abs().fillna(positions.abs())


def position_statistics(positions: pd.Series) -> dict:
    """Beschrijvende statistieken van de positiereeks.

    Nuttig om te zien of een strategie eigenlijk wel handelt, en hoe vaak ze
    van kant wisselt.
    """
    changes = turnover(positions)
    non_zero = positions[positions != 0]

    return {
        "n_days": int(len(positions)),
        "n_days_in_market": int((positions != 0).sum()),
        "share_in_market": float((positions != 0).mean()),
        "mean_abs_position": float(positions.abs().mean()),
        "mean_daily_turnover": float(changes.mean()),
        "annual_turnover": float(changes.mean() * 252),
        "n_sign_flips": int((np.sign(non_zero).diff().abs() > 0).sum())
        if len(non_zero) > 1
        else 0,
    }
