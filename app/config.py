from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    anthropic_api_key: str
    perplexity_api_key: str
    google_yt_api_key: str
    google_gemini_api_key: str
    webshare_username: str
    webshare_password: str
    
    environment: str = "dev"
    frontend_url: str = "https://youtube-fact-chekcer-ui.onrender.com"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings():
    return Settings() 