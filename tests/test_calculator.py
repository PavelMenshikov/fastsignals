from fastsignals.calculator import calculate_net_spread
from fastsignals.models import PoolQuote, SecurityReport


def quote(dex: str, price: float) -> PoolQuote:
    return PoolQuote("Mint111", "TKN", dex, price, 10_000, 20_000, "pool")


def test_calculate_net_spread_subtracts_all_costs() -> None:
    signal = calculate_net_spread(
        quote("raydium", 1.0),
        quote("orca", 1.017),
        SecurityReport(True, True, 100, 10),
        order_usdc=25,
        dex_fee_pct=0.3,
        slippage_pct=0.5,
        priority_fee_usdc=0.01,
    )

    assert signal is not None
    assert signal.gross_spread_pct == 1.7
    assert signal.net_spread_pct == 0.56
    assert signal.estimated_profit_usdc == 0.14


def test_no_signal_when_sell_price_is_not_higher() -> None:
    signal = calculate_net_spread(
        quote("raydium", 1.0), quote("orca", 1.0), SecurityReport(True, True, 100, 10), 25, 0.3, 0.5, 0.01
    )
    assert signal is None
