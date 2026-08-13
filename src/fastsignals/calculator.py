from .models import PoolQuote, SecurityReport, SpreadSignal


def calculate_net_spread(
    low: PoolQuote,
    high: PoolQuote,
    security: SecurityReport,
    order_usdc: float,
    dex_fee_pct: float,
    slippage_pct: float,
    priority_fee_usdc: float,
) -> SpreadSignal | None:
    """Return an executable signal when the high quote beats the low quote after costs."""
    if low.price_usdc <= 0 or high.price_usdc <= 0 or high.price_usdc <= low.price_usdc:
        return None

    gross_spread_pct = ((high.price_usdc - low.price_usdc) / low.price_usdc) * 100
    total_variable_cost_pct = dex_fee_pct * 2 + slippage_pct
    fixed_cost_pct = (priority_fee_usdc / order_usdc) * 100 if order_usdc else 0
    net_spread_pct = gross_spread_pct - total_variable_cost_pct - fixed_cost_pct
    estimated_profit_usdc = order_usdc * net_spread_pct / 100

    return SpreadSignal(
        token_mint=low.token_mint,
        token_symbol=low.token_symbol,
        buy_dex=low.dex,
        sell_dex=high.dex,
        gross_spread_pct=round(gross_spread_pct, 4),
        net_spread_pct=round(net_spread_pct, 4),
        estimated_profit_usdc=round(estimated_profit_usdc, 4),
        order_usdc=order_usdc,
        security=security,
    )
