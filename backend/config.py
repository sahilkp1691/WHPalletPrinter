import os
import sys

from pydantic_settings import BaseSettings


def _default_data_dir() -> str:
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.join(os.path.dirname(sys.executable), "data"),
            os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "WHPalletPrinter",
                "data",
            ),
        ]
    else:
        candidates = [os.path.join(os.path.dirname(__file__), "..", "data")]

    for data_dir in candidates:
        data_dir = os.path.normpath(data_dir)
        try:
            os.makedirs(data_dir, exist_ok=True)
            return data_dir
        except OSError:
            continue

    raise RuntimeError("Could not create application data directory")


class Settings(BaseSettings):
    api_port: int = 8766
    data_dir: str = _default_data_dir()
    database_path: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def resolved_database_path(self) -> str:
        if self.database_path:
            return self.database_path
        return os.path.join(self.data_dir, "articles.db")


settings = Settings()
