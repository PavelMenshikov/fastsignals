from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .execution_policy import ExecutionAction, ExecutionDecision
from .links import dexscreener_url, jupiter_sell_url, jupiter_swap_url
from .models import SpreadSignal
from .trading import TradingMode


def signal_text(signal: SpreadSignal, decision: ExecutionDecision | None = None) -> str:
    security = signal.security
    prefix = "🔔 ARBITRAGE OPPORTUNITY"
    mode_line = ""
    if decision and decision.mode_snapshot == TradingMode.PAPER:
        prefix = "🧪 PAPER EXECUTION"
        mode_line = "Mode: PAPER — virtual execution only"
    elif decision and decision.mode_snapshot == TradingMode.AUTO:
        prefix = "🤖 AUTO EXECUTION"
        mode_line = "🟢 Executed automatically" if decision.accepted else f"Rejected: {decision.reason}"

    lines = [
        prefix,
        f"TOKEN: {signal.token_symbol}",
        "",
        "Route:",
        f"BUY  {signal.buy_dex}",
        "↓",
        f"SELL {signal.sell_dex}",
        "",
        f"Input: {signal.order_usdc:g} USDC",
        f"Expected output: {signal.order_usdc + signal.estimated_profit_usdc:.4f} USDC",
        f"Net profit: {signal.estimated_profit_usdc:+.4f} USDC",
        f"Net spread: {signal.net_spread_pct:+.2f}% (Gross: {signal.gross_spread_pct:.2f}%)",
        "Security: "
        f"{'✅' if security.mint_revoked else '❌'} Mint | "
        f"{'✅' if security.freeze_revoked else '❌'} Freeze | "
        f"LP {security.lp_locked_or_burned_pct:.0f}% | Top10 {security.top10_holders_pct:.0f}%",
        f"Contract: `{signal.token_mint}`",
    ]
    if mode_line:
        lines.insert(1, mode_line)
    return "\n".join(lines)


def signal_keyboard(
    signal: SpreadSignal,
    slippage_pct: float,
    decision: ExecutionDecision | None = None,
) -> InlineKeyboardMarkup:
    if decision and decision.action == ExecutionAction.SIMULATE_PAPER:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🧪 Paper execution recorded", callback_data="paper_status")],
                [InlineKeyboardButton(text="📈 График DexScreener", url=dexscreener_url(signal.token_mint))],
            ]
        )
    if decision and decision.action == ExecutionAction.EXECUTE_AUTO:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🤖 AUTO executed", callback_data="auto_status")],
                [InlineKeyboardButton(text="MANUAL", callback_data="mode:manual_confirm")],
                [InlineKeyboardButton(text="📈 График DexScreener", url=dexscreener_url(signal.token_mint))],
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🚀 EXECUTE ARBITRAGE ${signal.order_usdc:g}",
                    url=jupiter_swap_url(signal.token_mint, signal.order_usdc, slippage_pct),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"BUY {signal.token_symbol}",
                    url=jupiter_swap_url(signal.token_mint, signal.order_usdc, slippage_pct),
                ),
                InlineKeyboardButton(
                    text=f"SELL {signal.token_symbol}",
                    url=jupiter_sell_url(signal.token_mint, slippage_pct),
                ),
            ],
            [InlineKeyboardButton(text="📈 График DexScreener", url=dexscreener_url(signal.token_mint))],
        ]
    )
