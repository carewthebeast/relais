from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Reglages(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env", extra="ignore")

    osrm_url: str = "http://127.0.0.1:5001"
    millisecondes_optimisation: int = 500


reglages = Reglages()
