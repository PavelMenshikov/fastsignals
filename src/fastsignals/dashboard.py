from .paper import PaperAccount
from .trading import TradingMode, TradingState, TradingStatus


def dashboard_text(state: TradingState, paper: PaperAccount) -> str:
    mode_icon = {
        TradingMode.OFF: "⚫ OFF",
        TradingMode.MANUAL: "⚪ MANUAL",
        TradingMode.PAPER: "🧪 PAPER",
        TradingMode.AUTO: "🤖 AUTO",
    }[state.mode]
    status_icon = "🟢 RUNNING" if state.status == TradingStatus.RUNNING else f"🔴 {state.status.value}"
    paper_icon = "🟢 RUNNING" if state.paper_status == TradingStatus.RUNNING else "🔴 STOPPED"
    return "\n".join(
        [
            "⚡ FastSignals",
            "",
            f"Mode: {mode_icon}",
            f"Status: {status_icon}",
            "",
            f"Paper: {paper_icon}",
            f"Virtual balance: ${paper.virtual_usdc_balance:,.2f}",
            f"Equity: ${paper.equity_usdc:,.2f}",
            f"P&L: ${paper.virtual_pnl_usdc:+,.2f}",
            f"Trades: {paper.trades}",
            f"Win rate: {paper.win_rate_pct:.1f}%",
            "",
            "AUTO limits:",
            f"Max position: ${state.auto_limits.max_position_usdc:g}",
            f"Max daily loss: ${state.auto_limits.max_daily_loss_usdc:g}",
            f"Max token exposure: ${state.auto_limits.max_token_exposure_usdc:g}",
            f"Max concurrent: {state.auto_limits.max_concurrent_trades}",
            f"Min net profit: {state.auto_limits.min_net_profit_pct:g}%",
            f"Max slippage: {state.auto_limits.max_slippage_pct:g}%",
            f"Max quote age: {state.auto_limits.max_quote_age_ms} ms",
        ]
    )
