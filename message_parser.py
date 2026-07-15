"""
Message parsing module to extract commitments from user responses.

Can use OpenAI API for intelligent parsing or fallback to simple pattern matching.
"""

import re
import logging
from typing import Dict, Optional, Tuple
import os

logger = logging.getLogger(__name__)

# Try to import OpenAI, but make it optional
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Using simple parsing.")

# Try to import Gemini, but make it optional
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-genai library not available. Gemini parsing will not be available.")


class MessageParser:
    """Parses user messages to extract today's work and tomorrow's commitments."""
    
    def __init__(
        self,
        use_openai: bool = False,
        openai_api_key: Optional[str] = None,
        use_gemini: bool = False,
        gemini_api_key: Optional[str] = None
    ):
        """
        Initialize the message parser.
        
        Args:
            use_openai: Whether to use OpenAI API for parsing
            openai_api_key: OpenAI API key (if use_openai is True)
            use_gemini: Whether to use Gemini API for parsing
            gemini_api_key: Gemini API key (if use_gemini is True)
        """
        self.use_openai = use_openai and OPENAI_AVAILABLE
        self.use_gemini = use_gemini and GEMINI_AVAILABLE
        
        if self.use_openai:
            if not openai_api_key:
                openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if openai_api_key:
                openai.api_key = openai_api_key
                logger.info("OpenAI API initialized for message parsing")
            else:
                logger.warning("OpenAI requested but no API key provided. Falling back to simple parsing.")
                self.use_openai = False

        self.gemini_client = None
        if self.use_gemini:
            if not gemini_api_key:
                gemini_api_key = os.getenv("GEMINI_API_KEY")
            
            if gemini_api_key:
                try:
                    self.gemini_client = genai.Client(api_key=gemini_api_key)
                    logger.info("Gemini API initialized for message parsing")
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini Client: {e}")
                    self.use_gemini = False
            else:
                logger.warning("Gemini requested but no API key provided. Falling back.")
                self.use_gemini = False
    
    def parse_message(self, message: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse a user message to extract yesterday's work, today's work, and blockers.
        
        Args:
            message: The user's message text
            
        Returns:
            Tuple of (today_work, tomorrow_commitment, blockers)
        """
        if self.use_gemini:
            return self._parse_with_gemini(message)
        elif self.use_openai:
            return self._parse_with_openai(message)
        else:
            return self._parse_simple(message)
    
    def _parse_with_gemini(self, message: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Use Gemini API to intelligently parse the message.
        
        Args:
            message: The user's message text
            
        Returns:
            Tuple of (today_work, tomorrow_commitment, blockers)
        """
        try:
            prompt = f"""Parse the following standup message and extract:
1. What the user worked on yesterday
2. What the user committed to work on today
3. Any blockers or challenges the user mentioned

Message: "{message}"

Respond in JSON format:
{{
    "today_work": "what they worked on yesterday or null",
    "tomorrow_commitment": "what they committed to do today or null",
    "blockers": "any blockers or challenges they mentioned or null"
}}

Only extract clear statements. If something is vague or uncertain, set it to null."""

            response = self.gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            
            import json
            result = json.loads(response.text)
            
            today_work = result.get("today_work")
            tomorrow_commitment = result.get("tomorrow_commitment")
            blockers = result.get("blockers")
            
            # Clean up null strings
            today_work = today_work if today_work and today_work.lower() != "null" else None
            tomorrow_commitment = tomorrow_commitment if tomorrow_commitment and tomorrow_commitment.lower() != "null" else None
            blockers = blockers if blockers and blockers.lower() != "null" else None
            
            logger.info(f"Gemini parsed message: today={bool(today_work)}, tomorrow={bool(tomorrow_commitment)}, blockers={bool(blockers)}")
            return today_work, tomorrow_commitment, blockers
            
        except Exception as e:
            logger.error(f"Error parsing with Gemini: {e}. Falling back.")
            if self.use_openai:
                return self._parse_with_openai(message)
            else:
                return self._parse_simple(message)

    def _parse_with_openai(self, message: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Use OpenAI API to intelligently parse the message.
        
        Args:
            message: The user's message text
            
        Returns:
            Tuple of (today_work, tomorrow_commitment, blockers)
        """
        try:
            client = openai.OpenAI()
            
            prompt = f"""Parse the following standup message and extract:
1. What the user worked on yesterday
2. What the user committed to work on today
3. Any blockers or challenges the user mentioned

Message: "{message}"

Respond in JSON format:
{{
    "today_work": "what they worked on yesterday or null",
    "tomorrow_commitment": "what they committed to do today or null",
    "blockers": "any blockers or challenges they mentioned or null"
}}

Only extract clear statements. If something is vague or uncertain, set it to null."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured information from standup messages."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            today_work = result.get("today_work")
            tomorrow_commitment = result.get("tomorrow_commitment")
            blockers = result.get("blockers")
            
            # Clean up null strings
            today_work = today_work if today_work and today_work.lower() != "null" else None
            tomorrow_commitment = tomorrow_commitment if tomorrow_commitment and tomorrow_commitment.lower() != "null" else None
            blockers = blockers if blockers and blockers.lower() != "null" else None
            
            logger.info(f"OpenAI parsed message: today={bool(today_work)}, tomorrow={bool(tomorrow_commitment)}, blockers={bool(blockers)}")
            return today_work, tomorrow_commitment, blockers
            
        except Exception as e:
            logger.error(f"Error parsing with OpenAI: {e}. Falling back to simple parsing.")
            return self._parse_simple(message)
    
    def _parse_simple(self, message: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Simple pattern-based parsing as fallback.
        
        Looks for common patterns like:
        - "yesterday I worked on...", "yesterday...", "yesterday's work..."
        - "today I will...", "today...", "today's work..."
        - "blockers...", "blocking..."
        
        Args:
            message: The user's message text
            
        Returns:
            Tuple of (today_work, tomorrow_commitment, blockers)
        """
        message_lower = message.lower()
        
        # Patterns for yesterday's work
        yesterday_patterns = [
            r"yesterday\s+(?:i\s+)?(?:worked\s+on|did|completed|finished|accomplished)\s*:?\s*(.+?)(?:\s+today|\s+blocker|$)",
            r"(?:worked\s+on|did|completed|finished|accomplished)\s*:?\s*(.+?)(?:\s+today|\s+blocker|$)",
            r"yesterday's?\s+work\s*:?\s*(.+?)(?:\s+today|\s+blocker|$)",
            r"yesterday\s*:?\s*(.+?)(?:\s+today|\s+blocker|$)",
        ]
        
        # Patterns for today's work
        today_patterns = [
            r"today\s+(?:i\s+)?(?:will|plan\s+to|going\s+to|gonna|work\s+on|am\s+working\s+on|do)\s*(?:work\s+on|do|complete|finish)?\s*:?\s*(.+?)(?:\s+blocker|$)",
            r"today's?\s+work\s*:?\s*(.+?)(?:\s+blocker|$)",
            r"today\s*:?\s*(.+?)(?:\s+blocker|$)",
            r"(?:will|plan\s+to|going\s+to|gonna|working\s+on)\s+(?:work\s+on|do|complete|finish)?\s*(.+?)(?:\.|\s+blocker|$)",
        ]

        # Patterns for blockers
        blocker_patterns = [
            r"(?:blocker|blocking|obstacle|challenge)s?\s*:?\s*(.+)",
        ]
        
        today_work = None
        tomorrow_commitment = None
        blockers = None
        
        # Try to extract blockers first if they exist, to prevent them bleeding into today/tomorrow
        for pattern in blocker_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE | re.DOTALL)
            if match:
                blockers = match.group(1).strip()
                if blockers:
                    break
        
        # If blockers found, clean them up
        if blockers:
            # Clean up common prefixes
            blockers = re.sub(r"^(none|no|nil)\b.*", "", blockers, flags=re.IGNORECASE)
            if blockers:
                blockers = blockers.strip(".,;: \n\r")
                if len(blockers) < 3:
                    blockers = None

        # Try to extract yesterday's work (today_work variable)
        for pattern in yesterday_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE | re.DOTALL)
            if match:
                today_work = match.group(1).strip()
                today_work = re.sub(r"^(on|that|the)\s+", "", today_work, flags=re.IGNORECASE)
                if today_work:
                    break
        
        # Try to extract today's work (tomorrow_commitment variable)
        for pattern in today_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE | re.DOTALL)
            if match:
                tomorrow_commitment = match.group(1).strip()
                tomorrow_commitment = re.sub(r"^(on|that|the)\s+", "", tomorrow_commitment, flags=re.IGNORECASE)
                if tomorrow_commitment:
                    break
        
        # Fallbacks for split-based parsing if patterns fail
        if not tomorrow_commitment and "today" in message_lower:
            parts = re.split(r"today", message_lower, flags=re.IGNORECASE)
            if len(parts) > 1:
                today_part = parts[1]
                if "blocker" in today_part:
                    today_part = today_part.split("blocker")[0]
                tomorrow_commitment = today_part.strip()
                tomorrow_commitment = re.sub(r"^(i\s+)?(?:will|plan\s+to|going\s+to|gonna|work\s+on|do)?\s*:?\s*", "", tomorrow_commitment, flags=re.IGNORECASE)
                if tomorrow_commitment:
                    tomorrow_commitment = tomorrow_commitment.strip(".,;: ")
        
        if not today_work and "yesterday" in message_lower:
            parts = re.split(r"yesterday", message_lower, flags=re.IGNORECASE)
            if len(parts) > 1:
                yesterday_part = parts[1]
                if "today" in yesterday_part:
                    yesterday_part = yesterday_part.split("today")[0]
                if "blocker" in yesterday_part:
                    yesterday_part = yesterday_part.split("blocker")[0]
                today_work = yesterday_part.strip()
                today_work = re.sub(r"^(i\s+)?(?:worked\s+on|did|completed|finished|accomplished)\s*:?\s*", "", today_work, flags=re.IGNORECASE)
                if today_work:
                    today_work = today_work.strip(".,;: ")
        
        # If still no match, try to split on common separators
        if not today_work and not tomorrow_commitment:
            sentences = re.split(r"[\.\n]", message, flags=re.IGNORECASE)
            if len(sentences) >= 2:
                today_work = sentences[0].strip()
                tomorrow_commitment = sentences[1].strip()
        
        # Clean up results
        if today_work:
            today_work = today_work.strip(".,;: \n\r")
            if len(today_work) < 3:
                today_work = None
        
        if tomorrow_commitment:
            tomorrow_commitment = tomorrow_commitment.strip(".,;: \n\r")
            if len(tomorrow_commitment) < 3:
                tomorrow_commitment = None
        
        logger.debug(f"Simple parsing result: today={bool(today_work)}, tomorrow={bool(tomorrow_commitment)}, blockers={bool(blockers)}")
        return today_work, tomorrow_commitment, blockers

