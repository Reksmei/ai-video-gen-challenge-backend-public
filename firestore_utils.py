Copyright [Year] [Your Name]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://apache.org

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

from firebase_admin import firestore, credentials
import firebase_admin
import os
import uuid
import time
from dotenv import load_dotenv
import logging

# Set up logging to help debug in Cloud Run/Prod
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Note that on the Backend, the firestore logic is solely for write operations. 
# For minimum latency and avoiding disconnection, I recommend to use the onSnapshot Cloud Firestore method from the Frontend with an API Key for read operations, 
# including getting the current events, games and game status.

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
    game_ref.set({"game_status": status}, merge=True)
    return {"status": "success"}



def set_active_game(eventId: str, game_id: str):
    db.collection("events").document(eventId).set({"activeGameId": game_id}, merge=True)
    return {"status": "success"}



def get_game_round(game_id: str):
    doc = db.collection("game_rounds").document(game_id).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        if 'created_at' in data and data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        data["server_time"] = int(time.time() * 1000)
        return data
    return None

def update_game_round(game_id: str, updates: dict):
    db.collection("game_rounds").document(game_id).set(updates, merge=True)
    return {"status": "success"}

def delete_game_round(game_id: str):
    doc_ref = db.collection("game_rounds").document(game_id)
    doc_ref.delete()
