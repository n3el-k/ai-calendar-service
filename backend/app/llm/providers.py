import os
import instructor
from openai import OpenAI

from app.llm.protocols import LLMProvider, T

class OllamaProvider:

    def __init__(self):

        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        url = os.getenv("OLLAMA_URL", "http://localhost:11434/v1")

        self.client = instructor.from_openai(
        OpenAI(base_url=url, api_key="ollama"),
            mode=instructor.Mode.JSON)
        
    def parse(self, system: str, user: str, response_model: type[T], context: dict | None = None) -> T:

        return self.client.chat.completions.create(
            model=self.model,
            response_model=response_model,
            context=context,
            max_retries=2,
            temperature=0,
            messages=[
                {"role":"system", "content":system},
                {"role":"user", "content":user}
            ]
        )

def get_provider() -> LLMProvider:
    service = os.getenv('LLM_PROVIDER', 'ollama')
    if service == 'ollama':
        return OllamaProvider()
    raise ValueError(f"Unknown Provider: {service}")
