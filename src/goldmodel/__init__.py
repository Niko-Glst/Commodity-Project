"""Kwantitatief model voor het analyseren en simuleren van goudprijzen.

Dit pakket is opgebouwd in vier lagen:

1. ``data``       — ophalen en cachen van macro- en prijsreeksen (fase 1)
2. ``explore``    — verkennende analyse: stationariteit, autocorrelatie (fase 2)
3. ``models``     — regressiemodellen: OLS/Newey-West, VAR, regularisatie (fase 3)
4. ``simulate``   — Monte Carlo met t-schokken en GARCH (fase 4)

De validatielaag (walk-forward backtesting, benchmarkvergelijking) loopt
dwars door lagen 3 en 4 heen en zit in ``validation``.

Op dit moment is alleen laag 1 geïmplementeerd.
"""

__version__ = "0.1.0"
