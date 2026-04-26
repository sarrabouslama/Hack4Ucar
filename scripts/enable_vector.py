from sqlalchemy import create_engine, text
from app.config import settings

def enable_vector():
    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as conn:
            print("Trying to enable pgvector...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("Successfully enabled pgvector")
    except Exception as e:
        print(f"Error enabling pgvector: {e}")

if __name__ == "__main__":
    enable_vector()
