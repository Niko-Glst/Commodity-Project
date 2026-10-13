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

    Over de no-trade band
    ---------------------
    ``no_trade_band`` is standaard 0,0: uit. Staat hij aan, dan blijft de
    positie ongewijzigd zolang de gewenste positie minder dan deze fractie
    afwijkt van de huidige. Dat onderdrukt het voortdurend bijschaven dat de
    'linear'-methode veroorzaakt.

    Dit is een OPTIE, geen correctie. Zie ``docs/RESULTS.md``: de band is één
    keer gedraaid om de omvang van het kosteneffect te laten zien, en er is
    geen waarde gezocht die de uitkomst gunstig maakt. Het onderliggende
    signaal blijft waardeloos, en een lagere omzet maakt een nulsignaal niet
    winstgevend — alleen goedkoper.
    """

    method: str = "linear"
    max_position: float = 1.0
    threshold_sigma: float = 0.5
    scale_by: str = "prediction_std"
    no_trade_band: float = 0.0


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

    positions = pd.Series(positions, index=predictions.index, name="position")

    if settings.no_trade_band > 0:
        positions = apply_no_trade_band(positions, settings.no_trade_band)

    return positions


def apply_no_trade_band(positions: pd.Series, band: float) -> pd.Series:
    """Houdt de positie vast zolang de gewenste wijziging klein is.

    Waarom dit nodig kan zijn
    -------------------------
    De 'linear'-methode schaalt de positie proportioneel aan de voorspelling.
    Die voorspelling verandert elke dag een beetje, dus de positie ook — ook
    als er niets zinnigs veranderd is. Het resultaat is een omzet van 181x per
    jaar, waarvan het grootste deel bestaat uit minieme aanpassingen die hun
    eigen transactiekosten niet waard zijn.

    De band legt een drempel op de WIJZIGING in plaats van op het signaal:
    verandert de gewenste positie minder dan ``band``, dan gebeurt er niets.

    Let op wat dit niet is
    ----------------------
    Dit maakt het signaal niet beter. Het maakt handelen goedkoper. Een
    signaal dat bruto exact nul oplevert, levert met minder kosten nog steeds
    ongeveer nul op — alleen minder negatief. Dat is precies waarom deze band
    als optie bestaat en niet als standaardinstelling.

    Argumenten:
        positions: De gewenste positie per dag, zonder band.
        band: Minimale wijziging voordat er gehandeld wordt, in dezelfde
            eenheid als de positie. 0,10 betekent: pas handelen als de
            gewenste positie meer dan 0,10 afwijkt van de huidige.

    Geeft terug:
        De werkelijk aangehouden positie per dag.
    """
    if band <= 0:
        return positions

    desired = positions.to_numpy(dtype=float)
    held = np.empty_like(desired)

    # De eerste dag is er nog geen positie om aan vast te houden.
    current = desired[0] if len(desired) else 0.0
    held[0] = current

    for i in range(1, len(desired)):
        if abs(desired[i] - current) >= band:
            current = desired[i]
        held[i] = current

    return pd.Series(held, index=positions.index, name="position")


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
