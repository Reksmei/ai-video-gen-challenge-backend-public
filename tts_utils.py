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

import tts_lang_manager
from google.cloud import texttospeech
from google import genai
from google.genai import types
import os
import gcs_utils
import firebase_admin
from firebase_admin import firestore, credentials
from dotenv import load_dotenv
from firestore_utils import db

load_dotenv()

# Set environmental variables and create tts client
client = texttospeech.TextToSpeechClient()


def synthesize_welcome_message(game_id:str, lang: str):
    """ Generates welcome message before game starts and saves it to an MP3 file.
    """
    doc_ref = db.collection("game_rounds").document(game_id)
    doc = doc_ref.get().to_dict()

    try: 
        player1 = doc.get("player1", "")
        player2 = doc.get("player2", "")
        player3 = doc.get("player3")
        raw_video_theme = doc.get("videoTheme")
    except Exception:
        print("No Player 3 in this game round")
        player1 = doc.get("player1", "")
        player2 = doc.get("player2", "")      
        player3 = None
        raw_video_theme = doc.get("videoTheme")
    
    prompt = "Read aloud with a charismatic tone"
    video_theme= raw_video_theme.replace("_", " ")

    if lang == "English" and player3 != None:
        language_code="en-us"
        text = tts_lang_manager.english_welcome_text2.format(player1=player1, player2=player2, player3=player3, video_theme=video_theme)
    
    elif lang == "English" and player3 == None:
        language_code="en-us"
        text = tts_lang_manager.english_welcome_text1.format(player1=player1, player2=player2, video_theme=video_theme)
    
    elif lang == "German" and player3 != None:
        language_code="de-DE"
        text = tts_lang_manager.german_welcome_text2.format(player1=player1, player2=player2, player3=player3, video_theme=video_theme)

    elif lang == "German" and player3 == None:
        language_code="de-DE"
        text = tts_lang_manager.german_welcome_text1.format(player1=player1, player2=player2, video_theme=video_theme)

    elif lang == "Polish" and player3 != None:
        language_code="pl-PL"
        text = tts_lang_manager.polish_welcome_text2.format(player1=player1, player2=player2, player3=player3, video_theme=video_theme)
    
    elif lang == "Polish" and player3 == None:
        language_code="pl-PL"
        text = tts_lang_manager.polish_welcome_text1.format(player1=player1, player2=player2, video_theme=video_theme)
        
    elif lang == "Spanish" and player3 != None:
        language_code = "es-ES"
        text = tts_lang_manager.spanish_welcome_text2.format(player1=player1, player2=player2, player3=player3, video_theme=video_theme)

    elif lang == "Spanish" and player3 == None:
        language_code = "es-ES"
        text = tts_lang_manager.spanish_welcome_text1.format(player1=player1, player2=player2, video_theme=video_theme)

    elif lang == "Arabic" and player3 != None:
        language_code =	"ar-EG"
        text = tts_lang_manager.arabic_welcome_2.format(player1=player1, player2=player2, player3=player3, video_theme=video_theme)

    elif lang == "Arabic" and player3 == None:
        language_code =	"ar-EG"
        text = tts_lang_manager.arabic_welcome_1.format(player1=player1, player2=player2, video_theme=video_theme)

    synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name="Alnilam",  
        model_name="gemini-3.1-flash-tts-preview"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    import base64
    audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
    audio_data_uri = f"data:audio/mpeg;base64,{audio_base64}"
    
    doc_ref.update({"welcome_text": text})
    return audio_data_uri


def synthesize_post_video_gen_audio(game_id:str, lang: str):
    doc_ref = db.collection("game_rounds").document(game_id)
    doc = doc_ref.get().to_dict()

    raw_video_theme = doc.get("videoTheme", doc.get("videoTheme", "video"))
    
    # Format video theme properly for spoken text if necessary
    video_theme = raw_video_theme.replace("_", " ")

    prompt = "Read aloud in with a charismatic tone"
    
    if lang == "English":
        language_code="en-us"
        text = tts_lang_manager.english_post_video_text.format(video_theme=video_theme)
    
    elif lang == "German":
        language_code="de-DE"
        text = tts_lang_manager.german_post_video_text.format(video_theme=video_theme)

    elif lang == "Polish":
        language_code="pl-PL"
        text = tts_lang_manager.polish_post_video_text.format(video_theme=video_theme)
    
    elif lang == "Spanish":
        language_code = "es-ES"
        text = tts_lang_manager.spanish_post_video_text.format(video_theme=video_theme)

    elif lang == "Arabic":
        language_code =	"ar-EG"
        text = tts_lang_manager.arabic_post_video_text.format(video_theme=video_theme)

    synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name="Alnilam",  
        model_name="gemini-2.5-flash-tts"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    import base64
    audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
    audio_data_uri = f"data:audio/mpeg;base64,{audio_base64}"

    doc_ref.update({"post_video_text": text})
    return audio_data_uri, text

