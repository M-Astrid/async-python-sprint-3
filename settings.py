from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HTTP_MAX_LINE: int = 64 * 1024
    HTTP_MAX_HEADERS: int = 100
