from flask import Blueprint, request, jsonify
from models import CustomerPreference, db

preferences_bp = Blueprint('preferences', __name__)

@preferences_bp.route('/preferences', methods=['POST'])
def set_preferences():
    user_id = request.json.get('user_id')
    submitted_prefs = request.json.get('preferences')
    stored = CustomerPreference.query.filter_by(user_id=user_id).first()
    if stored and stored.preferences == submitted_prefs:
        # Prefer 204 No Content; fallback to 200 OK
        return ('', 204)
    if stored:
        stored.preferences = submitted_prefs
    else:
        stored = CustomerPreference(user_id=user_id, preferences=submitted_prefs)
        db.session.add(stored)
    db.session.commit()
    # Emit preference update event only if updated
    return jsonify({'status': 'updated'})
