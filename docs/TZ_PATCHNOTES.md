# Патчноуты к ТЗ FastSignals

Этот документ фиксирует изменения к исходному ТЗ, чтобы FastSignals нельзя было принять как простой Telegram-бот, сравнивающий `priceUsd` из DexScreener. Цель проекта меняется на торговую систему, которая обнаруживает, проверяет, симулирует и при явном включении исполняет краткоживущие арбитражные возможности Solana.

## 0. Новая философия проекта

**Цель проекта — не разработка Telegram-бота, отображающего ценовые расхождения, а создание системы обнаружения, оценки, симуляции и, при включении пользователем соответствующего режима, исполнения арбитражных возможностей в сети Solana.**

Telegram является пользовательским интерфейсом, а не ядром торговой системы. Любая возможность должна оцениваться на основании исполнимых котировок и полной стоимости сделки. Теоретический spread без подтверждения возможности исполнения не считается торговым сигналом.

Система должна иметь обязательный Paper Trading режим, позволяющий проверять стратегию на реальном потоке данных без риска потери средств. ML/AI является дополнительным слоем оценки вероятности успешного исполнения и исследования рынка, но не заменяет детерминированную проверку экономики сделки.

## 1. Определение торгового сигнала

Торговым сигналом считается не наличие теоретического ценового спреда, а наличие **реально исполнимой арбитражной возможности**, подтверждённой актуальными котировками маршрута покупки и продажи, с учётом:

- price impact;
- фактической ликвидности;
- slippage;
- DEX fees;
- network fees;
- priority fees;
- latency;
- предполагаемой стоимости исполнения.

Простое сравнение `priceUsd` разных источников не является достаточным основанием для формирования торгового сигнала.

## 2. Market Data Engine

Добавить отдельный **Market Data Engine**. Он должен поддерживать:

- Raydium AMM;
- Raydium CLMM;
- Orca Whirlpools;
- Meteora;
- Jupiter как источник агрегированных executable quotes;
- Solana RPC;
- WebSocket;
- при возможности gRPC/Geyser.

DexScreener/Birdeye могут использоваться как дополнительные источники discovery, но не как единственный источник истины для исполнения.

Каждая котировка должна иметь:

```text
timestamp
source
slot
pool
token_mint
price
liquidity
quote_size
estimated_output
price_impact
quote_age
```

Бот должен определять stale quote и не использовать её для сигнала.

## 3. Executable Arbitrage Engine

Добавить **Executable Arbitrage Engine**. Для каждого кандидата система должна рассчитывать полный маршрут:

```text
USDC
 ↓
BUY route
 ↓
TOKEN
 ↓
SELL route
 ↓
USDC
```

Расчёт должен включать:

```text
input_amount
expected_token_output
expected_usdc_output
dex_fees
network_fees
priority_fee
price_impact
slippage
route_fees
expected_net_profit
expected_net_spread
```

Если теоретический spread составляет 3%, но после реального route quote остаётся 0.2%, сигнала быть не должно.

## 4. Dynamic Order Sizing

Размер `$25` не должен быть единственным расчётом. Система должна рассчитывать opportunity для нескольких размеров:

```text
$10
$25
$50
$100
$250
$500
$1000
```

Система должна находить **Optimal Trade Size** с максимальным ожидаемым net P&L с учётом падения доходности от price impact.

## 5. Latency Engine

Требование `<1–1.5 сек` должно быть измеряемым. Система должна записывать:

```text
T0 = событие/обновление pool
T1 = получение market data
T2 = candidate detection
T3 = security check
T4 = executable quote
T5 = signal generation
T6 = Telegram delivery
```

Хранить минимум:

```text
total_latency_ms
market_latency_ms
security_latency_ms
quote_latency_ms
telegram_latency_ms
```

Dashboard должен показывать P50, P95, P99 и max latency.

## 6. Signal Scoring Engine

Каждый кандидат должен получать **Signal Score 0–100**. Scoring состоит из двух частей:

### Deterministic Score

Проверяет spread, liquidity, price impact, execution, security, latency, volume и route quality.

### ML Score

Оценивает вероятность, что opportunity сохранится достаточно долго и будет успешно исполнена.

## 7. Anomaly Detection Engine

Добавить ML-модуль **Anomaly Detection Engine**. Первая модель — **Isolation Forest**.

