import multiprocessing
import pathlib

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# root directory
ROOT_PATH = str(pathlib.Path(__file__).parent.parent.parent)


class Settings(BaseSettings):
    # main db credentials
    POSTGRES_USER: str = Field(default='postgres', env='POSTGRES_USER')
    POSTGRES_PASSWORD: str = Field(default='postgres', env='POSTGRES_PASSWORD')
    POSTGRES_HOST: str = Field(default='localhost', env='POSTGRES_HOST')
    POSTGRES_PORT: int = Field(default=5432, env='POSTGRES_PORT')
    POSTGRES_DB: str = Field(default='postgres', env='POSTGRES_DB')
    # parser settings
    WEBDRIVER: str = Field(default='chrome', env='WEBDRIVER')
    ACCOUNT_DAILY_USAGE_RATE: int = Field(default=150, env='ACCOUNT_DAILY_USAGE_RATE')
    PROCESS_COUNT: int = Field(default=multiprocessing.cpu_count(), env='PROCESS_COUNT')
    PARSER_BETWEEN_RESTARTS_SLEEP_SEC: int = Field(default=1900, env='PARSER_BETWEEN_RESTARTS_SLEEP_SEC')

    class Config:
        env_prefix = ''
        case_sentive = False
        env_file = '../.env'
        env_file_encoding = 'utf-8'


# load env from file
load_dotenv()

# load vars to settings
settings = Settings()
