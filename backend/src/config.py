from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://autotrade_app:postgres@localhost:5432/autotrade_db"
    cors_origins: str = "http://localhost:3000"
    live_trading_enabled: bool = False

    helius_api_key: str = ""
    solana_rpc_url_override: str = ""
    data_freshness_max_age_sec: int = 30

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    openrouter_default_model: str = "anthropic/claude-haiku-5.5"
    nineroute_base_url: str = ""
    nineroute_api_key: str = ""
    nineroute_default_model: str = "google/gemini-flash-1.5"

    initial_paper_capital_usd: Decimal = Decimal("10000.00")
    max_risk_per_trade_pct: Decimal = Decimal("0.005")
    daily_loss_limit_pct: Decimal = Decimal("0.02")
    max_drawdown_limit_pct: Decimal = Decimal("0.08")
    max_spread_pct: Decimal = Decimal("0.0008")

    # Rust Risk Gate (RUST_ENGINE_INTEGRATION_SPEC.md §6.1). Empty = in-process Python gate only.
    engine_url: str = ""
    engine_timeout_ms: int = 10

    telegram_bot_token: str = ""
    telegram_allowed_user_id: str = ""
    telegram_allowed_chat_id: str = ""

    @property
    def solana_rpc_url(self) -> str:
        # Q-04: Helius Free Tier primer, Public RPC sebagai cadangan jika key belum diisi.
        if self.solana_rpc_url_override:
            return self.solana_rpc_url_override
        if self.helius_api_key and "your_helius_api_key_here" not in self.helius_api_key:
            return f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}"
        return "https://api.mainnet-beta.solana.com"


settings = Settings()
