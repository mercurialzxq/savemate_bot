from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    bot_token: SecretStr = Field(
        default=SecretStr(""),
        description="Telegram bot token obtained from @BotFather",
        validation_alias="BOT_TOKEN",
    )
    download_timeout: int = Field(
        default=60,
        description="Timeout in seconds for downloading media",
        validation_alias="DOWNLOAD_TIMEOUT",
    )
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size in MB for Telegram bot uploads",
        validation_alias="MAX_FILE_SIZE_MB",
    )
    temp_dir: Path = Field(
        default=Path("./tmp"),
        description="Temporary directory for downloaded media files",
        validation_alias="TEMP_DIR",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_token(self) -> None:
        """Validate that the bot token is set and not empty."""
        token_val = self.bot_token.get_secret_value().strip()
        if not token_val:
            raise ValueError(
                "BOT_TOKEN is not set! Please set BOT_TOKEN in your .env file or environment variables."
            )


config = Settings()
