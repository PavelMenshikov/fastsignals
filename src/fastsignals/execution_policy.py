from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from .models import SpreadSignal
from .trading import TradingMode, TradingState, TradingStatus


class ExecutionAction(StrEnum):
    REJECT = "REJECT"
    PREPARE_MANUAL = "PREPARE_MANUAL"
    SIMULATE_PAPER = "SIMULATE_PAPER"
    EXECUTE_AUTO = "EXECUTE_AUTO"


@dataclass(frozen=True)
class OpportunityChecks:
    executable: bool = True
    security_ok: bool = True
    risk_ok: bool = True
    quote_is_stale: bool = False
    opportunity_expired: bool = False
    position_limit_exceeded: bool = False
    concurrent_limit_exceeded: bool = False


@dataclass(frozen=True)
class ExecutionDecision:
    action: ExecutionAction
    accepted: bool
    mode_snapshot: TradingMode
    status_snapshot: TradingStatus
    reason: str
    signal_id: str
    timestamp: datetime


class ExecutionPolicy:
    """Single place that maps a validated opportunity to manual, paper or live behavior."""

    def decide(self, signal: SpreadSignal, state: TradingState, checks: OpportunityChecks) -> ExecutionDecision:
        reason = self._rejection_reason(signal, state, checks)
        if reason:
            return self._decision(ExecutionAction.REJECT, False, state, signal, reason)

        if state.mode == TradingMode.MANUAL:
            return self._decision(ExecutionAction.PREPARE_MANUAL, True, state, signal, "manual_user_action_required")
        if state.mode == TradingMode.PAPER:
            return self._decision(ExecutionAction.SIMULATE_PAPER, True, state, signal, "paper_simulation_only")
        if state.mode == TradingMode.AUTO:
            return self._decision(ExecutionAction.EXECUTE_AUTO, True, state, signal, "auto_execution_allowed")
        return self._decision(ExecutionAction.REJECT, False, state, signal, "mode_off")

    def _rejection_reason(
        self, signal: SpreadSignal, state: TradingState, checks: OpportunityChecks
    ) -> str | None:
        if state.status != TradingStatus.RUNNING:
            return "trading_engine_not_running"
        if state.emergency_stop and state.mode == TradingMode.AUTO:
            return "auto_emergency_stopped"
        if not checks.executable:
            return "not_executable"
        if not checks.security_ok or not signal.security.is_safe:
            return "security_rejected"
        if not checks.risk_ok:
            return "risk_rejected"
        if checks.quote_is_stale:
            return "quote_is_stale"
        if checks.opportunity_expired:
            return "opportunity_expired"
        if checks.position_limit_exceeded:
            return "position_limit_exceeded"
        if checks.concurrent_limit_exceeded:
            return "concurrent_limit_exceeded"
        if state.mode == TradingMode.AUTO:
            if signal.order_usdc > state.auto_limits.max_position_usdc:
                return "auto_max_position_exceeded"
            if signal.net_spread_pct < state.auto_limits.min_net_profit_pct:
                return "auto_min_net_profit_not_met"
        return None

    def _decision(
        self,
        action: ExecutionAction,
        accepted: bool,
        state: TradingState,
        signal: SpreadSignal,
        reason: str,
    ) -> ExecutionDecision:
        return ExecutionDecision(
            action=action,
            accepted=accepted,
            mode_snapshot=state.mode,
            status_snapshot=state.status,
            reason=reason,
            signal_id=signal.dedupe_key,
            timestamp=datetime.now(UTC),
        )
