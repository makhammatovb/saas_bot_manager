import os
from dotenv import load_dotenv

load_dotenv()


def _get_int_list(name: str) -> list[int]:
    raw = os.getenv(name, "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_PATH = os.getenv("SESSION_PATH", os.path.join(BASE_DIR, "userbot", "userbot_session"))


ADMIN_IDS = _get_int_list("ADMIN_IDS")
DATABASE_URL = os.getenv("DATABASE_URL", "")
ADD_DELAY_SECONDS = int(os.getenv("ADD_DELAY_SECONDS", "45"))
REMOVE_DELAY_SECONDS = int(os.getenv("REMOVE_DELAY_SECONDS", "5"))
DAILY_ADD_LIMIT = int(os.getenv("DAILY_ADD_LIMIT", "25"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
