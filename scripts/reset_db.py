"""Utility to reset the database."""

from app.core.database import engine, Base
from sqlalchemy import text

def reset_db():
    print("Resetting database...")
    with engine.connect() as conn:
        # Drop all tables
        # Use CASCADE to ensure everything is removed
        conn.execute(text("DROP TABLE IF EXISTS mail_logs CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS enrollments CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS exams CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS students CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS courses CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS research_indicators CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS budgets CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS partnerships CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS financial_reports CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS rankings CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS employees CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS contracts CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS absenteeism CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS employment_outcomes CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS esg_metrics CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS carbon_footprint CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS energy_consumption CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS recycling_statistics CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS inventory_items CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS equipment CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS facility_health CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS chat_messages CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS chat_sessions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS automation_actions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS workflows CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS workflow_executions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS orchestrations CASCADE"))
        conn.commit()
    # Recreate all tables using the Database manager's logic
    print("Recreating all tables...")
    from app.core.database import db
    db.create_tables()
    print("Database reset and recreation complete.")

if __name__ == "__main__":
    reset_db()
