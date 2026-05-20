# AI Video Gen Challenge🎬
![Homepage](https://storage.googleapis.com/ai-pg-demo-media/ai-video-gen-challenge-homepage.png)

## Overview

The AI Video Gen Challenge is an interactive, real-time web application that allows users to compete in AI-powered short film making competitions. Hosted live, the application allows a Game Host to set a creative theme and spin up a lobby. Players join via their mobile devices, craft a creative prompt, and submit it before a 30-second countdown ends. 

Once time is up, the application seamlessly coordinates multiple AI models to generate the videos, synthesize audio commentary, analyze the user's prompting skills, and finally, judge the resulting videos to crown a winner. 

## How It Works: The Tech Stack

The entire experience is orchestrated using a modern, scalable stack deeply integrated with Google Cloud and Agent Platform:

- **Veo 3.1 Fast on Agent Platform**: The core video generation engine. It provides the perfect balance of high-end cinematic quality and quicker generation speeds necessary for a live, interactive game.
- **Gemini 3.1 Flash Lite and Gemini 3.5 Flash on Agent Platform**: Powers the "AI Judge." It utilizes advanced multimodal reasoning to analyze the players' text prompts and visually review the multiple generated short videos in seconds to determine the winner.
- **Gemini 2.5 TTS on Agent Platform**: Provides the charismatic voice of the AI host/judge, dynamically generating realistic, synthesized speech for the welcome message, prompt analysis, and final judgment.
- **Cloud Run**: A serverless, scalable containerized FastAPI backend that securely manages the heavy API calls to Agent Platform and orchestrates the game logic.
- **Firebase & Firestore**: The real-time database backbone. It instantly synchronizes the game state (countdown timers, video URLs, generated text, and status flags) across the Host Panel, the Main Show Screen, and all the individual Player mobile screens.
- **Next.js (React)**: The responsive, interactive frontend handling the cinematic UI, synchronized teleprompter text, and real-time audio playback.

## Project structure

- **main.py**: Entry point to the FastAPI application, that calls the imported functions from the other modules for text, audio and video generation, as well as updating the database and storage buckets
- **gemini_utils.py**: Manages the logic behind the authentication and API calls to Gemini for prompt and video judging, and contains the prompts and system instructions for the text generation
- **veo_utils.py**: Manages the logic behind the authentication and API calls to Veo for video generation.
- **tts_utils.py**: Manages the logic behind the authentication and API calls to Gemini TTS for audio generation and contains output style instructions for TTS.
- **tts_lang_manager.py**: Contains different deterministic messages in different languages for each stage of the competition (such as the Welcome) which are imported by tts_utils.py and tweaked with string formatting for player names and video theme chosen.
- **firestore_utils.py**: Manages all logic regarding creating game rounds, updating game rounds and player details with text outputs from Gemini, and Cloud Storage file paths to generated audio and video and managing game state.
- **gcs_utils.py**: Manages the logic for uploading video and audio to Cloud Storage.

## Enterprise Use Cases 

While this application is a gamified experience, the underlying capabilities—automating video generation, analyzing multimodal inputs, and orchestrating complex generative workflows—are highly relevant to enterprise use cases:

### 1. Mass-Scale Creative Generation
Companies can use **Veo** and **Gemini** to automate the creation of thousands of hyper-personalized video advertisements, product catalog videos, or localized email marketing assets. By replacing manual video editing with programmatic generation, brands can scale production across global markets while maintaining brand compliance.

### 2. Automated Content Analysis & Localization
Organizations can leverage **Gemini's multimodal capabilities** to process long-form video, automate multilingual subtitle generation, and analyze unstructured social media data or community sentiment. This dramatically reduces the time required to extract actionable insights from video and audio.

### 3. Campaign & Creative Workflows
Agencies can use conversational AI as a "creative accelerator" to brainstorm concepts, draft marketing copy, and generate in-game assets or storyboards directly from design documents. The integration of **TTS (Text-to-Speech)** allows for rapid audio-to-video animation and immersive, interactive avatars.

### 4. "Synthetic Persona" Testing & Suitability
Marketing teams can use LLMs to simulate user profiles and test campaign assets before they go live. Additionally, AI can analyze video and audio to ensure brand safety, verifying that ad placements are situated next to suitable content.

## How to Test Locally

To run the backend locally, you will need two terminal windows—one for the FastAPI backend and one for the Next.js frontend.

### Prerequisites
- Python 3.9+
- Node.js 18+
- Google Cloud Project with Agent Platform enabled
- Firebase Project configured
- A `.env` file in the Backend and a `.env.local` file in the Frontend with your GCP/Firebase credentials.

### Clone and Setup
1. Open your terminal and change the directory to when you want to clone the repo, then clone this repo
   ```bash
   gh repo clone https://github.com/Reksmei/ai-video-gen-challenge-backend-public
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   cd 
   pip install -r requirements.txt
   ```
4. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload
   ```
   *The backend will run on `http://localhost:8000`*
