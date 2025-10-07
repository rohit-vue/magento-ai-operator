# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Load variables from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

    MAGENTO_STORE_URL: str
    MAGENTO_API_TOKEN: str
    LLM_API_KEY: str
    LLM_MODEL_NAME: str

# Create a single instance of the settings to be used throughout the app
settings = Settings()