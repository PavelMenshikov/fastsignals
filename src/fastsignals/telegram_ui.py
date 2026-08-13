from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .links import dexscreener_url, jupiter_sell_url, jupiter_swap_url
from .models import SpreadSignal


def signal_text(signal: SpreadSignal) -> str:
    security = signal.security
    return "\n".join(
        [
            f"🔔 СИГНАЛ: {signal.token_symbol}",
            f"📊 Чистый спред: +{signal.net_spread_pct:.2f}% (Грязный: {signal.gross_spread_pct:.2f}%)",
            f"💰 Расчетный профит с {signal.estimated_profit_usdc:.2f} USDC",
            "🛡️ Безопасность: "
            f"{'✅' if security.mint_revoked else '❌'} Mint Revoked | "
            f"{'✅' if security.freeze_revoked else '❌'} Freeze Revoked | "
            f"✅ LP {security.lp_locked_or_burned_pct:.0f}% Burned/Locked",
            f"🕯️ Контракт: `{signal.token_mint}`",
            f"Маршрут: купить на {signal.buy_dex}, продать на {signal.sell_dex}",
        ]
    )


def signal_keyboard(signal: SpreadSignal, slippage_pct: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🚀 Купить на ${signal.order_usdc:g} (Jupiter)",
                    url=jupiter_swap_url(signal.token_mint, signal.order_usdc, slippage_pct),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💸 Продать {signal.token_symbol} (Jupiter)",
                    url=jupiter_sell_url(signal.token_mint, slippage_pct),
                )
            ],
            [InlineKeyboardButton(text="📈 График DexScreener", url=dexscreener_url(signal.token_mint))],
        ]
    )
