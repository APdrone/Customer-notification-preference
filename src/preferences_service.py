from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from .models import Preference, Customer
from .database import get_db

router = APIRouter()

@router.put("/preferences/{customer_id}")
def update_preferences(customer_id: int, submitted_prefs: dict, db: Session = Depends(get_db)):
    stored_prefs = db.query(Preference).filter_by(customer_id=customer_id).first()
    # Compare submitted preferences with stored values for idempotency
    if stored_prefs and stored_prefs.values == submitted_prefs:
        # No change: Return 204 No Content, do not update DB or emit event
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    elif not stored_prefs:
        # New preference: Create
        new_pref = Preference(customer_id=customer_id, values=submitted_prefs)
        db.add(new_pref)
    else:
        # Changed prefs: Update
        stored_prefs.values = submitted_prefs
    db.commit()
    # emit_audit_event(customer_id, submitted_prefs)
    return {"status": "success"}
