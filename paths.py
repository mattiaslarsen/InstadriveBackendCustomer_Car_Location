# paths.py

from pathlib import Path

# Rotkatalogen för projektet (denna fil ligger i rotkatalogen)
ROOT = Path(__file__).parent

# Underkataloger inom projektet
SERV_DIR = ROOT / "Services"
TEST_DIR = ROOT / "Tests"
DATA_DIR = ROOT / "Data"

# Funktioner för att hämta dynamiska sökvägar för specifika filer i varje katalog
def service_file(filename: str) -> Path:
    return SERV_DIR / filename

def test_file(filename: str) -> Path:
    return TEST_DIR / filename

def data_file(filename: str) -> Path:
    return DATA_DIR / filename