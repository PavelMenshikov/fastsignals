import aiosqlite


class Storage:
    def __init__(self, path: str) -> None:
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    dedupe_key TEXT PRIMARY KEY,
                    token_mint TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    chat_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def get_float(self, key: str, default: float) -> float:
        async with aiosqlite.connect(self.path) as db:
            row = await (await db.execute("SELECT value FROM settings WHERE key = ?", (key,))).fetchone()
        return float(row[0]) if row else default

    async def set_value(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            await db.commit()

    async def add_subscriber(self, chat_id: int, user_id: int | None, is_admin: bool) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO subscribers(chat_id, user_id, is_admin) VALUES (?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET user_id=excluded.user_id, is_admin=excluded.is_admin
                """,
                (chat_id, user_id, int(is_admin)),
            )
            await db.commit()

    async def remove_subscriber(self, chat_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM subscribers WHERE chat_id = ?", (chat_id,))
            await db.commit()

    async def subscriber_chat_ids(self, admin_ids: set[int]) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            rows = await (await db.execute("SELECT chat_id FROM subscribers")).fetchall()
        chat_ids = {int(row[0]) for row in rows}
        chat_ids.update(admin_ids)
        return sorted(chat_ids)

    async def remember_signal(self, dedupe_key: str, token_mint: str, payload: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    "INSERT INTO signals(dedupe_key, token_mint, payload) VALUES (?, ?, ?)",
                    (dedupe_key, token_mint, payload),
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False
