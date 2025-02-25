import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class CommandHandler:
    """
    Process transcribed text to detect and handle commands
    """
    
    def __init__(self):
        """Initialize the command handler"""
        # Define command keywords and synonyms
        self.commands = {
            "play": ["play", "start", "begin", "resume", "go"],
            "pause": ["pause", "stop", "halt", "freeze", "wait"]
        }
        
        # Cooldown to prevent rapid command triggering
        self.last_command = None
        self.last_command_time = 0
        self.command_cooldown = 1.0  # seconds between allowed repeated commands
    
    def process_command(self, text: str) -> Optional[str]:
        """
        Process text to detect commands
        
        Args:
            text: Transcribed text from ASR
            
        Returns:
            Detected command or None
        """
        if not text:
            return None
            
        text = text.lower().strip()
        
        # Print for debugging
        logger.info(f"[COMMAND PROCESSOR] Processing: '{text}'")
        
        # Check for direct command matches (exact word or substring)
        for command, keywords in self.commands.items():
            # First check if the command itself is in the text
            if command in text:
                logger.info(f"[COMMAND PROCESSOR] Command found: {command}")
                return self._apply_cooldown(command)
        
        # Check for any keyword in text (more lenient)
        for command, keywords in self.commands.items():
            for keyword in keywords:
                # Check if keyword appears as whole word
                if keyword in text.split() or f" {keyword} " in f" {text} ":
                    logger.info(f"[COMMAND PROCESSOR] Keyword '{keyword}' found for command: {command}")
                    return self._apply_cooldown(command)
                
                # Even more lenient - check if keyword appears anywhere
                if keyword in text:
                    logger.info(f"[COMMAND PROCESSOR] Substring '{keyword}' found for command: {command}")
                    return self._apply_cooldown(command)
        
        # Special cases for common misrecognitions
        if "clay" in text or "lay" in text:
            logger.info("[COMMAND PROCESSOR] Possible 'play' misrecognition")
            return self._apply_cooldown("play")
            
        if "paws" in text or "cause" in text or "post" in text:
            logger.info("[COMMAND PROCESSOR] Possible 'pause' misrecognition")
            return self._apply_cooldown("pause")
        
        return None
    
    def _apply_cooldown(self, command: str) -> Optional[str]:
        """Apply cooldown logic to avoid rapid repeat commands"""
        current_time = time.time()
        
        # Check if this is a repeat command within cooldown period
        if command == self.last_command and current_time - self.last_command_time < self.command_cooldown:
            logger.info(f"[COMMAND PROCESSOR] Command '{command}' ignored due to cooldown")
            return None
            
        # Update last command info
        self.last_command = command
        self.last_command_time = current_time
        
        logger.info(f"[COMMAND PROCESSOR] Command '{command}' accepted!")
        return command