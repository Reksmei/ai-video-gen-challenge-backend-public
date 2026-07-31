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

from google import genai
from google.genai import types
import tts_utils
import time
from fastapi import HTTPException
import os
from firestore_utils import db, player_score
from dotenv import load_dotenv

load_dotenv()

# Create client for Gen AI SDK
client = genai.Client(enterprise=True, project=os.getenv("PROJECT_ID"), location="global")

# Create tool mapping
tools_map = {
    "player_score": player_score
}

# Generates an optional reference image to accompany text prompt for video generation
def generate_ref_image(game_id: str, player_id: str, custom_prompt: str = None):
    '''
    Generates custom reference image to use to generate a video using Nano Banana 2 Lite
    '''

    doc_ref = db.collection("game_rounds").document(game_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Game round not found")
    
    game_data = doc.to_dict()
    video_theme = game_data.get("videoTheme", "modern scene")
    
    if custom_prompt and custom_prompt.strip():
        prompt_text = custom_prompt.strip()
    else:
        player_prompt = game_data.get(f"{player_id}Prompt", "")
        prompt_text = player_prompt

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt_text,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio="4:3"
            )
        )
    )

    generated_bytes = None
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                generated_bytes = part.inline_data.data if hasattr(part.inline_data, 'data') else part.inline_data
    
    if not generated_bytes:
        raise HTTPException(status_code=500, detail="Failed to generate image bytes from model response")

    image_url = upload_image_to_gcs(generated_bytes, content_type="image/png")
    key = f"{player_id}_image"
    doc_ref.set(
        {key: image_url},
        merge=True
    )

    return {
        "status": "success",
        "image_url": image_url
    }

# Function to request prompt analysis from Gemini
def judge_prompt(game_id: str, player3: bool):
    doc_ref = db.collection("game_rounds").document(game_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Game round not found")
    
    game_data = doc.to_dict()
    video_theme = game_data.get('videoTheme')  
    lang = game_data.get('language', 'English')
    eventId = game_data.get('eventId', 'default_event')

    players_info = f"Player 1 was {game_data.get('player1')}, Player 2 was {game_data.get('player2')}."
    if game_data.get('player3'):
        players_info += f" Player 3 was {game_data.get('player3')}."

    prompt_judge_prompt = f'''
     We have just held a video generation challenge round where participants had 30 seconds to prompt Veo 3.1 Fast to generate
    an 8 second {video_theme}. 
    
    We don't have the videos yet, but you will be providing some constructive feedback on each's player's prompt whilst we wait
    for the videos to be generated, and you will be judging them in a couple of minutes. 
    {players_info}
    
    In {lang}, create a little but not too much suspense following the end of the game round and then analyze each of the prompts, 
    providing a sentence with feedback on each prompt. 
    Use double line breaks between each player's feedback and the introduction for readability.
    '''

    parts = []
    for i in range(1, 4):
        player_name = game_data.get(f'player{i}')
        prompt_text = game_data.get(f"player{i}Prompt")
        
        if player_name and prompt_text:
            parts.append(types.Part(text=f"Prompt from {player_name}: {prompt_text}"))
            
    if not parts:
        raise HTTPException(status_code=400, detail="No prompts found to judge.")
        
    parts.append(types.Part(text=prompt_judge_prompt))

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            temperature=1.2,
            system_instruction='''You are a world class cinematic director and AI video generator 
            with experience directing short films, and generating short clips using AI video generation models 
            such as Veo and Kling. You are analyzing competition entries for an AI video generation competition,
            and you have a playful yet charismatic tone. 
            Use the player names provided, do not refer to the players as Player1, Player2 or Player3.
            Do not use asterisks (**) and do not use stage directions or gestures in your output
            ''')
    )

    prompt_judgment_text = response.text
    prompt_judging_audio, _ = tts_utils.synthesize_judging_audio(response.text, lang)

    doc_ref.update({
        "prompt_analysis": prompt_judgment_text,
        "prompt_judging_audio": prompt_judging_audio
    })

    return {
        'prompt_judgment_text': prompt_judgment_text,
        'prompt_judging_audio': prompt_judging_audio
    }

# Generate dynamic short lecture on how to prompt for video generation
def gemini_prompt_lecture(game_id: str, lang:str):
    doc_ref = db.collection("game_rounds").document(game_id)

    prompt = f'''
    You have just reviewed some prompts and now you need to identify the key components of what makes a good prompt for video generation and provide
    a friendly lecture in {lang}, no more than 20 seconds long on how to prompt for video generation. 
    Start with a natural transition such as "Now, I'd like quickly discuss what is the key to prompting for Video Generation" or the equivalent in {lang},
    and deliver a some quick yet important insights on the nuances behind prompt engineering for generating high quality videos.
    Don't refer to the fact that you have just reviewed the prompts and do not guess the prompts were. Please leave 2 lines between each sentence.

    Once you're done, mention that you'll analyze their (your) videos shortly and then you'll crown a winner! 
    '''
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=[prompt],
        config = types.GenerateContentConfig(
            system_instruction='''
            You are a world class cinematic director and AI video generator 
            with experience directing short films, and generating short clips using AI video generation models 
            such as Veo and Kling. You will have been analyzing competition entries for an AI video generation competition,
            and you have a playful yet charismatic tone. 
            Do not use asterisks (**) and do not use stage directions or gestures in your output.
            
            ''',
            temperature = 1,
        )
    )
    prompt_lecture_text = response.text
    prompt_lecture_audio, _ = tts_utils.synthesize_prompt_lecture_audio(gemini_lecture=prompt_lecture_text, lang=lang)

    doc_ref.update({
        "prompt_lecture_text": prompt_lecture_text,
        "prompt_lecture_audio": prompt_lecture_audio
    })

    return {
        "prompt_lecture_text": prompt_lecture_text,
        "prompt_lecture_audio": prompt_lecture_audio
    }

