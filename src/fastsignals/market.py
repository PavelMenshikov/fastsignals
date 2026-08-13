import aiohttp

from .models import PoolQuote

DEX_ALLOWLIST = {"raydium", "orca", "meteora"}


class MarketDataClient:
    """Fetches high-frequency Solana pool data from DexScreener-compatible APIs."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def fetch_quotes(self, session: aiohttp.ClientSession) -> list[PoolQuote]:
        async with session.get(f"{self.base_url}/latest/dex/search", params={"q": "SOLANA"}, timeout=2) as resp:
            resp.raise_for_status()
            data = await resp.json()

        quotes: list[PoolQuote] = []
        for pair in data.get("pairs", []):
            if pair.get("chainId") != "solana":
                continue
            dex = str(pair.get("dexId", "")).lower()
            if dex not in DEX_ALLOWLIST:
                continue
            base = pair.get("baseToken") or {}
            liquidity = pair.get("liquidity") or {}
            volume = pair.get("volume") or {}
            try:
                quotes.append(
                    PoolQuote(
                        token_mint=base["address"],
                        token_symbol=base.get("symbol", "UNKNOWN"),
                        dex=dex,
                        price_usdc=float(pair["priceUsd"]),
                        liquidity_usd=float(liquidity.get("usd") or 0),
                        volume_24h_usd=float(volume.get("h24") or 0),
                        pool_address=pair.get("pairAddress", ""),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return quotes
