"""Configuration du logging de l'API.

- Console (stdout) : format lisible  -> `docker compose logs api`
- Fichier logs/api.log : une ligne JSON par événement -> lu par Logstash (ELK)

Chaque log métier répond à : Quand ? Qui ? Quelle opération ? Quel modèle ?
Quel résultat ? Combien de temps ? Quelle erreur ?
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

SERVICE_NAME = "ml-churn-api"

# Attributs standards d'un LogRecord : tout le reste vient de `extra=`.
_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "taskName",
}


def _extras(record: logging.LogRecord) -> dict:
    return {
        k: v for k, v in record.__dict__.items()
        if k not in _STANDARD_ATTRS and not k.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """Une ligne JSON par log, prête à être indexée dans Elasticsearch."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        payload.update(_extras(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Format du sujet (asctime levelname message) + champs contextuels."""

    def __init__(self):
        super().__init__("%(asctime)s %(levelname)s %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = _extras(record)
        if extras:
            base += " " + " ".join(f"{k}={v}" for k, v in extras.items())
        return base


def setup_logging() -> logging.Logger:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(ConsoleFormatter())
    root.addHandler(console)

    if os.getenv("LOG_TO_FILE", "true").lower() == "true":
        log_dir = Path(os.getenv("LOG_DIR", Path(__file__).resolve().parents[1] / "logs"))
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_dir / "api.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            file_handler.setFormatter(JsonFormatter())
            root.addHandler(file_handler)
        except OSError as exc:  # le logging fichier ne doit jamais empêcher l'API de démarrer
            root.warning("Logging fichier désactivé : %s", exc)

    # Bibliothèques trop bavardes
    for noisy in ("httpx", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger(SERVICE_NAME)
