from fastsignals.trading import TradingMode, TradingModeService, TradingStatus, startup_state


def test_startup_defaults_are_safe() -> None:
    state = startup_state()

    assert state.mode == TradingMode.MANUAL
    assert state.status == TradingStatus.STOPPED
    assert state.paper_status == TradingStatus.STOPPED
    assert not state.emergency_stop


def test_auto_requires_confirmation_and_starts_stopped() -> None:
    service = TradingModeService()

    assert "ENABLE AUTO TRADING" in service.request_auto_enable()
    state = service.confirm_auto()

    assert state.mode == TradingMode.AUTO
    assert state.status == TradingStatus.STOPPED


def test_emergency_stop_blocks_auto_restart_until_reenabled() -> None:
    service = TradingModeService()
    service.confirm_auto()
    service.start()
    stopped = service.emergency_stop_auto()

    assert stopped.mode == TradingMode.AUTO
    assert stopped.status == TradingStatus.EMERGENCY_STOPPED
    assert stopped.emergency_stop

    still_stopped = service.start()
    assert still_stopped.status == TradingStatus.EMERGENCY_STOPPED


def test_auto_to_manual_keeps_running_for_new_opportunities_only() -> None:
    service = TradingModeService()
    service.confirm_auto()
    service.start()

    state = service.set_manual()

    assert state.mode == TradingMode.MANUAL
    assert state.status == TradingStatus.RUNNING
