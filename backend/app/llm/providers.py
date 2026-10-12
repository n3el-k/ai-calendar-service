import instructor
from openai import OpenAI
import anthropic
from functools import lru_cache

from app.config import settings
from app.llm.protocols import LLMProvider, T

class AnthropicProvider:

    def __init__(self):
        self.model = settings.anthropic_model
        self.client = instructor.from_anthropic(anthropic.Anthropic(), mode=instructor.Mode.ANTHROPIC_JSON, )        

    def parse(self, system, user, response_model, context=None):
        return self.client.messages.create(     
            model=self.model,
            max_tokens=400,                     
            system=system,                       
            messages=[{"role": "user", "content": user}],
            response_model=response_model,
            context=context,
            max_retries=2,
        )
        
class OllamaProvider:

    def __init__(self):

        self.model = settings.ollama_model
        url = settings.ollama_url

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

@lru_cache(maxsize=1)
def get_provider() -> LLMProvider:
    service = settings.llm_provider
    if service == 'ollama':
        return OllamaProvider()
    if service == 'anthropic':
        return AnthropicProvider()
    raise ValueError(f"Unknown Provider: {service}")