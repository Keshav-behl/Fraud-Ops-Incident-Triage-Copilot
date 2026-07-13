import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_CHAT_MODEL = os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.1-8b-instruct")
    NVIDIA_EMBED_MODEL = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")

    JIRA_SITE_URL = os.getenv("JIRA_SITE_URL")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    JIRA_JSM_PROJECT_KEY = os.getenv("JIRA_JSM_PROJECT_KEY", "FOT")

    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_ESCALATION_CHANNEL = os.getenv("SLACK_ESCALATION_CHANNEL", "#fraud-ops-escalations")

    CONFIDENCE_ESCALATION_THRESHOLD = float(os.getenv("CONFIDENCE_ESCALATION_THRESHOLD", "65"))
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/triage.db")


settings = Settings()
