import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. Get DATABASE_URL from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# 2. Setup Engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True  # Automatically checks & repairs dropped connections
)

# 3. Setup Session and Base
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
