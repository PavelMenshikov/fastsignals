from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str = Field(default="", alias="BOT_TOKEN")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    database_url: str = Field(default="signals.db", alias="DATABASE_URL")

    birdeye_api_key: str = Field(default="", alias="BIRDEYE_API_KEY")
    rugcheck_base_url: HttpUrl = Field(default="https://api.rugcheck.xyz", alias="RUGCHECK_BASE_URL")
    dexscreener_base_url: HttpUrl = Field(
        default="https://api.dexscreener.com", alias="DEXSCREENER_BASE_URL"
    )

    default_order_usdc: float = Field(default=25.0, alias="DEFAULT_ORDER_USDC")
    default_min_net_spread_pct: float = Field(default=0.8, alias="DEFAULT_MIN_NET_SPREAD_PCT")
    default_min_liquidity_usd: float = Field(default=5_000.0, alias="DEFAULT_MIN_LIQUIDITY_USD")
    default_min_volume_24h_usd: float = Field(default=10_000.0, alias="DEFAULT_MIN_VOLUME_24H_USD")
    slippage_pct: float = Field(default=0.5, alias="SLIPPAGE_PCT")
    dex_fee_pct: float = Field(default=0.3, alias="DEX_FEE_PCT")
    priority_fee_usdc: float = Field(default=0.01, alias="PRIORITY_FEE_USDC")
    poll_interval_seconds: float = Field(default=1.0, alias="POLL_INTERVAL_SECONDS")

    @property
    def admin_id_set(self) -> set[int]:
        return {int(item.strip()) for item in self.admin_ids.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
