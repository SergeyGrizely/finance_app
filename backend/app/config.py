import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://finance_user:finance_pass@db:5432/finance_db")
SECRET_KEY = os.getenv("SECRET_KEY", "4133")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
ALGORITHM = "HS256"
