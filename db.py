import aiosqlite
import logging
from config import DATABASE

logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                user_id INTEGER PRIMARY KEY,
                private_key TEXT NOT NULL,
                address TEXT NOT NULL UNIQUE,
                public_key TEXT NOT NULL UNIQUE
            );
        """)
        await db.commit()
        logger.info("Database initialized")

async def insert_wallet(user_id: int, mnemonic: str, address: str, pubkey: str):
    async with aiosqlite.connect(DATABASE) as db:
        try:
            await db.execute(
                "INSERT INTO wallets VALUES (?, ?, ?, ?)",
                (user_id, mnemonic, address, pubkey)
            )
            await db.commit()
        except aiosqlite.IntegrityError as e:
            logger.error(f"Wallet exists: {e}")

async def get_wallet(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
            "SELECT private_key, address, public_key FROM wallets WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            return await cursor.fetchone()