# Function to request video judgment from Gemini
def judge_videos(game_id: str, player3: bool):
    doc_ref = db.collection("game_rounds").document(game_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Game round not found")
        
    game_data = doc.to_dict()
    video_theme = game_data.get('videoTheme')
    lang = game_data.get('language', 'English')
    eventId = game_data.get('eventId', 'default_event')
    prompt_analysis = game_data.get('prompt_analysis', 'No previous prompt analysis available.')

    players_info = f"Player 1 was {game_data.get('player1')}, Player 2 was {game_data.get('player2')}."
    if game_data.get('player3'):
        players_info += f" Player 3 was {game_data.get('player3')}."

    # PROMPT 1: Only qualitative analysis and announcing the winner (NO NUMBERS)
    video_judge_prompt = f'''
    We have just held a video generation challenge round where participants had 30 seconds to prompt Veo 3.1 Fast to generate
    an 8 second {video_theme}. You previously had analyzed their prompts, the output of which was: {prompt_analysis} and now you have been provided the videos too. 
    {players_info}
    
    In {lang}, create some suspense and then analyze each of the videos, 
    providing a sentence highlighting the key features from each video. 
    
    Evaluate which participant's video is the best based on Consistency, Fluidity, Detail and adherence to the theme.
    
    Announce the winner with "and the winner is" or the equivalent in {lang}!
    You should provide 2-3 sentences detailing why the winner's video was the best and how the other participants could improve their videos.
    
    CRITICAL: Keep this purely cinematic and conversational. DO NOT mention any numerical scores out of 100 in your response.
    Use double line breaks between the video analysis and the winner announcement.
    '''

    parts =[]
    for i in range(1, 4):
        player_name = game_data.get(f'player{i}')
        video_uri = game_data.get(f"player{i}Video")
        prompt_text = game_data.get(f"player{i}Prompt")
        
        if video_uri and player_name:
            parts.append(types.Part.from_text(text=f"Video from {player_name} (Prompt: {prompt_text}):"))
            parts.append(types.Part.from_uri(file_uri=video_uri, mime_type="video/mp4"))
            
    if not parts:
        raise HTTPException(status_code=400, detail="No videos found to judge.")
        
    parts.append(types.Part.from_text(text=video_judge_prompt))

    # Define the tool configuration
    player_score_tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="player_score",
                description="Update a player's score in the leaderboard.",
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "eventId": types.Schema(type="STRING"),
                        "player_name": types.Schema(type="STRING"),
                        "total_score": types.Schema(type="INTEGER"),
                        "consistency_score": types.Schema(type="INTEGER"),
                        "fluidity_score": types.Schema(type="INTEGER"),
                        "detail_score": types.Schema(type="INTEGER"),
                    },
                    required=["eventId", "player_name", "total_score", "consistency_score", "fluidity_score", "detail_score"]
                )
            )
        ]
    )

    # 1. Initialize the Chat Session
    chat = client.chats.create(
        model="gemini-3.6-flash",
        config=types.GenerateContentConfig(
            temperature=0.7,
            system_instruction='''You are a world class cinematic director and AI video generator 
            with experience directing short films, and generating short clips using AI video generation models 
            such as Veo, Sora and Kling. You are analyzing competition entries for an AI video generation competition,
            and you have a playful yet charismatic tone. 
            Use the player names provided, do not refer to the players as Player1, Player2 or Player3.
            Do not use asterisks (**) and do not use stage directions or gestures in your output
            '''
        )
    )

    # TURN 1: Send the videos and get the textual judgement
    response_1 = chat.send_message(parts)
    
    # Extract text from Turn 1
    final_judgment_text = response_1.text.strip() if response_1.text else ""
    if not final_judgment_text:
        final_judgment_text = "It seems there was an issue generating the final judgement. Here are your videos!"

    # Create TTS audio
    final_judging_audio, _ = tts_utils.synthesize_judging_audio(final_judgment_text, lang)
    
    # Update the database immediately so the frontend can start playing the audio
    # while Gemini quietly assigns scores in Turn 2!
    doc_ref.update({
        "final_judgement": final_judgment_text,
        "judging_audio": final_judging_audio,
        "game_status": "finished"
    })
    
    # TURN 2: Calculate scores based on Turn 1 and call the tool
    tool_config = types.GenerateContentConfig(
        tools=[player_score_tool],
        temperature=0.0, # Make it strictly analytical
    )
    
    tool_prompt = f'''
    Based on the analysis you just gave and the winner you just announced, it is now time to assign numerical scores.
    
    For EACH player, calculate a score out of 100 for:
    1. Consistency
    2. Fluidity
    3. Detail
    Then calculate their overall total_score. Make sure the winner you just announced gets the highest total_score.
    
    Call the `player_score` tool for EVERY player to save their scores to the leaderboard using the eventId: {eventId}. 
    Do not output any normal text, just execute the tools.
    '''
    
    response_2 = chat.send_message(tool_prompt, config=tool_config)

    # Execute tool calls from Turn 2
    if response_2.function_calls:
        for function_call in response_2.function_calls:
            fn_name = function_call.name
            fn_args = function_call.args
            if fn_name in tools_map:
                try:
                    tools_map[fn_name](**fn_args)
                except Exception as e:
                    print(f"Error calling tool {fn_name}: {e}")

    return {
        "judgement": final_judgment_text,
        "judging_audio": final_judging_audio
    }
