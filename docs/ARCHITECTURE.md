# FastSignals Target Architecture

FastSignals must be treated as a trading intelligence system with a Telegram interface, not as a Telegram-first price alert bot.

```text
                    SOLANA
                       │
        ┌──────────────┴──────────────┐
        │                             │
   RPC/WebSocket                 DEX APIs
        │                             │
        └──────────────┬──────────────┘
                       ↓
              MARKET DATA ENGINE
                       ↓
             OPPORTUNITY ENGINE
                       ↓
          EXECUTABLE QUOTE ENGINE
                       ↓
                SECURITY ENGINE
                       ↓
                  RISK ENGINE
                       ↓
              ┌────────┴────────┐
              │                 │
        ML/ANOMALY          DETERMINISTIC
         SCORING              SCORING
              │                 │
              └────────┬────────┘
                       ↓
                 SIGNAL ENGINE
                       ↓
              ┌────────┴────────┐
              │                 │
            PAPER             LIVE
              │                 │
              └────────┬────────┘
                       ↓
                 TRADE JOURNAL
                       ↓
              ML TRAINING DATA
                       ↓
               MODEL IMPROVEMENT
```

The LLM/AI research layer sits outside the latency-critical path and consumes journals, metrics, failures, and aggregate statistics.

## Module boundaries

### 1. Market Data Engine

Responsibilities:

- Subscribe to Solana pool updates through RPC/WebSocket and optionally gRPC/Geyser.
- Pull executable quotes from Jupiter and direct DEX integrations.
- Use DexScreener/Birdeye only for discovery or enrichment, not as the final execution source.
- Normalize every quote with timestamp, slot, source, pool, token mint, quote size, estimated output, liquidity, price impact and quote age.
- Mark quotes as stale when quote age exceeds configured TTL.

### 2. Opportunity Engine

Responsibilities:

- Build candidates from normalized market data.
- Compare possible BUY and SELL venues for the same SPL token.
- Reject candidates that do not have both sides of the route.
- Pass candidates to the Executable Quote Engine; it must not publish signals directly.

### 3. Executable Quote Engine

Responsibilities:

- Quote the complete `USDC → TOKEN → USDC` route.
- Calculate expected token output, expected USDC output, fees, price impact, slippage, priority fee and minimum acceptable output.
- Re-quote before execution or publication if the quote is near TTL.
- Mark opportunities as `EXECUTABLE`, `NON_EXECUTABLE`, `STALE` or `NON_ATOMIC`.

### 4. Security Engine

Responsibilities:

- Keep the original checks: mint authority revoked, freeze authority revoked, LP burned/locked and top-holder concentration.
- Add production-grade checks: token age, liquidity age, creator concentration, suspicious transfers, holder growth, liquidity withdrawal velocity, sellability/honeypot, suspicious mint activity, known malicious addresses and metadata anomalies.
- Return a numeric `security_score` and machine-readable rejection reasons.

### 5. Risk Engine

Responsibilities:

- Block stale quotes, excessive price impact, insufficient liquidity, high volatility, liquidity withdrawals, bad security, low ML confidence, cooldown violations and exceeded exposure limits.
- Enforce `max_position`, `max_daily_loss`, `max_token_exposure`, `max_concurrent_trades` and per-token cooldown.
- Own kill-switch state for signals, paper and live execution.

### 6. Scoring Engines

Responsibilities:

- Deterministic scoring: spread, liquidity, route quality, execution quality, security, latency, volume and price impact.
- Anomaly scoring: Isolation Forest on market/execution features.
- Prediction scoring: supervised probabilities for successful and profitable execution once paper/live outcomes exist.
- Produce final score 0–100 without allowing ML to bypass deterministic safety checks.

### 7. Signal Engine

Responsibilities:

- Publish only opportunities that have an executable quote, pass security/risk gates and exceed configured net profit thresholds.
- Persist full signal payload and lifecycle status.
- Track opportunity state after 100ms, 500ms, 1s, 5s, 30s and 1min.

### 8. Paper Trading Engine

Responsibilities:

- Use the same execution quotes and risk checks as live mode.
- Maintain virtual USDC and token balances per user/account.
- Simulate execution latency, slippage, price impact, opportunity disappearance, failed execution and fees.
- Record expected vs actual virtual P&L.

### 9. Live Execution Engine

Responsibilities:

- Non-custodial mode: prepare a transaction/route for wallet confirmation.
- Automated opt-in mode: use delegated/session signing with explicit user consent and risk limits; do not store private keys in the Telegram bot.
- Prefer atomic `USDC → TOKEN → USDC` Solana transactions when technically possible.
- Revalidate executable quote immediately before broadcast.
- Reject execution if minimum net profit cannot be guaranteed.

### 10. Telegram UI

Responsibilities:

- Display signals, paper results, dashboard views and admin/operator controls.
- It must not be the execution engine.
- Telegram delivery latency is measured but must not be in the live automated critical path.

### 11. Journaling, Backtesting and ML Dataset

Responsibilities:

- Persist every signal, quote, lifecycle transition, paper trade, live trade, re-quote, failure reason and latency segment.
- Provide historical backtests over 1h, 6h, 24h, 7d and 30d windows.
- Feed paper/live outcomes into model training datasets with model versioning and validation stages.

## Target execution path

### Signal/Paper path

```text
market event
  → normalized quote
  → candidate
  → executable quote
  → security/risk
  → score
  → signal journal
  → Telegram and/or paper execution
```

### Live automated path

```text
market event
  → normalized quote
  → candidate
  → executable quote
  → security/risk
  → score
  → transaction build
  → re-quote
  → sign
  → broadcast
  → outcome journal
```

Telegram is not required in the live automated path.

## Implementation phases

1. **Specification and schemas**: finalize event schemas, quote schemas, signal lifecycle, journal schema and risk settings.
2. **Market data and executable quotes**: replace price-only scanner with executable Jupiter/direct DEX quotes and stale-quote handling.
3. **Paper trading and journaling**: implement virtual balances and outcome collection on real live market data.
4. **Risk/security hardening**: production-grade security score, exposure limits, kill switches and MEV/race protections.
5. **Backtesting and dashboards**: user and admin dashboards over journal data.
6. **ML/anomaly layer**: Isolation Forest first, supervised model only after enough paper/live outcomes exist.
7. **Live execution**: non-custodial transaction preparation first; automated delegated/session signing only as explicit opt-in.
