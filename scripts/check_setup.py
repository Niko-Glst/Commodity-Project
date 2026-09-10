"""Controleert of de installatie klopt: pakketten, API-sleutel, netwerk, cache.

Draai dit als eerste na het opzetten van het project, of wanneer iets niet
werkt. Het script zegt per onderdeel of het goed is en wat je moet doen als
het dat niet is.

Gebruik:
    python scripts/check_setup.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

OK = "[OK]  "
FOUT = "[FOUT]"
LET_OP = "[!]   "


def check_python() -> bool:
    """Controleert de Python-versie."""
    version = sys.version_info
    if version >= (3, 11):
        print(f"{OK} Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"{FOUT} Python {version.major}.{version.minor} is te oud; 3.11 of hoger nodig.")
    return False


def check_packages() -> bool:
    """Controleert of alle benodigde pakketten geïnstalleerd zijn."""
    required = {
        "pandas": "pandas",
        "numpy": "numpy",
        "pyarrow": "pyarrow",
        "yfinance": "yfinance",
        "requests": "requests",
        "dotenv": "python-dotenv",
        "statsmodels": "statsmodels",
        "scipy": "scipy",
        "sklearn": "scikit-learn",
        "arch": "arch",
        "matplotlib": "matplotlib",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if not missing:
        print(f"{OK} Alle {len(required)} pakketten geïnstalleerd")
        return True

    print(f"{FOUT} Ontbrekende pakketten: {', '.join(missing)}")
    print("       Oplossing: pip install -r requirements.txt")
    return False


def check_env_file() -> bool:
    """Controleert of .env bestaat en een FRED-sleutel bevat."""
    env_path = PROJECT_ROOT / ".env"

    if not env_path.exists():
        print(f"{FOUT} Het bestand .env bestaat niet.")
        print("       Oplossing: kopieer .env.example naar .env en vul je sleutel in.")
        return False

    from goldmodel.config import get_fred_api_key

    key = get_fred_api_key()
    if not key:
        print(f"{LET_OP} .env bestaat, maar FRED_API_KEY is leeg.")
        print("       Vul je sleutel in achter 'FRED_API_KEY=' in het bestand .env")
        print("       Gratis aanvragen: https://fredaccount.stlouisfed.org/apikeys")
        print("       Zonder sleutel werken alleen de yfinance-reeksen.")
        return False

    if len(key) != 32 or not key.isalnum():
        print(f"{LET_OP} FRED_API_KEY gevonden, maar ziet er ongebruikelijk uit.")
        print(f"       Verwacht: 32 letters/cijfers. Gevonden: {len(key)} tekens.")
        print("       Controleer of je de sleutel volledig hebt geplakt.")
        return False

    print(f"{OK} FRED_API_KEY gevonden ({key[:4]}...{key[-4:]})")
    return True


def check_gitignore() -> bool:
    """Controleert of .env buiten versiebeheer blijft."""
    gitignore = PROJECT_ROOT / ".gitignore"
    if not gitignore.exists():
        print(f"{FOUT} Geen .gitignore — je sleutel kan per ongeluk gecommit worden.")
        return False

    content = gitignore.read_text(encoding="utf-8")
    if ".env" in content:
        print(f"{OK} .env staat in .gitignore (je sleutel blijft privé)")
        return True

    print(f"{FOUT} .env staat NIET in .gitignore. Voeg de regel '.env' toe.")
    return False


def check_fred_connection() -> bool:
    """Doet één echte call naar FRED om de sleutel te testen."""
    from goldmodel.config import get_fred_api_key
    from goldmodel.data.fred_client import FredClient, FredDataError

    key = get_fred_api_key()
    if not key:
        print(f"{LET_OP} FRED-verbinding niet getest (geen sleutel)")
        return False

    try:
        client = FredClient(key, max_retries=1)
        # Kleine testcall: één maand data van een korte reeks.
        frame = client.fetch_series("DFF", start_date="2024-01-01", end_date="2024-01-31")
        print(f"{OK} FRED-verbinding werkt ({len(frame)} testwaarnemingen opgehaald)")
        return True
    except FredDataError as exc:
        message = str(exc)
        print(f"{FOUT} FRED weigert de sleutel of is onbereikbaar.")
        if "api_key" in message.lower() or "400" in message:
            print("       De sleutel lijkt ongeldig. Controleer of je hem")
            print("       volledig en zonder spaties hebt geplakt in .env")
        else:
            print(f"       Melding: {message[:150]}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"{FOUT} Onverwachte fout bij FRED: {str(exc)[:150]}")
        return False


def check_yahoo_connection() -> bool:
    """Doet één echte call naar Yahoo Finance."""
    from goldmodel.data.yahoo_client import YahooClient

    try:
        client = YahooClient(max_retries=1)
        frame = client.fetch_series("GC=F", start_date="2024-01-01", end_date="2024-01-31")
        print(f"{OK} Yahoo Finance werkt ({len(frame)} testwaarnemingen opgehaald)")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"{LET_OP} Yahoo Finance onbereikbaar: {str(exc)[:100]}")
        print("       Geen sleutel nodig; waarschijnlijk een tijdelijke storing.")
        return False


def check_cache() -> bool:
    """Controleert of de cachemap schrijfbaar is."""
    from goldmodel.config import get_cache_dir
    from goldmodel.data.cache import ParquetCache

    try:
        cache_dir = get_cache_dir()
        cache = ParquetCache(cache_dir)
        summary = cache.summary()
        count = len(summary)
        print(f"{OK} Cache schrijfbaar: {cache_dir}")
        if count:
            print(f"       {count} reeks(en) opgeslagen")
        else:
            print("       Nog leeg — draai scripts/fetch_data.py om te vullen")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"{FOUT} Cachemap niet bruikbaar: {str(exc)[:150]}")
        return False


def main() -> int:
    """Voert alle controles uit."""
    print("=" * 70)
    print("CONTROLE VAN DE INSTALLATIE")
    print("=" * 70)
    print()

    print("Basis:")
    python_ok = check_python()
    packages_ok = check_packages()
    print()

    if not packages_ok:
        print("Los eerst de ontbrekende pakketten op; de rest is dan pas te testen.")
        return 1

    print("Configuratie:")
    check_gitignore()
    key_ok = check_env_file()
    print()

    print("Verbindingen:")
    fred_ok = check_fred_connection()
    yahoo_ok = check_yahoo_connection()
    print()

    print("Opslag:")
    cache_ok = check_cache()
    print()

    print("=" * 70)
    if python_ok and packages_ok and key_ok and fred_ok and yahoo_ok and cache_ok:
        print("ALLES IN ORDE — draai nu: python scripts/fetch_data.py")
        return 0
    if yahoo_ok and cache_ok:
        print("GEDEELTELIJK IN ORDE")
        print("Je kunt al werken met de yfinance-reeksen (goud, zilver, VIX, S&P 500).")
        print("Vul de FRED-sleutel in om ook de macro-reeksen op te halen.")
        return 0
    print("ER ZIJN PROBLEMEN — zie de meldingen hierboven.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
