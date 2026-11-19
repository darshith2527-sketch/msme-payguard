"""App settings, read from environment variables (see backend/.env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()

# SQLite works out of the box; switch to Postgres with e.g.
# postgresql+psycopg://payguard:payguard@localhost:5432/payguard
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./payguard.db")

# RBI Bank Rate in percent. MSMED Act s.16 interest = 3x this rate,
# compounded monthly. VERIFY the current rate on rbi.org.in before demoing.
RBI_BANK_RATE = float(os.getenv("RBI_BANK_RATE", "5.75"))

# Invoices due within this many days are flagged "due_soon".
DUE_SOON_DAYS = int(os.getenv("DUE_SOON_DAYS", "7"))

# Optional LLM for polishing reminder letters. Any OpenAI-compatible
# chat-completions endpoint works (OpenAI, Gemini, Groq, Ollama, ...).
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
