from typing import List, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    # Обязательные параметры
    TELEGRAM_TOKEN: str
    YANDEX_MUSIC_TOKEN: str
    ALLOWED_USER_IDS: List[int]

    # Параметры загрузки
    QUALITY: Literal[0, 1, 2] = 2
    SKIP_EXISTING: bool = True
    LYRICS_FORMAT: Literal['none', 'text', 'lrc'] = 'text'
    EMBED_COVER: bool = True
    COVER_RESOLUTION: str = 'original'
    DELAY: float = 0
    STICK_TO_ARTIST: bool = False
    ONLY_MUSIC: bool = False
    COMPATIBILITY_LEVEL: float = 1

    # Пути
    DOWNLOAD_DIR: str = './downloads'

    @field_validator('ALLOWED_USER_IDS', mode='before')
    def parse_user_ids(cls, v):
        if isinstance(v, str):
            return [int(id.strip()) for id in v.split(',')]
        return v

    @field_validator('COVER_RESOLUTION')
    def validate_cover_resolution(cls, v):
        if v.lower() != 'original' and not v.isdigit():
            raise ValueError('COVER_RESOLUTION must be "original" or number')
        return v.lower() if v.lower() == 'original' else v

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'