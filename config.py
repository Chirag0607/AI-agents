import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
DB_PATH = os.getenv("DB_PATH", "tasks.db")
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "6"))
