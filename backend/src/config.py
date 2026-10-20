from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://autotrade_app:postgres@localhost:5432/autotrade_db"

    helius_api_key: str = ""
    solana_rpc_url_override: str = ""
    data_freshness_max_age_sec: int = 30

    @property
    def solana_rpc_url(self) -> str:
        # Q-04: Helius Free Tier primer, Public RPC sebagai cadangan jika key belum diisi.
        if self.solana_rpc_url_override:
            return self.solana_rpc_url_override
        if self.helius_api_key and "your_helius_api_key_here" not in self.helius_api_key:
            return f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}"
        return "https://api.mainnet-beta.solana.com"


settings = Settings()
