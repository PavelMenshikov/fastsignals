import asyncio
import json
from collections import defaultdict

import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from .calculator import calculate_net_spread
from .config import Settings, get_settings
from .market import MarketDataClient
from .security import SecurityClient
from .storage import Storage
from .telegram_ui import signal_keyboard, signal_text

router = Router()
monitoring_task: asyncio.Task | None = None
monitoring_enabled = False


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
            "Команды: /settings, /pause, /resume, /set_order, /set_spread, "
            "/set_liquidity, /set_volume, /unsubscribe"
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


@router.message(Command("pause"))
async def pause(message: Message) -> None:
    global monitoring_enabled
    if is_admin(message, get_settings()):
        monitoring_enabled = False
        await message.answer("Мониторинг на паузе")


@router.message(Command("resume"))
async def resume(message: Message) -> None:
    global monitoring_enabled
    if is_admin(message, get_settings()):
        monitoring_enabled = True
        await message.answer("Мониторинг включен")


async def monitor(settings: Settings, bot: Bot, storage: Storage) -> None:
    market = MarketDataClient(str(settings.dexscreener_base_url))
    security_client = SecurityClient(str(settings.rugcheck_base_url))
    async with aiohttp.ClientSession() as session:
        while True:
            if not monitoring_enabled:
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
                    low, high, security, order, settings.dex_fee_pct, settings.slippage_pct, settings.priority_fee_usdc
                )
                if not signal or signal.net_spread_pct < min_spread:
                    continue
                payload = json.dumps(signal.__dict__, default=str, ensure_ascii=False)
                if not await storage.remember_signal(signal.dedupe_key, signal.token_mint, payload):
                    continue
                for chat_id in await storage.subscriber_chat_ids(settings.admin_id_set):
                    await bot.send_message(
                        chat_id,
                        signal_text(signal),
                        reply_markup=signal_keyboard(signal, settings.slippage_pct),
                        parse_mode="Markdown",
                    )
            await asyncio.sleep(settings.poll_interval_seconds)


async def main() -> None:
    global monitoring_task, monitoring_enabled
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    storage = Storage(settings.database_url)
    await storage.init()
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    monitoring_enabled = True
    monitoring_task = asyncio.create_task(monitor(settings, bot, storage))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
