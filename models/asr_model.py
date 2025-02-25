import os
import logging
import numpy as np
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class SpeechModel:
    """
    A speech recognition model using Vosk for real-time transcription
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the speech model
        
        Args:
            model_path: Path to the pre-trained model. If None, will download a small model.
        """
        self.sample_rate = 16000  # 16kHz is standard for speech
        
        # Keywords we're particularly interested in
        self.keywords = ["play", "pause"]
        
        try:
            # Import vosk
            from vosk import Model, KaldiRecognizer
            
            # Use default model path if not provided
            if model_path is None:
                # Create models directory if it doesn't exist
                models_dir = Path('./models/data')
                models_dir.mkdir(parents=True, exist_ok=True)
                
                model_path = models_dir / "vosk-model-small-en-us-0.15"
                
                # Check if model exists, if not guide user to download
                if not model_path.exists():
                    logger.info(f"Vosk model not found at {model_path}")
                    logger.info("Please download the model from https://alphacephei.com/vosk/models")
                    logger.info("and extract it to the models/data directory")
                    logger.info("For this example, we recommend the small English model (vosk-model-small-en-us-0.15)")
                    
                    # Create dummy model for demonstration
                    self.vosk_model = None
                    self.recognizer = None
                    self.is_dummy = True
                    logger.warning("Using dummy model for demonstration")
                    return
            
            # Load the model
            logger.info(f"Loading Vosk model from {model_path}")
            self.vosk_model = Model(str(model_path))
            
            # Create recognizer
            self.recognizer = KaldiRecognizer(self.vosk_model, self.sample_rate)
            
            # Set up partial results for faster responses
            self.recognizer.SetPartialWords(True)
            self.recognizer.SetWords(True)
            
            logger.info("Vosk model loaded successfully")
            self.is_dummy = False
            
        except Exception as e:
            logger.error(f"Error loading Vosk model: {e}")
            logger.warning("Using dummy model for demonstration")
            self.vosk_model = None
            self.recognizer = None
            self.is_dummy = True
    
    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio data to text
        
        Args:
            audio_data: Audio data as numpy array with shape (n,) and sample rate 16kHz
            
        Returns:
            Transcribed text
        """
        if audio_data is None or len(audio_data) < 1600:  # At least 0.1 seconds of audio
            return ""
            
        try:
            # If we're using a dummy model, return a simple result
            if self.is_dummy:
                return self._dummy_transcribe(audio_data)
            
            # Convert to int16 PCM as expected by Vosk
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Send data to recognizer
            recognizer_delay = 0.01  # 10ms delay to avoid overloading
            if self.recognizer.AcceptWaveform(audio_data.tobytes()):
                # Get full result
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "").lower().strip()
                if text:
                    print(f"[VOSK FULL] {text}")  # Print to terminal for debugging
                    
                    # Directly check for keywords
                    for keyword in self.keywords:
                        if keyword in text.split() or text == keyword:
                            print(f"[KEYWORD DETECTED] {keyword}")
                            return keyword
            else:
                # Get partial result for real-time feedback
                result = json.loads(self.recognizer.PartialResult())
                text = result.get("partial", "").lower().strip()
                if text:  # Only print if there's actual content
                    print(f"[VOSK PARTIAL] {text}")  # Print to terminal for debugging
                    
                    # Check for clear keyword matches even in partial results
                    for keyword in self.keywords:
                        if text == keyword or f" {keyword} " in f" {text} ":
                            print(f"[KEYWORD DETECTED IN PARTIAL] {keyword}")
                            return keyword
            
            # Return the text even if empty for real-time feedback
            return text
            
        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            return ""
            
    def _dummy_transcribe(self, audio_data: np.ndarray) -> str:
        """Simulate transcription with random outputs focused on our keywords"""
        import random
        
        # Randomly return keywords sometimes for demo purposes
        r = random.random()
        if r < 0.05:
            return "play"
        elif r < 0.1:
            return "pause"
        else:
            return ""