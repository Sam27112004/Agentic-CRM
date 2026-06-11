import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.models import Contact
from backend.database import SessionLocal

def seed_contacts():
    db = SessionLocal()
    
    contacts_data = [
        {"email": "bob.jones@enterprise.net", "name": "Bob Jones", "company": "Enterprise Net", "status": "VIP", "account_value": 84000, "churn_risk_score": 0.1},
        {"email": "alice.smith@greenlight-npo.org", "name": "Alice Smith", "company": "Greenlight NPO", "status": "Active", "account_value": 12000, "churn_risk_score": 0.2},
        {"email": "karen.w@retail-co.com", "name": "Karen W.", "company": "Retail Co", "status": "Active", "account_value": 6000, "churn_risk_score": 0.4},
        {"email": "marcus.del@fintech-startup.co", "name": "Marcus Del", "company": "Fintech Startup", "status": "Active", "account_value": 25000, "churn_risk_score": 0.15},
    ]

    for data in contacts_data:
        existing = db.query(Contact).filter_by(email=data["email"]).first()
        if not existing:
            contact = Contact(**data)
            db.add(contact)
    
    db.commit()
    print("Successfully seeded 4 contacts!")

if __name__ == "__main__":
    seed_contacts()
