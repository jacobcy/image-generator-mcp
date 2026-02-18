from typing import Optional, Dict, Any
from pathlib import Path
import os
import json
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    """
    Application configuration using Pydantic Settings.
    Loads from environment variables (prefix CRC_) and .env file.
    """
    # API Keys
    ttapi_api_key: Optional[SecretStr] = Field(None, alias="TTAPI_API_KEY")
    openai_api_key: Optional[SecretStr] = Field(None, alias="OPENAI_API_KEY")
    imgbb_api_key: Optional[SecretStr] = Field(None, alias="IMGBB_API_KEY")
    server_api_key: Optional[SecretStr] = Field(None, alias="SERVER_API_KEY")

    # Directories
    crc_base_dir: Path = Field(default_factory=lambda: Path.cwd() / ".crc")
    global_config_dir: Path = Field(default_factory=lambda: Path.home() / ".crc")
    
    # Defaults
    default_model: str = "relax"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CRC_" # Allows CRC_TTAPI_API_KEY to override
    )

    @property
    def log_dir(self) -> Path:
        return self.crc_base_dir / "logs"

    @property
    def state_dir(self) -> Path:
        return self.crc_base_dir / "state"

    @property
    def metadata_dir(self) -> Path:
        return self.crc_base_dir / "metadata"

    @property
    def output_dir(self) -> Path:
        # Try to load from state/config.json if it exists
        state_config = self.state_dir / "config.json"
        if state_config.exists():
            try:
                with open(state_config, "r") as f:
                    data = json.load(f)
                    if "output_dir" in data:
                        return Path(data["output_dir"])
            except Exception:
                pass
        return self.crc_base_dir / "output"

    def get_ttapi_key(self) -> Optional[str]:
        return self.ttapi_api_key.get_secret_value() if self.ttapi_api_key else None

    def get_openai_key(self) -> Optional[str]:
        return self.openai_api_key.get_secret_value() if self.openai_api_key else None
