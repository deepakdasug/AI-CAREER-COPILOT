from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# 1. Cleaned up URL: Using PyMySQL's native SSL verification flags
DATABASE_URL = 'mysql+pymysql://2N3JjeTTyhJwnL4.root:03vtmdN3SuDR64qe@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'

# 2. Setup Engine
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True  # Automatically checks & repairs dropped connections
)

# 3. Setup Session and Base
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
Base.metadata.drop_all(engine)