Минимальные фичи:

```text
spread
spread_velocity
price_velocity
volume_velocity
liquidity
liquidity_change
price_deviation
pool_imbalance
trade_frequency
quote_age
price_impact
DEX_count
```

Модель используется для обнаружения необычных расхождений, резких изменений ликвидности, abnormal market behaviour и дополнительного ranking кандидатов. Isolation Forest не должен самостоятельно инициировать live trade.

## 8. ML Prediction Engine

После накопления истории добавить supervised model, прогнозирующую:

```text
P(successful_execution)
P(profitable_execution)
```

Модель должна обучаться на реальных результатах paper/live execution, а не на искусственно размеченных данных.

## 9. AI/LLM Research Layer

Добавить отдельный **AI Research Layer**. LLM не должен находиться в latency-critical signal path.

LLM используется для анализа истории сигналов, причин failed trades, генерации гипотез, анализа аномалий, объяснения сигналов человеку, помощи в создании новых features и анализа эффективности стратегий. LLM не должен иметь права самостоятельно отправлять live transaction.

## 10. Paper Trading

Добавить обязательный режим **PAPER TRADING**. Пользователь получает виртуальный баланс, например `$1,000 Virtual USDC`, и виртуальные токены.

Paper engine должен моделировать BUY, SELL, fees, slippage, price impact, priority fee, latency, failed execution, исчезновение opportunity и изменение цены между quote и execution.

Нельзя считать `profit = spread × order`. Paper trade должен использовать тот же Execution Engine, что и live trading.

## 11. Backtesting

Добавить исторический режим **BACKTEST**. Пользователь выбирает period, capital и order size, а система возвращает signals, trades, win rate, average profit, total P&L, max drawdown, Sharpe-like metrics, failed executions и average latency.

## 12. Live / Paper / Signal режимы

В интерфейсе должны быть три независимых режима:

- 👀 **SIGNAL** — только обнаружение возможностей;
- 🧪 **PAPER** — реальные market data → виртуальные сделки;
- 💰 **LIVE** — реальные сделки.

Market Data, Opportunity Engine, Risk Engine и Execution Engine должны быть общими, а не тремя разными реализациями.

## 13. Virtual Dashboard

Добавить пользовательский dashboard: Balance, Equity, P&L, Win rate, Trades, Open positions, Closed positions, Best trade, Worst trade, Average execution, Average latency. Графики: Equity curve, P&L, Daily P&L, Signal quality, Execution success.

## 14. Signal Journal

Каждый сигнал должен сохраняться полностью: SIGNAL ID, timestamp, token, mint, buy/sell DEX, market price, executable buy/sell, gross/net spread, liquidity, volume, price impact, slippage, security score, ML score, final score, quote age, detection latency и execution latency.

После публикации система должна записывать, что произошло через 100ms, 500ms, 1s, 5s, 30s и 1min. Эти данные являются датасетом для ML.

## 15. Signal Lifecycle

У сигнала должен быть lifecycle:

```text
DETECTED
   ↓
VALIDATING
   ↓
EXECUTABLE
   ↓
PUBLISHED
   ↓
PAPER_EXECUTED
   ↓
EXPIRED / SUCCESS / FAILED
```

## 16. Risk Engine

Добавить отдельный Risk Engine. Он блокирует сигнал при недостаточной ликвидности, слишком большом price impact, stale quote, резком изменении цены, падении liquidity, подозрительной активности, плохом ML confidence или высокой вероятности failed execution.

Настройки риска: `max_position`, `max_daily_loss`, `max_token_exposure`, `max_concurrent_trades`, `cooldown`.

## 17. Production-grade Anti-Scam

Текущие проверки оставить, но добавить token age, liquidity age, creator concentration, suspicious transfers, holder growth, liquidity withdrawal velocity, honeypot/sellability checks, suspicious mint activity, known malicious addresses и metadata anomalies.

Результат должен быть **Security Score**, например `Security: 96/100`, а не только `safe=true`.

## 18. MEV / Race Protection

Система должна учитывать, что opportunity может быть уже захвачена другим searcher, quote может устареть, несколько ботов могут видеть один spread одновременно, а цена может измениться между BUY и SELL.

