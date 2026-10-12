from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Loads .env into os.environ so the Anthropic SDK can find ANTHROPIC_API_KEY
# (pydantic-settings only reads values for the fields declared below)
load_dotenv()

class Settings(BaseSettings):
    llm_provider: str = "anthropic"
    anthropic_model: str = "claude-haiku-5-5"
    ollama_model: str = "qwen2.5:7b"
    ollama_url: str = "http://localhost:11434/v1"
    reset_db_on_start: bool = False
    db_path: Path = Path(__file__).resolve().parent.parent / "calendar.db"

settings = Settings()
