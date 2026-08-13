from fastsignals.execution_policy import ExecutionAction, ExecutionPolicy, OpportunityChecks
from fastsignals.models import SecurityReport, SpreadSignal
from fastsignals.paper import PaperAccount, PaperExecutionAdapter
from fastsignals.trading import AutoRiskLimits, TradingMode, TradingState, TradingStatus


def signal(net: float = 1.0, order: float = 25.0) -> SpreadSignal:
    return SpreadSignal(
        token_mint="Mint111",
        token_symbol="TKN",
        buy_dex="raydium",
        sell_dex="orca",
        gross_spread_pct=2.0,
        net_spread_pct=net,
        estimated_profit_usdc=order * net / 100,
        order_usdc=order,
        security=SecurityReport(True, True, 100, 10),
    )


def test_manual_prepares_transaction_and_does_not_auto_execute() -> None:
    decision = ExecutionPolicy().decide(
        signal(), TradingState(mode=TradingMode.MANUAL, status=TradingStatus.RUNNING), OpportunityChecks()
    )

    assert decision.action == ExecutionAction.PREPARE_MANUAL
    assert decision.mode_snapshot == TradingMode.MANUAL


def test_paper_simulates_and_never_sends_blockchain_transaction() -> None:
    decision = ExecutionPolicy().decide(
        signal(), TradingState(mode=TradingMode.PAPER, status=TradingStatus.RUNNING), OpportunityChecks()
    )
    account = PaperAccount()
    result = PaperExecutionAdapter().execute(account, signal(), decision)

    assert decision.action == ExecutionAction.SIMULATE_PAPER
    assert result.executed
    assert account.trades == 1
    assert PaperExecutionAdapter.blockchain_transactions_sent == 0


def test_auto_executes_only_when_all_safety_gates_pass() -> None:
    decision = ExecutionPolicy().decide(
        signal(), TradingState(mode=TradingMode.AUTO, status=TradingStatus.RUNNING), OpportunityChecks()
    )

    assert decision.action == ExecutionAction.EXECUTE_AUTO
    assert decision.mode_snapshot == TradingMode.AUTO


def test_stopped_engine_rejects_every_mode() -> None:
    decision = ExecutionPolicy().decide(
        signal(), TradingState(mode=TradingMode.AUTO, status=TradingStatus.STOPPED), OpportunityChecks()
    )

    assert decision.action == ExecutionAction.REJECT
    assert decision.reason == "trading_engine_not_running"


def test_auto_risk_limits_block_low_profit_and_large_position() -> None:
    state = TradingState(
        mode=TradingMode.AUTO,
        status=TradingStatus.RUNNING,
        auto_limits=AutoRiskLimits(max_position_usdc=25, min_net_profit_pct=0.8),
    )

    low_profit = ExecutionPolicy().decide(signal(net=0.3), state, OpportunityChecks())
    large_position = ExecutionPolicy().decide(signal(net=1.0, order=50), state, OpportunityChecks())

    assert low_profit.reason == "auto_min_net_profit_not_met"
    assert large_position.reason == "auto_max_position_exceeded"


def test_policy_snapshot_survives_later_mode_change() -> None:
    state = TradingState(mode=TradingMode.AUTO, status=TradingStatus.RUNNING)
    decision = ExecutionPolicy().decide(signal(), state, OpportunityChecks())
    changed_state = TradingState(mode=TradingMode.MANUAL, status=TradingStatus.RUNNING)

    assert changed_state.mode == TradingMode.MANUAL
    assert decision.mode_snapshot == TradingMode.AUTO
    assert decision.action == ExecutionAction.EXECUTE_AUTO
