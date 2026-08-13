from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass(frozen=True)
class PoolQuote:
    token_mint: str
    token_symbol: str
    dex: str
    price_usdc: float
    liquidity_usd: float
    volume_24h_usd: float
    pool_address: str


@dataclass(frozen=True)
class SecurityReport:
    mint_revoked: bool
    freeze_revoked: bool
    lp_locked_or_burned_pct: float
    top10_holders_pct: float

    @property
    def is_safe(self) -> bool:
        return (
            self.mint_revoked
            and self.freeze_revoked
            and self.lp_locked_or_burned_pct >= 80
            and self.top10_holders_pct <= 30
        )


@dataclass(frozen=True)
class SpreadSignal:
    token_mint: str
    token_symbol: str
    buy_dex: str
    sell_dex: str
    gross_spread_pct: float
    net_spread_pct: float
    estimated_profit_usdc: float
    order_usdc: float
    security: SecurityReport
    created_at: datetime = datetime.now(UTC)

    @property
    def dedupe_key(self) -> str:
        bucket = int(self.created_at.timestamp() // 60)
        return f"{self.token_mint}:{self.buy_dex}:{self.sell_dex}:{bucket}"
