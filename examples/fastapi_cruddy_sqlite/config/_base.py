import os
from pydantic_settings import BaseSettings


class Base(BaseSettings):
    class Config:
        case_sensitive = True
        env_file = os.path.expanduser("~/.env")
        env_file_encoding = "utf-8"
