import enum
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from ymd import YandexMusicDownloader, CoreTrackQuality, LyricsFormat

from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TRACK_RE = re.compile(r"track/(\d+)")
ALBUM_RE = re.compile(r"album/(\d+)$")
ARTIST_RE = re.compile(r"artist/(\d+)$")
PLAYLIST_RE = re.compile(r"([\w\-._@]+)/playlists/(\d+)$")

class ContentType(str, enum.Enum):
    TRACK = 0
    ALBUM = enum.auto()
    UNKNOWN = enum.auto()

class YandexMusicBot:
    def __init__(self, config: Config):
        self.config = config
        self.downloader = YandexMusicDownloader(config.YANDEX_MUSIC_TOKEN)

        Path(config.DOWNLOAD_DIR).mkdir(exist_ok=True)

    def _is_user_allowed(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if user_id not in self.config.ALLOWED_USER_IDS:
            logger.warning(f'Unauthorized access attempt by user {user_id}')
            return False
        return True

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_user_allowed(update):
            return

        user = update.effective_user
        await update.message.reply_html(
            f"Привет {user.mention_html()}! Я бот для скачивания музыки с Yandex Music.\n"
            "Просто отправь мне ссылку на трек, альбом или исполнителя.\n\n"
            f"Текущие настройки:\n"
            f"Качество: {self._get_quality_name()}\n"
            f"Пропускать существующие: {'Да' if self.config.SKIP_EXISTING else 'Нет'}\n"
            f"Текст песен: {self.config.LYRICS_FORMAT}\n"
            f"Обложка: {'Да' if self.config.EMBED_COVER else 'Нет'}"
        )

    def _get_quality_name(self) -> str:
        quality_map = {
            0: 'Низкое (AAC 64kbps)',
            1: 'Оптимальное (AAC 192kbps)',
            2: 'Лучшее (FLAC)'
        }
        return quality_map.get(self.config.QUALITY, 'Неизвестно')


    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_user_allowed(update):
            return

        await update.message.reply_text(
            "Отправь мне ссылку на:\n"
            "- Трек (например, https://music.yandex.ru/album/12345/track/54321)\n"
            "- Альбом (например, https://music.yandex.ru/album/12345)\n"
            # "- Исполнителя (например, https://music.yandex.ru/artist/123)\n\n"
            "Все параметры загрузки настраиваются через переменные окружения."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_user_allowed(update):
            return

        message = update.message
        url = message.text.strip()

        if not url.startswith(('https://music.yandex.ru/', 'http://music.yandex.ru/')):
            await message.reply_text("Пожалуйста, отправьте корректную ссылку на Yandex Music.")
            return

        try:
            content_type = self._detect_content_type(url)

            if content_type == ContentType.TRACK:
                await message.reply_text("Начинаю скачивание трека...")
                file_path =  self.downloader.download_track(
                    track_id=url,
                    output_dir=self.config.DOWNLOAD_DIR,
                    quality=CoreTrackQuality(self.config.QUALITY),
                    lyrics_format=LyricsFormat(self.config.LYRICS_FORMAT),
                    embed_cover=self.config.EMBED_COVER
                )
                await message.reply_text("Завершено скачивание.")
                await message.reply_audio(audio=open(file_path, 'rb'))

            elif content_type == ContentType.ALBUM:
                await message.reply_text("Начинаю скачивание альбома...")
                paths = self.downloader.download_album(
                    album_id=url,
                    output_dir=self.config.DOWNLOAD_DIR,
                    quality=CoreTrackQuality(self.config.QUALITY),
                    lyrics_format=LyricsFormat(self.config.LYRICS_FORMAT),
                    embed_cover=self.config.EMBED_COVER
                )
                await message.reply_text(f"Завершено скачивание {len(paths)} треков.")
                for path in paths:
                    await message.reply_audio(audio=open(path, 'rb'))

            # TODO
            # elif content_type == ContentType.ARTIST:
            #     await message.reply_text("Начинаю скачивание популярных треков исполнителя...")
            #     zip_path = await self.downloader.download_artist(url, **download_params)
            #     await message.reply_document(document=open(zip_path, 'rb'))

            else:
                await message.reply_text("Не удалось определить тип контента по ссылке.")

        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            await message.reply_text(f"Произошла ошибка: {str(e)}")


    def _detect_content_type(self, url: str) -> ContentType:
        parsed_url = urlparse(url)
        path = parsed_url.path
        if ALBUM_RE.search(path):
            return ContentType.ALBUM
        elif TRACK_RE.search(path):
            return ContentType.TRACK
        else:
            return ContentType.UNKNOWN


    def run(self):
        application = Application.builder().token(self.config.TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        application.run_polling()