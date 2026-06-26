from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str
    ROBOFLOW_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    GEMINI_API_KEY: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
