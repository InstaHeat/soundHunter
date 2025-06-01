import os
import asyncio
import signal
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
import yt_dlp
import logging
import platform

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt"

# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Создаем папку для загрузок
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Обработчики команд
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🎵 Привет! Отправь мне название песни или исполнителя")

@dp.message(Command("help"))
async def help_handler(message: Message):
    help_text = (
        "🎵 Музыкальный бот\n\n"
        "Просто отправьте мне название песни или исполнителя, "
        "и я попробую найти и отправить вам аудио.\n\n"
        "Команды:\n"
        "/start - Начать работу\n"
        "/help - Эта справка"
    )
    await message.answer(help_text)

# Обработчик текстовых сообщений
@dp.message()
async def download_music(message: Message):
    try:
        query = message.text.strip()
        if not query:
            await message.answer("Пожалуйста, введите название песни или исполнителя")
            return

        await message.answer(f"🔍 Ищу: {query}...")

        ydl_opts = {
            # 'format': 'bestaudio/best',
            # 'postprocessors': [{
            #     'key': 'FFmpegExtractAudio',
            #     'preferredcodec': 'mp3',
            #     'preferredquality': '192',
            # }],
            # 'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
            # 'quiet': True,
            # 'cookies': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
            # 'socket_timeout': 30,
            # 'retries': 10,
            # 'max_filesize': 50 * 1024 * 1024,

    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
    }],
    'cookies': 'cookies.txt',
    'geo_bypass': True,
    'extractor_args': {'youtube': {'player_client': ['android']}},
    'quiet': True,
    'no_warnings': True,

        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if not info.get('entries'):
                    await message.answer("❌ Ничего не найдено. Попробуйте другой запрос.")
                    return
                
                if info['entries'][0].get('duration', 0) > 900:
                    await message.answer("❌ Слишком длинное видео. Максимальная длительность - 15 минут.")
                    return
                
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)['entries'][0]
                filename = ydl.prepare_filename(info)
                mp3_path = os.path.splitext(filename)[0] + '.mp3'

                if not os.path.exists(mp3_path):
                    await message.answer("❌ Не удалось обработать аудиофайл.")
                    return

                audio_file = FSInputFile(mp3_path)
                await message.reply_audio(
                    audio=audio_file,
                    title=info.get('title', 'Audio')[:64],
                    performer=info.get('uploader', 'Unknown artist')[:64],
                    read_timeout=180,
                    write_timeout=180,
                    connect_timeout=180
                )

        except yt_dlp.utils.DownloadError as e:
            if "File is larger than max-filesize" in str(e):
                await message.answer("❌ Файл слишком большой (максимум 50MB)")
            else:
                await message.answer(f"❌ Ошибка загрузки: {str(e)}")

    except Exception as e:
        logger.error(f"Error processing {message.text}: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке вашего запроса.")
    
    finally:
        if 'mp3_path' in locals() and os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")

async def shutdown():
    """Корректное завершение работы"""
    logger.info("Shutting down...")
    await dp.storage.close()
    await bot.session.close()

def handle_exit():
    """Обработчик завершения работы для Windows"""
    logger.info("Received exit signal, shutting down...")
    # Для Windows просто ставим флаг, что нужно завершить работу
    asyncio.create_task(shutdown())

async def main():
    try:
        # Для Unix-систем регистрируем обработчики сигналов
        if platform.system() != 'Windows':
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        else:
            # Для Windows используем обработчик через try/except
            pass

        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Polling cancelled")
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
        await shutdown()
    except Exception as e:
        logger.error(f"Error in polling: {e}")
    finally:
        await shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")