import sys
import logging
from backend.database import SessionLocal
from backend.models import Email
from backend.services.job_processor import JobProcessor

logging.basicConfig(level=logging.DEBUG)

db = SessionLocal()
# find a pending email
email = db.query(Email).filter(Email.status == "Received").first()
if email:
    try:
        from backend.services.llm_classifier import classify_email
        res = classify_email(db, email.id)
        print("Success:", res)
    except Exception as e:
        print("Exception:", e)
        import traceback
        traceback.print_exc()
else:
    print("No pending emails found")
