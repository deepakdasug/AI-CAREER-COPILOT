import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. Get DATABASE_URL from environment variables, fallback to SQLite for local testing
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///career_copilot.db')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# 2. Setup Engine (with different settings for SQLite vs MySQL)
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True  # Automatically checks & repairs dropped connections
    )

# 3. Setup Session and Base
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
