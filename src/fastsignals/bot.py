import asyncio
import json
from collections import defaultdict

import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from .calculator import calculate_net_spread
from .config import Settings, get_settings
from .dashboard import dashboard_text
from .execution_policy import ExecutionPolicy, OpportunityChecks
from .market import MarketDataClient
from .paper import PaperAccount, PaperExecutionAdapter
from .security import SecurityClient
from .storage import Storage
from .telegram_ui import signal_keyboard, signal_text
from .trading import TradingMode, TradingModeService, TradingStatus

router = Router()
monitoring_task: asyncio.Task | None = None
mode_service = TradingModeService()
paper_account = PaperAccount()
paper_adapter = PaperExecutionAdapter()
execution_policy = ExecutionPolicy()


def is_admin(message: Message, settings: Settings) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_id_set)


@router.message(Command("start"))
async def start(message: Message) -> None:
    settings = get_settings()
    storage = Storage(settings.database_url)
    await storage.init()
    user_id = message.from_user.id if message.from_user else None
    admin = bool(user_id and user_id in settings.admin_id_set)
    await storage.add_subscriber(message.chat.id, user_id, is_admin=admin)
    if admin:
        await message.answer(
            "FastSignals готов. Вы администратор. "
            "Команды: /dashboard, /mode_manual, /mode_paper, /enable_auto, /confirm_auto, "
            "/start_engine, /stop_engine, /start_paper, /stop_paper, /emergency_stop"
        )
    else:
        await message.answer(
            "Вы подписаны на сигналы FastSignals. "
            "Админ-команды доступны только владельцам из ADMIN_IDS. Для отписки: /unsubscribe"
        )


@router.message(Command("unsubscribe"))
async def unsubscribe(message: Message) -> None:
    settings = get_settings()
    storage = Storage(settings.database_url)
    await storage.remove_subscriber(message.chat.id)
    await message.answer("Вы отписаны от сигналов FastSignals")


@router.message(Command("dashboard"))
async def dashboard_cmd(message: Message) -> None:
    if not is_admin(message, get_settings()):
        await message.answer("Недостаточно прав")
        return
    await message.answer(dashboard_text(mode_service.state, paper_account))


@router.message(Command("settings"))
async def settings_cmd(message: Message) -> None:
    settings = get_settings()
    if not is_admin(message, settings):
        await message.answer("Недостаточно прав")
        return
    storage = Storage(settings.database_url)
    order = await storage.get_float("order_usdc", settings.default_order_usdc)
    spread = await storage.get_float("min_net_spread_pct", settings.default_min_net_spread_pct)
    liquidity = await storage.get_float("min_liquidity_usd", settings.default_min_liquidity_usd)
    volume = await storage.get_float("min_volume_24h_usd", settings.default_min_volume_24h_usd)
    await message.answer(
        f"Order: ${order:g}\n"
        f"Min net spread: {spread:g}%\n"
        f"Min liquidity: ${liquidity:g}\n"
        f"Min 24h volume: ${volume:g}"
    )


async def set_float(message: Message, key: str) -> None:
    settings = get_settings()
    if not is_admin(message, settings):
        await message.answer("Недостаточно прав")
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Передайте числовое значение после команды")
        return
    value = float(parts[1].replace(",", "."))
    await Storage(settings.database_url).set_value(key, str(value))
    await message.answer(f"Сохранено: {key} = {value:g}")


@router.message(Command("set_order"))
async def set_order(message: Message) -> None:
    await set_float(message, "order_usdc")


@router.message(Command("set_spread"))
async def set_spread(message: Message) -> None:
    await set_float(message, "min_net_spread_pct")


@router.message(Command("set_liquidity"))
async def set_liquidity(message: Message) -> None:
    await set_float(message, "min_liquidity_usd")


@router.message(Command("set_volume"))
async def set_volume(message: Message) -> None:
    await set_float(message, "min_volume_24h_usd")


