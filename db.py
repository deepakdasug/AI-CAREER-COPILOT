import os
from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. Get DATABASE_URL from environment variables, fallback to SQLite for local testing
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///career_copilot.db')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

def normalize_database_url(database_url):
    url = make_url(database_url)
    if url.drivername in ("mysql", "mysql+mysqldb"):
        url = url.set(drivername="mysql+pymysql")
    return url


# 2. Setup Engine (with different settings for SQLite vs MySQL)
engine_url = normalize_database_url(DATABASE_URL)
if engine_url.get_backend_name() == "sqlite":
    engine = create_engine(engine_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        engine_url,
        pool_pre_ping=True  # Automatically checks & repairs dropped connections
    )

# 3. Setup Session and Base
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
