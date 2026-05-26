from google import genai
from google.genai import types
from google.genai.types import GenerateVideosConfig
from google.genai.types import Image as GenaiImage
import gcs_utils
import time
from typing import Optional, List, Union
from fastapi import HTTPException
from firestore_utils import db
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Configure retry options if Veo fails
retry_options = types.HttpRetryOptions(
    initial_delay=5.0, 
    attempts=3, 
    exp_base=1,
    http_status_codes=[429, 500, 502, 503, 504], 
    )

http_options = types.HttpOptions(
    retry_options=retry_options,
    )
    
aclient = genai.Client(
    vertexai=True, project=os.getenv("PROJECT_ID"),
     location="us-central1",
     http_options=http_options
).aio

video_bucket=os.getenv("VIDEO_BUCKET")

async def generate_and_upload_video(game_id: str, player_num: str, prompt: str, reference_images: Optional[Union[List[str], str]]):
    try:
        image_obj = None
        img_path = None
   
        if reference_images:
            if isinstance(reference_images, str):
                img_path = reference_images
            elif isinstance(reference_images, list) and len(reference_images) > 0:
                img_path = reference_images[0]
        
        if img_path:
            print(f"Processing reference image: {img_path}")
            # reference_images[0] is typically something like "/images/formula_e_race/fe_race_1.webp"
            clean_path = img_path
            if clean_path.startswith("/images/"):
                clean_path = clean_path[len("/images/"):]
            gs_uri = f"gs://ai-video-gen-challenge-ref-images/{clean_path}"
            
            ext = clean_path.split('.')[-1].lower()
            mime_type = "image/png"
            if ext in ['jpeg', 'jpg']:
                mime_type = "image/jpeg"
            elif ext == 'webp':
                mime_type = "image/webp"

            print(f"Mapped to GS URI: {gs_uri} with mime_type: {mime_type}")
            image_obj = types.Image(
                gcs_uri=gs_uri,
                mime_type=mime_type
            )

        config_args = {
            "number_of_videos": 1,
            "duration_seconds": 8,
            "generate_audio": True
        }
        
        if image_obj:
            # For veo-3.1-fast-generate-001, images are passed as reference_images in the config
            # reference_type is required, "asset" is used for subject consistency
            config_args["reference_images"] = [
                types.VideoGenerationReferenceImage(
                    image=image_obj,
                    reference_type="asset"
                )
            ]

        model_name = 'veo-3.1-fast-generate-001'
        print(f"Triggering Veo generation for {player_num} with model {model_name}. Image: {bool(image_obj)}")
        
        operation = await aclient.models.generate_videos(
            model=model_name,
            prompt=prompt,
            config=types.GenerateVideosConfig(**config_args)
        )

        while not operation.done:
            print(f"Waiting for video generation ({player_num})...")
            await asyncio.sleep(15)
            operation = await client.operations.get(operation.name)

        if operation.error:
            print(f"Operation error for {player_num}: {operation.error}")
            raise Exception(f"Video generation failed: {operation.error}")

        if operation.response:
            print(f"Generation complete for {player_num}. Uploading to GCS...")
            # Reverting back to original logic: upload video_bytes to GCS
            video_data = operation.result.generated_videos[0].video.video_bytes
            if video_data is None:
                raise Exception("Operation succeeded but video_bytes is None. Check if output_gcs_uri was inadvertently set or if the model changed behavior.")

            video_url = await asyncio.to_thread(gcs_utils.upload_video_to_gcs, video_data, content_type="video/mp4")
            await asyncio.sleep(5)

            filename = video_url.split('/')[-1]
            gs_uri_stored = f"gs://{video_bucket}/{filename}"

            game_ref = db.collection("game_rounds").document(game_id)
            update_data = {
                f"{player_num}Video": gs_uri_stored,
                f"{player_num}Prompt": prompt,
            }
            await asyncio.to_thread(game_ref.update, update_data)
            print(f"Successfully saved {player_num} video to Firestore.")

            return {
                "status": "success",
                "video_url" : video_url,
                "qr_code_base64": await asyncio.to_thread(gcs_utils.generate_qr_base64, video_url)
            }
        else:
            raise Exception("No video generated in the response")

    except Exception as e:
        import traceback
        print(f"Error in video generation for {player_num}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
