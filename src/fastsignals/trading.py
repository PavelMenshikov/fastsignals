from dataclasses import dataclass, replace
from enum import StrEnum


class TradingMode(StrEnum):
    OFF = "OFF"
    MANUAL = "MANUAL"
    PAPER = "PAPER"
    AUTO = "AUTO"


class TradingStatus(StrEnum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    ERROR = "ERROR"
    EMERGENCY_STOPPED = "EMERGENCY_STOPPED"


@dataclass(frozen=True)
class AutoRiskLimits:
    max_position_usdc: float = 25.0
    max_daily_loss_usdc: float = 5.0
    max_token_exposure_usdc: float = 50.0
    max_concurrent_trades: int = 2
    min_net_profit_pct: float = 0.8
    max_slippage_pct: float = 0.5
    max_quote_age_ms: int = 500


@dataclass(frozen=True)
class TradingState:
    mode: TradingMode = TradingMode.MANUAL
    status: TradingStatus = TradingStatus.STOPPED
    paper_status: TradingStatus = TradingStatus.STOPPED
    emergency_stop: bool = False
    auto_limits: AutoRiskLimits = AutoRiskLimits()


class TradingModeService:
    """Central state machine for trading mode and process status.

    The service intentionally starts in MANUAL/STOPPED after process startup. AUTO is never restored
    automatically because live execution must require explicit operator confirmation after restart.
    """

    def __init__(self, state: TradingState | None = None) -> None:
        self._state = state or TradingState()

    @property
    def state(self) -> TradingState:
        return self._state

    def set_manual(self) -> TradingState:
        status = TradingStatus.RUNNING if self._state.status == TradingStatus.RUNNING else TradingStatus.STOPPED
        self._state = replace(
            self._state,
            mode=TradingMode.MANUAL,
            status=status,
            emergency_stop=False,
        )
        return self._state

    def set_paper(self) -> TradingState:
        status = TradingStatus.RUNNING if self._state.status == TradingStatus.RUNNING else TradingStatus.STOPPED
        self._state = replace(self._state, mode=TradingMode.PAPER, status=status)
        return self._state

    def request_auto_enable(self) -> str:
        return (
            "⚠️ ENABLE AUTO TRADING\n\n"
            "The system will execute eligible arbitrage transactions automatically without manual "
            "confirmation. Confirm with /confirm_auto."
        )

    def confirm_auto(self) -> TradingState:
        self._state = replace(
            self._state,
            mode=TradingMode.AUTO,
            status=TradingStatus.STOPPED,
            emergency_stop=False,
        )
        return self._state

    def start(self) -> TradingState:
        if self._state.emergency_stop and self._state.mode == TradingMode.AUTO:
            self._state = replace(self._state, status=TradingStatus.EMERGENCY_STOPPED)
            return self._state
        if self._state.mode == TradingMode.OFF:
            self._state = replace(self._state, status=TradingStatus.STOPPED)
            return self._state
        self._state = replace(self._state, status=TradingStatus.RUNNING)
        return self._state

    def stop(self) -> TradingState:
        self._state = replace(self._state, status=TradingStatus.STOPPED)
        return self._state

    def start_paper(self) -> TradingState:
        self._state = replace(self._state, paper_status=TradingStatus.RUNNING)
        return self._state

    def stop_paper(self) -> TradingState:
        self._state = replace(self._state, paper_status=TradingStatus.STOPPED)
        return self._state

    def emergency_stop_auto(self) -> TradingState:
        self._state = replace(
            self._state,
            mode=TradingMode.AUTO,
            status=TradingStatus.EMERGENCY_STOPPED,
            emergency_stop=True,
        )
        return self._state


def startup_state() -> TradingState:
    """Safety default used after restart: live AUTO is always disabled."""
    return TradingState()
