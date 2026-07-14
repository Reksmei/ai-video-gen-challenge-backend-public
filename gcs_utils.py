# Copyright 2026 Reksmei Arkadiusz-Davidavic

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://apache.org

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import uuid
import qrcode
import base64
import io
from google.cloud import storage
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Initialize Storage Client
video_bucket_name = os.getenv("VIDEO_BUCKET")
audio_bucket_name = os.getenv("AUDIO_BUCKET")
storage_client = storage.Client(project=os.getenv("PROJECT_ID"))

video_bucket = storage_client.bucket(video_bucket_name)
audio_bucket = storage_client.bucket(audio_bucket_name)
image_bucket = storage_client.bucket(image_bucket_name)

def upload_video_to_gcs(video_data: bytes, content_type: str = "video/mp4") -> str:
    '''
    Uploads generated videos to Cloud Storage with unique name and returns public URL
    '''
    filename = f"video-{uuid.uuid4()}.mp4"
    blob = video_bucket.blob(filename)
    blob.upload_from_string(video_data, content_type=content_type)
    return f"https://storage.googleapis.com/{video_bucket_name}/{filename}"

def upload_audio_to_gcs(audio_data: bytes, content_type: str = "audio/mp3") -> str:
    '''
    Uploads generated TTS audio to GCS
    '''
    filename = f"audio-{uuid.uuid4()}.mp3"
    blob = audio_bucket.blob(filename)
    blob.upload_from_string(audio_data, content_type=content_type)
    return f"https://storage.googleapis.com/{audio_bucket_name}/{filename}"

def upload_image_to_gcs(image_data: bytes, content_type: str="image/png"):
    '''
    Uploads custom reference images to GCS
    '''
    filename = f"image-{uuid.uuid4()}.png"
    blob = image_bucket.blob(filename)
    blob.upload_from_string(image_data, content_type=content_type)
    return f"https://storage.googleapis.com/{image_bucket_name}/{filename}"


def generate_qr_base64(url: str) -> str:
    '''
    Generates a QR code for a URL and returns it as a base64 string.
    '''

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )  

    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode('utf-8')
