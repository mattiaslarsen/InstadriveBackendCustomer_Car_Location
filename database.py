# database.py
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from paths import DATA_DIR

# Ladda miljövariabler från .env
load_dotenv()

# Säkerställ att Data-katalogen finns
DATA_DIR.mkdir(exist_ok=True)

# Hämta databasURL från .env
database_url = os.getenv('DATABASE_URL', 'sqlite:///./Data/instadrive.db')

# Skriv ut konfiguration vid uppstart (hjälpsamt för debugging)
print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
print(f"Database URL: {database_url}")

# Skapa databasmotorn
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False}  # Behövs för SQLite
)

# Skapa sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    from models import Base
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {database_url}")

# Dependency för FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()