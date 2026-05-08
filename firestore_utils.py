from firebase_admin import firestore, credentials
import firebase_admin
import os
import uuid
from dotenv import load_dotenv
import logging

# Set up logging to help debug in Cloud Run
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Get the database ID
firestore_db_id = os.getenv("FIRESTORE_ID")

if not firestore_db_id:
    logger.warning("FIRESTORE_ID not found in environment. Falling back to (default).")
else:
    logger.info(f"Connecting to Firestore database: {firestore_db_id}")

if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin: {e}")
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

db = firestore.client(database_id=firestore_db_id)

def player_score(eventId: str, player_name: str, total_score: int, consistency_score: int, fluidity_score: int, detail_score: int):
    player_scores = {
        "total_score" : total_score,
        "consistency_score": consistency_score,
        "fluidity_score": fluidity_score,
        "detail_score": detail_score,
    }
    
    player_data = {
        "player_name": player_name,
        "player_scores": player_scores,
        "updated_at": firestore.SERVER_TIMESTAMP
    }

    # Sanitize player name for map key
    safe_name = player_name.replace(".", "_")

    db.collection("leaderboards").document(eventId).set({
        "players": {
            safe_name: player_data
        },
        "last_updated": firestore.SERVER_TIMESTAMP
    }, merge=True)
    
    return f"Logged score for {player_name}: {total_score}"

def get_leaderboard(eventId: str):
    doc = db.collection("leaderboards").document(eventId).get()
    if not doc.exists:
        return []
    
    data = doc.to_dict()
    players_dict = data.get("players", {})
    
    leaderboard_list = []
    for safe_name, details in players_dict.items():
        player_scores = details.get("player_scores", {})
        player_info = {
            "player_name": details.get("player_name"),
            "total_score": player_scores.get("total_score", 0),
            "consistency_score": player_scores.get("consistency_score", 0),
            "fluidity_score": player_scores.get("fluidity_score", 0),
            "detail_score": player_scores.get("detail_score", 0),
        }
        leaderboard_list.append(player_info)
    
    # Sort by total_score descending
    leaderboard_list.sort(key=lambda x: x["total_score"], reverse=True)
    
    return leaderboard_list[:10]

tools_map = {"player_score": player_score}

def create_event(eventName: str, eventId: str, password: str):
    eventData = {
        "eventName": eventName,
        "eventId": eventId,
        "created_at": firestore.SERVER_TIMESTAMP,
        "password": password
    }
    db.collection("events").document(eventId).set(eventData)
    return {"status": "success", "eventId": eventId}

def get_events():
    event_ref = db.collection('events')
    events = event_ref.stream()
    event_list = []
    for event in events:
        data = event.to_dict()
        if 'created_at' in data and data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        event_list.append(data)
    return event_list

def create_game(eventId: str, video_theme: str, player1: str, player2: str, player3: str, language: str):
    game_id = f"ai-video-gen-round-{uuid.uuid4()}"
    
    game_data = {
        "eventId": eventId,
        "videoTheme": video_theme,
        "player1": player1,
        "player2": player2,
        "player3": player3,
        "created_at": firestore.SERVER_TIMESTAMP,
        "language": language,
        "game_status": "just_created"
    }
    db.collection("game_rounds").document(game_id).set(game_data)
    return {"status": "success", "game_id": game_id}

def update_game_status(status: str, game_id: str):
    game_ref = db.collection("game_rounds").document(game_id)
    game_ref.update({"game_status": status})
    return {"status": "success"}

def get_game_status(game_id: str):
    doc_ref = db.collection("game_rounds").document(game_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("game_status")
    raise HTTPException(status_code=404, detail="Game not found")
    
def get_event(eventId: str):
    doc = db.collection("events").document(eventId).get()
    if doc.exists:
        data = doc.to_dict()
        if 'created_at' in data and data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        return data
    return None

def set_active_game(eventId: str, game_id: str):
    db.collection("events").document(eventId).update({"activeGameId": game_id})
    return {"status": "success"}

def get_game_rounds(eventId: str):
    try:
        from google.cloud.firestore_v1.base_query import FieldFilter
        rounds = db.collection("game_rounds").where(filter=FieldFilter("eventId", "==", eventId)).stream()
    except ImportError:
        rounds = db.collection("game_rounds").where("eventId", "==", eventId).stream()
        
    rounds_list = []
    for r in rounds:
        data = r.to_dict()
        data["id"] = r.id
        if 'created_at' in data and data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        rounds_list.append(data)
    return rounds_list

def get_game_round(game_id: str):
    doc = db.collection("game_rounds").document(game_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        if 'created_at' in data and data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        return data
    return None

def update_game_round(game_id: str, updates: dict):
    db.collection("game_rounds").document(game_id).update(updates)
    return {"status": "success"}

def delete_game_round(game_id: str):
    doc_ref = db.collection("game_rounds").document(game_id)
    doc_ref.delete()