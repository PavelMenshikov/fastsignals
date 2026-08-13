import aiohttp

from .models import SecurityReport


class SecurityClient:
    """Token risk client using RugCheck-compatible responses with safe defaults."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def check(self, session: aiohttp.ClientSession, token_mint: str) -> SecurityReport:
        async with session.get(f"{self.base_url}/v1/tokens/{token_mint}/report", timeout=2) as resp:
            resp.raise_for_status()
            data = await resp.json()

        risks = data.get("risks", [])
        lp_pct = float(data.get("lpLockedPct") or data.get("lpBurnedPct") or 0)
        top10_pct = float(data.get("topHoldersPct") or 100)
        risk_names = {str(item.get("name", "")).lower() for item in risks if isinstance(item, dict)}

        return SecurityReport(
            mint_revoked="mint authority" not in risk_names,
            freeze_revoked="freeze authority" not in risk_names,
            lp_locked_or_burned_pct=lp_pct,
            top10_holders_pct=top10_pct,
        )
