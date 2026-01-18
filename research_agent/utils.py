import logging
import sys
import os
from typing import Optional

def setup_logger(name: str = "research_agent", level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a standard logger for the agent."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if they exist
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logger("llm_client")

class LLMClient:
    def __init__(self, provider: str = "auto", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.client = None
        
        if self.provider == "auto":
            if os.environ.get("GOOGLE_API_KEY"):
                self.provider = "google"
            elif os.environ.get("OPENAI_API_KEY"):
                self.provider = "openai"
            else:
                self.provider = "mock"
                logger.warning("No API keys found. Defaulting to MOCK LLM.")

        self._init_client()

    def _init_client(self):
        try:
            if self.provider == "google":
                import google.generativeai as genai
                if not self.api_key:
                     raise ValueError("Google API Key required")
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel('gemini-3-flash-preview')
                logger.info("Initialized Google Gemini Client (gemini-3-flash-preview)")
                
            elif self.provider == "openai":
                from openai import OpenAI
                if not self.api_key:
                    raise ValueError("OpenAI API Key required")
                self.client = OpenAI(api_key=self.api_key)
                logger.info("Initialized OpenAI Client")
                
            elif self.provider == "mock":
                logger.info("Initialized Mock Client")
                
        except ImportError as e:
            logger.error(f"Failed to import library for {self.provider}: {e}")
            self.provider = "mock"
        except Exception as e:
            logger.error(f"Failed to initialize {self.provider}: {e}")
            self.provider = "mock"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "google":
            try:
                # Gemini doesn't always support system instructions purely in the same way, 
                # but we can prepend it or use the system_instruction arg if supported by lib version.
                # safely prepending for compatibility.
                full_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"
                response = self.client.generate_content(full_prompt)
                return response.text
            except Exception as e:
                logger.error(f"Google generation failed: {e}")
                return "{}"

        elif self.provider == "openai":
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI generation failed: {e}")
                return "{}"

        else: # Mock
            return self._mock_response(user_prompt)

    def _mock_response(self, prompt: str) -> str:
        # Return a valid JSON based on simple keyword matching or just a default
        logger.info("Returning MOCK response")
        return """
        {
            "research_goal": "Mock Research Plan",
            "assumptions": ["Mock Assumption"],
            "steps": [
                {
                    "id": 1,
                    "type": "research",
                    "description": "Mock Step 1",
                    "constraints": ["None"]
                },
                {
                    "id": 2,
                    "type": "synthesize",
                    "description": "Mock Synthesis",
                    "inputs": [1]
                }
            ],
            "stop_conditions": {"max_steps": 5}
        }
        """
