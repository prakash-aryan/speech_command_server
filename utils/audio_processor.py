import io
import logging
import time
import numpy as np
import wave
from typing import Optional

logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Process audio data for speech recognition
    """
    
    def __init__(self):
        """Initialize the audio processor"""
        self.sample_rate = 16000  # 16kHz for speech recognition
        self.frame_duration_ms = 30  # 30ms frames
        
        # Buffer for collecting audio
        self.audio_buffer = bytearray()
        self.buffer_limit = self.sample_rate * 2  # 2 seconds limit
        
        # For diagnostics
        self.total_audio_processed = 0
        self.last_diagnostic_time = 0
        
    def process_audio(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """
        Process incoming audio data
        
        Args:
            audio_bytes: Raw audio bytes
            
        Returns:
            Processed audio as numpy array or None if no valid audio
        """
        try:
            # Check if we have valid data
            if not audio_bytes or len(audio_bytes) < 32:
                return None
            
            # For safety, work with a copy of the data
            try:
                # Try to convert bytes to numpy array (16-bit signed integer)
                # Make sure we have an even number of bytes for 16-bit samples
                bytes_len = len(audio_bytes)
                if bytes_len % 2 != 0:
                    # Trim to even length
                    audio_bytes = audio_bytes[:bytes_len - (bytes_len % 2)]
                
                # First try to interpret as raw PCM
                try:
                    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                    
                    # Check if the audio data makes sense as PCM
                    # If mean value is extreme or values out of bounds, it might not be PCM
                    mean_abs = np.mean(np.abs(audio_array))
                    if mean_abs > 30000 or mean_abs < 10:
                        # Try alternative format (WebM/Opus)
                        logger.warning(f"Audio data doesn't look like valid PCM: mean={mean_abs}")
                        return None
                except Exception as e:
                    logger.error(f"Error interpreting as PCM: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error converting audio bytes to array: {e}")
                return None
                
            # Check if we actually got data
            if len(audio_array) == 0:
                return None
                
            # Log stats for debugging
            current_time = time.time()
            self.total_audio_processed += len(audio_array)
            
            if current_time - self.last_diagnostic_time > 5:
                logger.info(f"Total audio processed: {self.total_audio_processed} samples")
                logger.info(f"Audio buffer size: {len(self.audio_buffer) / 2} samples")
                self.last_diagnostic_time = current_time
                
            # Log audio data shape periodically
            logger.debug(f"Audio data: shape={audio_array.shape}, dtype={audio_array.dtype}")
            
            # Reset buffer every 0.5 seconds to focus on immediate commands
            # This makes the system much more responsive
            current_buffer_seconds = len(self.audio_buffer) / 2 / self.sample_rate
            if current_buffer_seconds > 0.5:
                logger.debug("Buffer exceeded 0.5 seconds, resetting")
                self.audio_buffer = bytearray()
                
            # Simple processing - create a fresh buffer instead of extending the existing one
            new_buffer = bytearray(self.audio_buffer)
            
            # Only add the new data if it's valid
            if len(audio_array) > 0:
                # Check audio energy - if it's very low, don't add to buffer
                audio_energy = np.mean(np.abs(audio_array))
                if audio_energy < 50:  # Very quiet, probably silence
                    logger.debug(f"Audio energy too low: {audio_energy:.2f}, skipping")
                    # Return current buffer anyway for processing
                    result = np.frombuffer(self.audio_buffer, dtype=np.int16)
                    return result if len(result) > 0 else None
                
                # Copy to buffer (safely)
                try:
                    new_buffer.extend(audio_array.tobytes())
                except Exception as e:
                    logger.error(f"Error extending buffer: {e}")
                    # Reset buffer and start fresh with current data
                    new_buffer = bytearray(audio_array.tobytes())
            
            # Update our instance buffer
            self.audio_buffer = new_buffer
            
            # Keep buffer within size limits
            max_bytes = self.buffer_limit * 2  # *2 for 16-bit samples
            if len(self.audio_buffer) > max_bytes:
                self.audio_buffer = self.audio_buffer[-max_bytes:]
            
            # Convert buffer back to numpy array
            try:
                result = np.frombuffer(self.audio_buffer, dtype=np.int16)
            except Exception as e:
                logger.error(f"Error converting buffer to array: {e}")
                self.audio_buffer = bytearray()  # Reset buffer on error
                return None
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            # Reset buffer on error to prevent cascading failures
            self.audio_buffer = bytearray()
            return None