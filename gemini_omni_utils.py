from google import genai
from google.genai import types
from firestore_utils import db
import os
from dotenv import load_dotenv
import gcs_utils
from fastapi import HTTPException
from uuid import uuid4
import asyncio
import requests
import time
import base64
from typing import Optional, List, Union

load_dotenv()

# Create Retry Options in case of a 429 error
retry_options = types.HttpRetryOptions(
    attempts=3,
    http_status_codes=[429, 500, 502, 503, 504],
    exp_base=1,
    initial_delay=5.0
)

http_options = types.HttpOptions(
    retry_options=retry_options
)

# Set up Agent Platform Clients and Video Bucket
client = genai.Client(
    enterprise=True,
    project=os.getenv("PROJECT_ID"),
    location="global",
    http_options=http_options
)

aclient = client.aio

video_bucket = os.getenv("VIDEO_BUCKET")


async def generate_and_upload_video(
    game_id: str,
    player_num: str,
) -> dict:
    '''
    Fetches the game round from firestore and uses a player's prompt to generate a video with Gemini Omni
    and upload it to GCS

    Args:
      game_id(str): The game round in Firestore,
      player_num(str): The identifier of the player submitting the prompt (e.g. player1, player2)
    '''
    try:
        doc_ref = db.collection("game_rounds").document(game_id)
        doc = doc_ref.get()
        doc_data = doc.to_dict() or {}
        prompt = doc_data.get(f"{player_num}_prompt", "")
        img_path = doc_data.get(f"{player_num}_image")

        # Process optional reference image
        public_image_url = None
        gs_uri = None
        mime_type = "image/png"

        if img_path:
            clean_path = img_path.replace("/images/", "").lstrip('/')
            if "https://storage.googleapis.com/" in clean_path:
                gs_uri = clean_path.replace("https://storage.googleapis.com/", "gs://")
            elif clean_path.startswith("gs://"):
                gs_uri = clean_path
            else:
                gs_uri = f"gs://ai-video-gen-challenge-ref-images/{clean_path}"

            public_image_url = gs_uri.replace("gs://", "https://storage.googleapis.com/")

            ext = clean_path.split('?')[0].split('.')[-1].lower()
            if ext in ['jpeg', 'jpg']:
                mime_type = "image/jpeg"
            elif ext == 'webp':
                mime_type = "image/webp"

        inputs = []
        if gs_uri:
            inputs.append({"type": "image", "uri": gs_uri, "mime_type": mime_type})
            task = "reference_to_video"
        else:
            task = "text_to_video"

        inputs.append({"type": "text", "text": prompt})

        # Config Retry limits for Gemini Omni Generation
        MAX_ATTEMPTS = 1
        attempts = 0
        omni_success = False
        video_data = None
        OMNI_TIMEOUT_SECONDS = 75

        while attempts < MAX_ATTEMPTS and not omni_success:
            attempts += 1
            print(f"Attempt {attempts}/{MAX_ATTEMPTS} for Gemini Omni Generation ({player_num})")

            try:
                response = await aclient.interactions.create(
                    model="gemini-omni-1.1-flash-preview",
                    input=inputs,
                    background=True,
                    generation_config={
                        "video_config": {
                            "task": task,
                        }
                    },
                    response_format={
                        "type": "video",
                        "aspect_ratio": "16:9",
                    }
                )

                interaction_id = response.id
                start_time = time.time()
                while True:
                    elapsed = int(time.time() - start_time)
                    if elapsed > OMNI_TIMEOUT_SECONDS:
                        raise TimeoutError(f"Gemini Omni generation timed out after {elapsed}s for {player_num}. Triggering Seedance fallback.")

                    response = await aclient.interactions.get(id=interaction_id)
                    if response.status == "completed":
                        break
                    elif response.status == "failed":
                        raise RuntimeError(f"Gemini Omni generation failed for {player_num}: {getattr(response, 'errors', 'Unknown error')}")
                    print(f"Waiting for video processing ({player_num})... status: {response.status} ({elapsed}s)")
                    await asyncio.sleep(5)

                if response.output_video and getattr(response.output_video, "data", None):
                    video_data = base64.b64decode(response.output_video.data)
                    omni_success = True
                    print(f"Successfully generated video using Gemini Omni for {player_num} in {int(time.time() - start_time)}s!")

                if not omni_success:
                    raise Exception("Gemini Omni interaction completed but output_video data was not found.")
           
           # Handling a 429 Error and logging attempt number
            except (ResourceExhausted, Exception) as e:
                if isinstance(e, ResourceExhausted):
                    print(f"ResourceExhausted (429) on attempt {attempts} for {player_num}")
                else:
                    print(f"Gemini Omni attempt {attempts}/{MAX_ATTEMPTS} error for {player_num}: {str(e)}")

                if attempts < MAX_ATTEMPTS:
                    await asyncio.sleep(3)

        # If the request was successful
        if video_data:
            video_url = await asyncio.to_thread(gcs_utils.upload_video_to_gcs, video_data, content_type="video/mp4")
            await asyncio.sleep(5)


            filename = video_url.split('/')[-1]
            gs_uri_stored = f"gs://{video_bucket}/{filename}"

            game_ref = db.collection("game_rounds").document(game_id)
            update_data = {
                f"{player_num}_video": gs_uri_stored,
                f"{player_num}_prompt": prompt
            }
            await asyncio.to_thread(game_ref.update, update_data)
            print(f"Successfully saved {player_num} video to Firestore.")

            return {
                "status": "success",
                "video_url": video_url,
                "qr_code_base64": await asyncio.to_thread(gcs_utils.generate_qr_base64, social_url)
            }
        else:
            raise Exception("No video generated in the response")
   
    # If no video generated after 3 attempts
    except Exception as e:
        import traceback
        print(f"Error in video generation for {player_num}: {str(e)}\n{traceback.format_exc()}")
        try:
            game_ref = db.collection("game_rounds").document(game_id)
            game_ref.set({"video_generation_failed": True}, merge=True)
            print(f"Successfully updated Firestore with video_generation_failed: True for game {game_id}")
        except Exception as update_err:
            print(f"Failed to update video_generation_failed flag in Firestore: {update_err}")
        raise HTTPException(status_code=500, detail=str(e))