Нужны `opportunity_age`, `quote_age`, `execution_probability` и проверка opportunity непосредственно перед execution.

## 19. Telegram не является Execution Engine

Telegram должен быть интерфейсом:

```text
Solana → Market Data → Arbitrage Engine → Risk Engine → ML Scoring → Signal → Telegram UI
```

Telegram latency не должен определять возможность торговли.

## 20. 1-Click / Execution режимы

Для SIGNAL/PAPER допустимо открывать Jupiter или показывать route. Для LIVE нужно поддержать две архитектуры:

- **Non-custodial**: пользователь подтверждает transaction через wallet;
- **Automated**: отдельный opt-in режим с delegated/session signing, без хранения приватного ключа пользователя в Telegram-боте.

Автоматический режим должен включаться отдельно и иметь лимиты риска.

## 21. Dashboard администратора

Добавить dashboard администратора: System status, RPC latency, Data latency, Quote latency, Telegram latency, Signals/min, Candidates/min, Valid opportunities, Rejected opportunities, Paper P&L, Live P&L, Win rate, Execution success, ML confidence, Model version, Errors.

## 22. ML Model Management

Система должна сохранять `model_version`, `training_period`, `features_version`, `dataset_version`, `metrics` и не позволять новой модели автоматически становиться production-моделью.

Этапы модели: TRAIN, VALIDATE, BACKTEST, PAPER, PRODUCTION.

## 23. Kill Switch

Добавить 🛑 **EMERGENCY STOP**, который мгновенно отключает live execution, paper execution и signal publication по отдельности.

Пример состояния:

```text
Signals: ON
Paper: ON
Live: OFF
```

## 24. Acceptance Criteria

Проект нельзя считать принятым, если система показывает spread, но не может подтвердить executable quote.

Нужно доказать на тестовом периоде:

- detection latency;
- quote freshness;
- execution simulation;
- paper trading;
- отсутствие duplicate signals;
- корректность P&L;
- корректность fee calculation;
- корректность security checks.

Paper trading должен работать минимум на реальном live market data:

```text
REAL SOLANA DATA
       ↓
REAL QUOTES
       ↓
REAL SIGNALS
       ↓
VIRTUAL MONEY
       ↓
VIRTUAL EXECUTION
       ↓
REAL PERFORMANCE STATISTICS
```

## 25. Atomic Arbitrage Execution

Система должна поддерживать не только обнаружение ценового расхождения, но и построение арбитражной сделки как последовательности `BUY → SELL`.

Для каждого сигнала система обязана определить DEX покупки, DEX продажи, торговую пару, размер входа, ожидаемый output, минимально допустимый output, комиссии, priority fee, price impact, slippage, ожидаемый net P&L и срок актуальности котировки.

Для LIVE режима система должна стремиться выполнять BUY и SELL в рамках **одной атомарной Solana transaction**, когда это технически возможно. Транзакция не должна отправляться, если актуальная executable quote больше не обеспечивает заданный минимальный net profit.

Если атомарное исполнение невозможно, система должна помечать opportunity как `NON_ATOMIC` и применять значительно более строгие ограничения риска.

## 26. Atomicity

Приоритетным является атомарное исполнение `USDC → TOKEN → USDC` в рамках одной транзакции. Система не должна использовать последовательность `BUY → ожидание подтверждения → SELL` как основной механизм арбитража.

## 27. Sell Route

Каждый arbitrage signal обязан содержать не только BUY route, но и SELL route. Система не имеет права публиковать opportunity только на основании выгодной цены покупки. Перед публикацией сигнала SELL route должен быть рассчитан и подтверждён актуальной executable quote.

## 28. Execution Revalidation

Непосредственно перед отправкой система должна выполнить re-quote:

```text
SIGNAL → re-quote → profit still positive? → YES execute / NO cancel
```

## 29. Expiration

У opportunity должен быть TTL: `signal_created_at`, `quote_timestamp`, `expires_at`. Если opportunity старше TTL, она получает статус `EXPIRED` и не исполняется.

## 30. Execution Outcome

После отправки нужно отслеживать `submitted`, `confirmed`, `failed`, `reverted`, `profitable`, `unprofitable` и сохранять expected P&L, actual P&L, expected execution price, actual execution price, latency и failure reason. Эти данные становятся датасетом для ML.
