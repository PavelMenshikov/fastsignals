from dataclasses import dataclass

from .execution_policy import ExecutionAction, ExecutionDecision
from .models import SpreadSignal


@dataclass
class PaperAccount:
    virtual_usdc_balance: float = 1000.0
    virtual_pnl_usdc: float = 0.0
    trades: int = 0
    wins: int = 0

    @property
    def equity_usdc(self) -> float:
        return self.virtual_usdc_balance

    @property
    def win_rate_pct(self) -> float:
        return (self.wins / self.trades * 100) if self.trades else 0.0


@dataclass(frozen=True)
class PaperExecutionResult:
    executed: bool
    expected_pnl_usdc: float
    actual_pnl_usdc: float
    reason: str


class PaperExecutionAdapter:
    """Virtual execution adapter; it never sends blockchain transactions."""

    blockchain_transactions_sent = 0

    def execute(self, account: PaperAccount, signal: SpreadSignal, decision: ExecutionDecision) -> PaperExecutionResult:
        if decision.action != ExecutionAction.SIMULATE_PAPER or not decision.accepted:
            return PaperExecutionResult(False, 0.0, 0.0, decision.reason)

        pnl = signal.estimated_profit_usdc
        account.virtual_usdc_balance += pnl
        account.virtual_pnl_usdc += pnl
        account.trades += 1
        if pnl > 0:
            account.wins += 1
        return PaperExecutionResult(True, pnl, pnl, "paper_executed")
