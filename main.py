from gemini_utils import gemini_prompt_lecture
import firestore_utils
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from firebase_admin import firestore, credentials
import firebase_admin
import os
import uuid
import time
from dotenv import load_dotenv
import gemini_utils
import veo_utils
import tts_utils
import uvicorn
import logging

class PollingEndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn access log args are typically: (client_addr, method, path, http_version, status_code)
        if record.args and len(record.args) >= 5:
            path = record.args[2]
            status_code = record.args[4]
            if isinstance(path, str) and ("get_event" in path or "get_game" in path):
                return status_code >= 400  # Only log if it's an error (400+)
        return True

logging.getLogger("uvicorn.access").addFilter(PollingEndpointFilter())

load_dotenv()

if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
    except Exception:
        cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/create_event")
def main_create_event(eventName: str = Form(...), eventId: str = Form(...), password: str = Form(...)):
    return firestore_utils.create_event(eventName=eventName, eventId=eventId, password=password)

@app.get("/get_events")
def main_get_events():
    return firestore_utils.get_events()

@app.get("/get_leaderboard")
def main_get_leaderboard(eventId: str):
    return firestore_utils.get_leaderboard(eventId)

@app.post("/create_game")
def main_create_game(eventId: str = Form(...), video_theme: str = Form(...), player1: str = Form(...), player2: str = Form(...), player3: Optional[str] = Form(None), language: str = Form("English")):
    return firestore_utils.create_game(eventId=eventId, video_theme=video_theme, player1=player1, player2=player2, player3=player3, language=language)

@app.post("/update_game_status")
def main_update_game_status(status: str = Form(...), game_id: str = Form(...)):
    return firestore_utils.update_game_status(status=status, game_id=game_id)

@app.get("/get_game_status")
def main_get_game_status(game_id: str):
    return(firestore_utils.get_game_status)

@app.get("/get_event")
def main_get_event(eventId: str):
    return firestore_utils.get_event(eventId)

@app.post("/set_active_game")
def main_set_active_game(eventId: str = Form(...), game_id: str = Form(...)):
    return firestore_utils.set_active_game(eventId, game_id)

@app.get("/get_game_rounds")
def main_get_game_rounds(eventId: str):
    return firestore_utils.get_game_rounds(eventId)

@app.get("/get_game_round")
def main_get_game_round(game_id: str):
    return firestore_utils.get_game_round(game_id)

@app.post("/update_game_round")
def main_update_game_round(game_id: str = Form(...), updates: str = Form(...)):
    import json
    updates_dict = json.loads(updates)
    return firestore_utils.update_game_round(game_id, updates_dict)

@app.delete("/remove_game_round")
def main_delete_game_round(game_id: str = Form(...)):
    firestore_utils.delete_game_round(game_id=game_id)

@app.post("/welcome_message")
def main_synthesize_welcome_message(game_id:str = Form(...), lang: str = Form(...)):
    return tts_utils.synthesize_welcome_message(game_id=game_id, lang=lang)

from typing import Optional, List, Union

# ... (inside app definition)

@app.post("/video_generator")
def video_generation(game_id: str = Form(...), player_num: str = Form(...), prompt: str = Form(...), reference_images: Optional[Union[List[str], str]] = Form(None)):
    return veo_utils.generate_and_upload_video(game_id=game_id, player_num=player_num, prompt=prompt, reference_images=reference_images)

@app.post("/post_video_gen_audio")
def main_synthesize_post_video_gen_audio(game_id: str = Form(...), lang: str = Form(...)):
    return tts_utils.synthesize_post_video_gen_audio(game_id=game_id, lang=lang), tts_utils.video_show_audio(game_id=game_id, lang=lang)

@app.post("/prompt_judger")
def prompt_judger(game_id: str = Form(...), player3: bool = Form(...)):
    return gemini_utils.judge_prompt(game_id=game_id, player3=player3)

@app.post("/prompt_lecture")
def prompt_lecturer(game_id: str = Form(...), lang: str = Form(...)):
    return gemini_utils.gemini_prompt_lecture(game_id=game_id, lang=lang)

@app.post("/video_judger")
def video_judger(game_id: str = Form(...), player3: bool = Form(...)):
    return gemini_utils.judge_videos(game_id=game_id, player3=player3)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
