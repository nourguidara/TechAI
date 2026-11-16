from pathlib import Path
import os
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("LANGSMITH_HIDE_INPUTS", "true")
os.environ.setdefault("LANGSMITH_HIDE_OUTPUTS", "true")
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'sqlite:///./data/techstock.db'
    openai_api_key: str = ''
    openai_model: str = 'gpt-4.1-mini'
    langsmith_tracing: bool = False
    langsmith_project: str = 'techstock-ai'
    langsmith_api_key: str = ''
    email_mode: str = 'sandbox'
    smtp_host: str = 'localhost'
    smtp_port: int = 1025
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_from: str = 'orders@techstock.test'
    smtp_allowed_recipients: str = ''
    max_agent_steps: int = Field(default=12, ge=1, le=12)
    max_tool_retries: int = Field(default=2, ge=0, le=2)
    scraping_request_delay: float = Field(default=2, ge=2)
    scraping_max_pages: int = Field(default=20, ge=1, le=100)
    offer_max_age_hours: int = 48
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None

settings = Settings()