def video_show_audio(game_id: str, lang: str):
    prompt = "Read aloud in with a charismatic tone"
    
    doc_ref = db.collection("game_rounds").document(game_id)
    doc = doc_ref.get().to_dict()

    try: 
        player1 = doc.get("player1", "")
        player2 = doc.get("player2", "")
        player3 = doc.get("player3")
    except Exception:
        print("No Player 3 in this game round")
        player1 = doc.get("player1", "")
        player2 = doc.get("player2", "")      
        player3 = None
    
    prompt = "Read aloud with a charismatic tone"

    if lang == "English" and player3 != None:
        language_code="en-us"
        text = tts_lang_manager.english_video_show_text2.format(player1=player1, player2=player2, player3=player3)
    
    elif lang == "English" and player3 == None:
        language_code="en-us"
        text = tts_lang_manager.english_video_show_text1.format(player1=player1, player2=player2)
    
    elif lang == "German" and player3 != None:
        language_code="de-DE"
        text = tts_lang_manager.german_video_show_text2.format(player1=player1, player2=player2, player3=player3)

    elif lang == "German" and player3 == None:
        language_code="de-DE"
        text = tts_lang_manager.german_video_show_text1.format(player1=player1, player2=player2)

    elif lang == "Polish" and player3 != None:
        language_code="pl-PL"
        text = tts_lang_manager.polish_video_show_text2.format(player1=player1, player2=player2, player3=player3)
    
    elif lang == "Polish" and player3 == None:
        language_code="pl-PL"
        text = tts_lang_manager.polish_video_show_text1.format(player1=player1, player2=player2)
        
    elif lang == "Spanish" and player3 != None:
        language_code = "es-ES"
        text = tts_lang_manager.spanish_video_show_text2.format(player1=player1, player2=player2, player3=player3)

    elif lang == "Spanish" and player3 == None:
        language_code = "es-ES"
        text = tts_lang_manager.spanish_video_show_text1.format(player1=player1, player2=player2)

    elif lang == "Arabic" and player3 != None:
        language_code =	"ar-EG"
        text = tts_lang_manager.arabic_video_show_text2.format(player1=player1, player2=player2, player3=player3)

    elif lang == "Arabic" and player3 == None:
        language_code =	"ar-EG"
        text = tts_lang_manager.arabic_video_show_text1.format(player1=player1, player2=player2)

    synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name="Alnilam",  
        model_name="gemini-2.5-flash-tts"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
     # Upload audio to GCS
    try: 
       url = gcs_utils.upload_audio_to_gcs(response.audio_content)
       print("Audio uploaded successfully")
       return url, text
    
    except Exception as e:
        print(f"Upload to GCS failed for audio: {e}")
        return None

def synthesize_prompt_lecture_audio(gemini_lecture: str, lang: str):
    prompt = "Read aloud with a charismatic tone"

    if lang == "English":
        language_code="en-us"
    
    elif lang == "German":
        language_code="de-DE"

    elif lang == "Polish":
        language_code="pl-PL"
    
    elif lang == "Spanish":
        language_code = "es-ES"

    elif lang == "Arabic":
        language_code =	"ar-EG"

    synthesis_input = texttospeech.SynthesisInput(text=gemini_lecture, prompt=prompt)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name="Alnilam",
        model_name="gemini-2.5-flash-tts"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Upload audio to GCS
    try:
       url = gcs_utils.upload_audio_to_gcs(response.audio_content)
       print("Audio uploaded successfully")
       return url, gemini_lecture    
    except Exception as e:
        print(f"Upload to GCS failed for audio: {e}")
        return None
    

def synthesize_judging_audio(judging_output: str, lang: str):
    prompt = "Read aloud with a charismatic tone"
    text = judging_output # Note that the judging output will already be in the target language

    # Only need set the language code to make sure the voice/accent is appropriate for the language the judging out is in
    if lang == "English":
        language_code="en-us"
    
    elif lang == "German":
        language_code="de-DE"

    elif lang == "Polish":
        language_code="pl-PL"
    
    elif lang == "Spanish":
        language_code = "es-ES"

    elif lang == "Arabic":
        language_code =	"ar-EG"

    synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name="Alnilam",  
        model_name="gemini-2.5-flash-tts"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Upload audio to GCS
    try: 
       url = gcs_utils.upload_audio_to_gcs(response.audio_content)
       print("Audio uploaded successfully")
       return url, text
    
    except Exception as e:
        print(f"Upload to GCS failed for audio: {e}")
        return None

