import sys
import os
import json
import time
import queue
import signal
import sounddevice as sd
import numpy as np
from vosk import Model, KaldiRecognizer

# Parameters
SAMPLE_RATE = 16000
BUFFER_SIZE = 1600
COMMANDS = {"play": "▶️", "pause": "⏸️"}

# ASCII color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def generate_beep(frequency=440, duration=0.2, volume=0.5):
    """Generate a simple beep sound"""
    t = np.linspace(0, duration, int(duration * SAMPLE_RATE), False)
    # Generate sine wave
    note = np.sin(frequency * t * 2 * np.pi)
    envelope = np.ones_like(note)
    if len(envelope) > 100:
        envelope[:100] = np.linspace(0, 1, 100)
        envelope[-100:] = np.linspace(1, 0, 100)
    note = note * envelope
    # Normalize and scale by volume
    audio = note * volume / np.max(np.abs(note))
    # Convert to 16-bit PCM
    audio = (audio * 32767).astype(np.int16)
    return audio

def play_beep(frequency=440, duration=0.2, volume=0.5):
    """Play a beep sound"""
    try:
        # Generate beep
        beep_data = generate_beep(frequency, duration, volume)
        # Play the beep
        sd.play(beep_data, SAMPLE_RATE)
        sd.wait()
    except Exception as e:
        print(f"Error playing beep: {e}")

def clear_line():
    """Clear the current line in the terminal"""
    sys.stdout.write("\033[K")
    sys.stdout.flush()

def print_status(text, color=RESET, end='\n'):
    """Print status with color"""
    clear_line()
    sys.stdout.write(f"{color}{text}{RESET}{end}")
    sys.stdout.flush()

def main():
    def signal_handler(sig, frame):
        print_status("\nStopping speech command detection...", RED)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Check if model path is provided
    model_path = "models/data/vosk-model-small-en-us-0.15"
    if not os.path.exists(model_path):
        print_status(f"Model not found at {model_path}", RED)
        print_status("Please download the model from https://alphacephei.com/vosk/models", YELLOW)
        return

    # Initialize Vosk
    print_status(f"Loading Vosk model from {model_path}...", BLUE)
    model = Model(model_path)
    recognizer = KaldiRecognizer(model, SAMPLE_RATE)
    recognizer.SetWords(True)
    recognizer.SetPartialWords(True)
    
    # For command cooldown
    last_command = None
    last_command_time = 0
    command_cooldown = 1.0  # seconds
    
    # Setup audio input
    q = queue.Queue()
    
    def audio_callback(indata, frames, time, status):
        """Callback for audio input"""
        if status:
            print_status(f"Audio input error: {status}", RED)
        q.put(bytes(indata))
    
    # Start audio stream
    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BUFFER_SIZE,
            dtype='int16',
            channels=1,
            callback=audio_callback
        ):
            print_status(f"{BOLD}Speech Command Detector{RESET}", GREEN)
            print_status(f"Listening for commands: {', '.join([f'{GREEN}{cmd}{RESET}' for cmd in COMMANDS])}")
            print_status(f"Press {BOLD}Ctrl+C{RESET} to exit")
            print_status("-" * 50)
            
            while True:
                # Get audio data from queue
                data = q.get()
                
                # Process with recognizer
                if recognizer.AcceptWaveform(data):
                    # Get full result
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").strip().lower()
                    
                    if text:
                        print_status(f"[FULL] {text}")
                        
                        # Check for commands
                        detected_command = None
                        for command in COMMANDS:
                            if command in text.split() or text == command:
                                detected_command = command
                                break
                        
                        # Apply cooldown and trigger if command detected
                        if detected_command:
                            current_time = time.time()
                            if detected_command != last_command or current_time - last_command_time > command_cooldown:
                                # Update command state
                                last_command = detected_command
                                last_command_time = current_time
                                
                                # Visual feedback
                                emoji = COMMANDS[detected_command]
                                print_status(f"{BOLD}{YELLOW}Command detected: {detected_command} {emoji}{RESET}", YELLOW)
                                
                                # Audio feedback (different tones for play/pause)
                                if detected_command == "play":
                                    play_beep(660, 0.1)  # Higher tone for play
                                else:
                                    play_beep(440, 0.1)  # Lower tone for pause
                else:
                    # Get partial result
                    result = json.loads(recognizer.PartialResult())
                    partial = result.get("partial", "").strip().lower()
                    
                    if partial:
                        # Check for exact command matches in partial
                        exact_match = False
                        for command in COMMANDS:
                            if partial == command:
                                print_status(f"[PARTIAL EXACT] {partial}", BLUE, end='\r')
                                exact_match = True
                                break
                                
                        if not exact_match:
                            print_status(f"[PARTIAL] {partial}", end='\r')
    
    except Exception as e:
        print_status(f"Error: {e}", RED)

if __name__ == "__main__":
    main()