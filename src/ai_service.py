import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

CANDIDATE_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]

class AIService:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    def generate_briefing(self, prompt: str, system_instruction: str) -> str:
        config = types.GenerateContentConfig(system_instruction=system_instruction)
        for model_name in CANDIDATE_MODELS:
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=model_name, contents=prompt, config=config
                    )
                    return response.text
                except ServerError:
                    time.sleep((attempt + 1) * 6)
                except ClientError:
                    break
                except Exception:
                    time.sleep(5)
        raise RuntimeError("All Gemini models failed.")
