import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.database import SessionLocal
from sqlalchemy import text

def reset_inbox():
    db = SessionLocal()
    try:
        print("Clearing inbox data (emails, threads, actions, drafts, jobs, audit_log)...")
        # Use TRUNCATE CASCADE to efficiently clear out the tables while handling foreign keys
        db.execute(text("TRUNCATE emails, threads, actions, drafts, processing_jobs, audit_log RESTART IDENTITY CASCADE;"))
        db.commit()
        print("Inbox reset successful! Your contacts and knowledge base chunks are still intact.")
    except Exception as e:
        db.rollback()
        print(f"Failed to reset inbox: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_inbox()
