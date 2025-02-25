#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
import time
import traceback
from typing import List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from models.asr_model import SpeechModel
from utils.audio_processor import AudioProcessor
from utils.command_handler import CommandHandler

# Configure logging
log_level = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Print startup confirmation
print(f"Starting Speech Command Server with log level: {log_level}")
logger.info(f"Starting Speech Command Server with log level: {log_level}")

# Initialize FastAPI app
app = FastAPI(title="Speech Command Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize models and utilities
try:
    logger.info("Initializing speech model...")
    speech_model = SpeechModel()
    logger.info("Speech model initialized successfully")
    
    logger.info("Initializing audio processor...")
    audio_processor = AudioProcessor()
    logger.info("Audio processor initialized successfully")
    
    logger.info("Initializing command handler...")
    command_handler = CommandHandler()
    logger.info("Command handler initialized successfully")
except Exception as e:
    logger.error(f"Error initializing models: {e}")
    logger.error(traceback.format_exc())
    speech_model, audio_processor, command_handler = None, None, None

# Connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def get():
    """Serve the main HTML page"""
    logger.info("Serving index.html")
    try:
        with open(os.path.join("static", "index.html"), "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return HTMLResponse(content="Error loading index.html. Check server logs.", status_code=500)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "message": "Server is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time audio processing"""
    logger.info("WebSocket connection request received")
    
    # Check if models are initialized properly
    if speech_model is None or audio_processor is None or command_handler is None:
        logger.error("Critical components not initialized properly")
        return
    
    try:
        await manager.connect(websocket)
        
        # Last processed time to limit processing frequency
        last_processed_time = 0
        audio_process_count = 0
        
        logger.info("Starting WebSocket loop")
        
        while True:
            try:
                # Receive data without timeout
                data = await websocket.receive()
                
                # Process binary audio data
                if "bytes" in data:
                    audio_data = data["bytes"]
                    audio_process_count += 1
                    
                    # Log occasionally for debugging
                    if audio_process_count % 100 == 0:
                        logger.debug(f"Processed {audio_process_count} audio chunks")
                    
                    # Rate limiting
                    current_time = int(time.time() * 1000)
                    if current_time - last_processed_time < 50:
                        continue
                        
                    last_processed_time = current_time
                    
                    # Process audio
                    processed_audio = audio_processor.process_audio(audio_data)
                    
                    # Only process if we have enough audio data
                    if processed_audio is not None and len(processed_audio) > 1600:
                        # Get transcription
                        text = speech_model.transcribe(processed_audio)
                        
                        # Process transcription results
                        if text:
                            logger.info(f"Transcription: {text}")
                            
                            # Check for commands
                            command = command_handler.process_command(text)
                            
                            if command:
                                logger.info(f"Command detected: {command}")
                                await websocket.send_text(command)
                            else:
                                await websocket.send_text(text)
                
                # Handle disconnect message
                elif "type" in data and data["type"] == "websocket.disconnect":
                    logger.info("Received disconnect message from WebSocket")
                    break
                    
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected during receive")
                break
                
            except RuntimeError as e:
                if "disconnect message has been received" in str(e):
                    logger.info("WebSocket already disconnected")
                    break
                else:
                    logger.error(f"RuntimeError in websocket: {e}")
                    logger.error(traceback.format_exc())
                    
            except Exception as e:
                logger.error(f"Error processing data: {e}")
                logger.error(traceback.format_exc())
                # Don't break on error, try to continue
    
    except Exception as e:
        logger.error(f"Error in websocket connection: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Always clean up
        manager.disconnect(websocket)
        logger.info("WebSocket connection closed and cleaned up")


    """WebSocket endpoint for real-time audio processing"""
    logger.info("WebSocket connection request received")
    
    # Check if models are initialized properly
    if speech_model is None or audio_processor is None or command_handler is None:
        logger.error("Critical components not initialized properly")
        return
    
    try:
        await manager.connect(websocket)
        
        # Last processed time to limit processing frequency
        last_processed_time = 0
        audio_process_count = 0
        
        logger.info("Starting WebSocket loop")
        websocket_active = True
        
        while websocket_active:
            try:
                # Receive data with timeout
                data = await asyncio.wait_for(websocket.receive(), timeout=1.0)
                
                # Process binary audio data
                if "bytes" in data:
                    audio_data = data["bytes"]
                    audio_process_count += 1
                    
                    # Log occasionally for debugging
                    if audio_process_count % 100 == 0:
                        logger.debug(f"Processed {audio_process_count} audio chunks")
                    
                    # Rate limiting
                    current_time = int(time.time() * 1000)
                    if current_time - last_processed_time < 50:
                        continue
                        
                    last_processed_time = current_time
                    
                    # Process audio
                    processed_audio = audio_processor.process_audio(audio_data)
                    
                    # Only process if we have enough audio data
                    if processed_audio is not None and len(processed_audio) > 1600:
                        # Get transcription
                        text = speech_model.transcribe(processed_audio)
                        
                        # Process transcription results
                        if text:
                            logger.info(f"Transcription: {text}")
                            
                            # Check for commands
                            command = command_handler.process_command(text)
                            
                            if command:
                                logger.info(f"Command detected: {command}")
                                await websocket.send_text(command)
                            else:
                                await websocket.send_text(text)
                
                # Handle disconnect message
                elif "type" in data and data["type"] == "websocket.disconnect":
                    logger.info("Received disconnect message from WebSocket")
                    websocket_active = False
                    break
                    
            except asyncio.TimeoutError:
                # Check connection with ping
                try:
                    pong_waiter = await websocket.ping()
                    await asyncio.wait_for(pong_waiter, timeout=0.5)
                except Exception:
                    logger.info("WebSocket ping failed, connection seems broken")
                    websocket_active = False
                    break
                    
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected during receive")
                websocket_active = False
                break
                
            except RuntimeError as e:
                if "disconnect message has been received" in str(e):
                    logger.info("WebSocket already disconnected")
                    websocket_active = False
                    break
                else:
                    logger.error(f"RuntimeError in websocket: {e}")
                    
            except Exception as e:
                logger.error(f"Error processing data: {e}")
                logger.error(traceback.format_exc())
    
    except Exception as e:
        logger.error(f"Error in websocket connection: {e}")
    finally:
        manager.disconnect(websocket)
        logger.info("WebSocket connection closed and cleaned up")

if __name__ == "__main__":
    # Check for model
    model_path = "models/data/vosk-model-small-en-us-0.15"
    if not os.path.exists(model_path):
        logger.warning(f"Vosk model not found at {model_path}")
        logger.warning("Download from https://alphacephei.com/vosk/models")
        logger.warning("Install with these commands:")
        logger.warning("  mkdir -p models/data")
        logger.warning("  cd models/data")
        logger.warning("  wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        logger.warning("  unzip vosk-model-small-en-us-0.15.zip")
    
    # Start server
    try:
        log_level_uvicorn = log_level.lower()
        logger.info(f"Starting uvicorn with log_level={log_level_uvicorn}")
        uvicorn.run("app:app", host="0.0.0.0", port=8080, log_level=log_level_uvicorn)
    except Exception as e:
        logger.error(f"Error starting the server: {e}")
        print(f"Error starting the server: {e}")