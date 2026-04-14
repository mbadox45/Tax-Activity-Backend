import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "ArdiarTax App")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    TESSERACT_PATH: str | None = os.getenv("TESSERACT_PATH")

settings = Settings()

# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     APP_NAME: str = "ArdiarTax App"
#     DEBUG: bool = False
#     DATABASE_URL: str = "sqlite:///./test.db"
#     SECRET_KEY: str = "secret"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
#     ALGORITHM: str = "HS256"

#     class Config:
#         env_file = ".env"


# settings = Settings()