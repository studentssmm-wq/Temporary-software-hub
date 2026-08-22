import os

from dotenv import load_dotenv


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
MONO_JAR_URL = os.getenv("MONO_JAR_URL")
