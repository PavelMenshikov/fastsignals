from urllib.parse import quote

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def jupiter_swap_url(token_mint: str, amount_usdc: float, slippage_pct: float) -> str:
    amount = f"{amount_usdc:g}"
    slippage = f"{slippage_pct:g}"
    return (
        f"https://jup.ag/swap/{USDC_MINT}-{quote(token_mint)}"
        f"?inAmount={quote(amount)}&slippage={quote(slippage)}"
    )


def jupiter_sell_url(token_mint: str, slippage_pct: float) -> str:
    slippage = f"{slippage_pct:g}"
    return f"https://jup.ag/swap/{quote(token_mint)}-{USDC_MINT}?slippage={quote(slippage)}"


def dexscreener_url(token_mint: str) -> str:
    return f"https://dexscreener.com/solana/{quote(token_mint)}"