@router.message(Command("mode_manual"))
async def mode_manual(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.set_manual()
        await message.answer(dashboard_text(mode_service.state, paper_account))


@router.message(Command("mode_paper"))
async def mode_paper(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.set_paper()
        await message.answer(dashboard_text(mode_service.state, paper_account))


@router.message(Command("enable_auto"))
async def enable_auto(message: Message) -> None:
    if is_admin(message, get_settings()):
        await message.answer(mode_service.request_auto_enable())


@router.message(Command("confirm_auto"))
async def confirm_auto(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.confirm_auto()
        await message.answer("AUTO ENABLED\n" + dashboard_text(mode_service.state, paper_account))


@router.message(Command("start_engine", "resume"))
async def start_engine(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.start()
        await message.answer(dashboard_text(mode_service.state, paper_account))


@router.message(Command("stop_engine", "pause"))
async def stop_engine(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.stop()
        await message.answer(dashboard_text(mode_service.state, paper_account))


@router.message(Command("start_paper"))
async def start_paper(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.start_paper()
        await message.answer(dashboard_text(mode_service.state, paper_account))


@router.message(Command("stop_paper"))
async def stop_paper(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.stop_paper()
        await message.answer(dashboard_text(mode_service.state, paper_account))


@router.message(Command("emergency_stop"))
async def emergency_stop(message: Message) -> None:
    if is_admin(message, get_settings()):
        mode_service.emergency_stop_auto()
        await message.answer("🛑 EMERGENCY STOPPED\n" + dashboard_text(mode_service.state, paper_account))


def should_scan_market() -> bool:
    return mode_service.state.status == TradingStatus.RUNNING or mode_service.state.paper_status == TradingStatus.RUNNING


async def monitor(settings: Settings, bot: Bot, storage: Storage) -> None:
    market = MarketDataClient(str(settings.dexscreener_base_url))
    security_client = SecurityClient(str(settings.rugcheck_base_url))
    async with aiohttp.ClientSession() as session:
        while True:
            if not should_scan_market():
                await asyncio.sleep(settings.poll_interval_seconds)
                continue
            order = await storage.get_float("order_usdc", settings.default_order_usdc)
            min_spread = await storage.get_float("min_net_spread_pct", settings.default_min_net_spread_pct)
            min_liquidity = await storage.get_float("min_liquidity_usd", settings.default_min_liquidity_usd)
            min_volume = await storage.get_float("min_volume_24h_usd", settings.default_min_volume_24h_usd)
            quotes = [
                q
                for q in await market.fetch_quotes(session)
                if q.liquidity_usd >= min_liquidity and q.volume_24h_usd >= min_volume
            ]
            by_token: dict[str, list] = defaultdict(list)
            for quote in quotes:
                by_token[quote.token_mint].append(quote)
            for token_quotes in by_token.values():
                if len(token_quotes) < 2:
                    continue
                low = min(token_quotes, key=lambda item: item.price_usdc)
                high = max(token_quotes, key=lambda item: item.price_usdc)
                security = await security_client.check(session, low.token_mint)
                if not security.is_safe:
                    continue
                signal = calculate_net_spread(
                    low,
                    high,
                    security,
                    order,
                    settings.dex_fee_pct,
                    settings.slippage_pct,
                    settings.priority_fee_usdc,
                )
                if not signal or signal.net_spread_pct < min_spread:
                    continue
                payload = json.dumps(signal.__dict__, default=str, ensure_ascii=False)
                if not await storage.remember_signal(signal.dedupe_key, signal.token_mint, payload):
                    continue

                state_snapshot = mode_service.state
                decision = execution_policy.decide(signal, state_snapshot, OpportunityChecks())
                if decision.action.value == "SIMULATE_PAPER":
                    paper_adapter.execute(paper_account, signal, decision)
                if state_snapshot.paper_status == TradingStatus.RUNNING and state_snapshot.mode != TradingMode.PAPER:
                    paper_state = TradingModeService(state_snapshot).set_paper()
                    paper_decision = execution_policy.decide(signal, paper_state, OpportunityChecks())
                    paper_adapter.execute(paper_account, signal, paper_decision)

                for chat_id in await storage.subscriber_chat_ids(settings.admin_id_set):
                    await bot.send_message(
                        chat_id,
                        signal_text(signal, decision),
                        reply_markup=signal_keyboard(signal, settings.slippage_pct, decision),
                        parse_mode="Markdown",
                    )
            await asyncio.sleep(settings.poll_interval_seconds)


async def main() -> None:
    global monitoring_task
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    storage = Storage(settings.database_url)
    await storage.init()
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    mode_service.set_manual()
    monitoring_task = asyncio.create_task(monitor(settings, bot, storage))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
