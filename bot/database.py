"""
Async SQLite Database Manager
Handles all DB operations with retry logic for locked/busy database.
Optimized for 1.78B row dataset with deep-link search capability.
"""

import asyncio
import logging
import sqlite3
from functools import wraps
from typing import Any

import aiosqlite

from bot.config import DB_PATH, DB_RETRY_ATTEMPTS, DB_RETRY_DELAY, MAX_RESULTS

logger = logging.getLogger(__name__)


def retry_on_lock(func):
    """Decorator: retry query on sqlite3.OperationalError (database locked)."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        delay = DB_RETRY_DELAY
        for attempt in range(1, DB_RETRY_ATTEMPTS + 1):
            try:
                return await func(*args, **kwargs)
            except (sqlite3.OperationalError, aiosqlite.OperationalError) as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    logger.warning(
                        f"DB locked (attempt {attempt}/{DB_RETRY_ATTEMPTS}), "
                        f"retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise
        return await func(*args, **kwargs)
    return wrapper


class DatabaseManager:
    """Async SQLite connection manager for the users database."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self):
        """Open a persistent connection with optimized settings."""
        logger.info(f"Connecting to database: {self.db_path}")
        self._conn = await aiosqlite.connect(self.db_path, timeout=30)
        self._conn.row_factory = aiosqlite.Row

        # ── Performance optimizations for read-heavy 1.78B row DB ──
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA busy_timeout=10000;")
        await self._conn.execute("PRAGMA cache_size=-64000;")   # 64MB cache
        await self._conn.execute("PRAGMA mmap_size=2147483648;")  # 2GB mmap
        await self._conn.execute("PRAGMA temp_store=MEMORY;")
        await self._conn.execute("PRAGMA query_only=ON;")  # read-only safety

        logger.info("Database connected with WAL mode and optimized settings.")

    async def close(self):
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed.")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    # ── Search Methods ─────────────────────────────────────────────

    @retry_on_lock
    async def search_by_mobile(self, mobile: str) -> list[dict[str, Any]]:
        """Exact match on indexed mobile column — O(log n), very fast."""
        query = "SELECT * FROM users WHERE mobile = ? LIMIT ?"
        async with self.conn.execute(query, (mobile, MAX_RESULTS)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    @retry_on_lock
    async def search_by_alt_mobile(self, mobile: str) -> list[dict[str, Any]]:
        """Search alt_mobile column for linked numbers."""
        query = "SELECT * FROM users WHERE alt_mobile = ? LIMIT ?"
        async with self.conn.execute(query, (mobile, MAX_RESULTS)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def deep_search(self, seed_mobile: str, max_depth: int = 3) -> dict[str, Any]:
        """
        BFS deep-link search: follow mobile ↔ alt_mobile chains.
        Returns a consolidated profile with all linked numbers, records, and addresses.
        
        Flow:
        1. Search seed_mobile in both mobile & alt_mobile columns
        2. Collect all alt_mobile & mobile numbers from results
        3. Search those new numbers (BFS) up to max_depth levels
        4. Return consolidated profile
        """
        visited_numbers: set[str] = set()
        queue: list[str] = [seed_mobile]
        all_rows: list[dict[str, Any]] = []
        seen_rowids: set[int] = set()  # avoid duplicate rows

        depth = 0
        while queue and depth < max_depth:
            next_queue: list[str] = []

            for number in queue:
                if number in visited_numbers:
                    continue
                visited_numbers.add(number)

                # Search both mobile and alt_mobile columns
                rows_mobile = await self.search_by_mobile(number)
                rows_alt = await self.search_by_alt_mobile(number)

                for row in rows_mobile + rows_alt:
                    row_id = row.get("rowid") or id(row)
                    # Use a content-based key to deduplicate
                    row_key = (
                        row.get("mobile", ""),
                        row.get("name", ""),
                        row.get("fname", ""),
                        row.get("address", ""),
                    )
                    row_hash = hash(row_key)
                    if row_hash not in seen_rowids:
                        seen_rowids.add(row_hash)
                        all_rows.append(row)

                    # Collect new numbers to search
                    mob = str(row.get("mobile", "")).strip()
                    alt = str(row.get("alt_mobile", "")).strip()

                    if mob and mob not in visited_numbers and len(mob) == 10:
                        next_queue.append(mob)
                    if alt and alt not in visited_numbers and len(alt) >= 10:
                        # Clean alt_mobile if it has prefix
                        alt_clean = alt[-10:] if len(alt) > 10 else alt
                        if alt_clean not in visited_numbers:
                            next_queue.append(alt_clean)

            queue = next_queue
            depth += 1

        # Build consolidated profile
        return self._build_profile(seed_mobile, all_rows, visited_numbers)

    def _build_profile(
        self,
        seed: str,
        rows: list[dict[str, Any]],
        all_numbers: set[str],
    ) -> dict[str, Any]:
        """Consolidate rows into a single OSINT profile."""
        phones: list[str] = []
        addresses: list[str] = []
        names: list[str] = []
        fnames: list[str] = []
        emails: list[str] = []
        circles: list[str] = []
        op_ids: list[str] = []

        seen_phones: set[str] = set()
        seen_addr: set[str] = set()
        seen_names: set[str] = set()
        seen_fnames: set[str] = set()
        seen_emails: set[str] = set()
        seen_circles: set[str] = set()

        for row in rows:
            # Phones
            mob = str(row.get("mobile", "")).strip()
            alt = str(row.get("alt_mobile", "")).strip()
            if mob and mob not in seen_phones:
                seen_phones.add(mob)
                phones.append(mob)
            if alt and alt not in seen_phones and alt != "N/A" and alt:
                seen_phones.add(alt)
                phones.append(alt)

            # Names
            name = str(row.get("name", "")).strip()
            if name and name not in seen_names and name != "None":
                seen_names.add(name)
                names.append(name)

            fname = str(row.get("fname", "")).strip()
            if fname and fname not in seen_fnames and fname != "None":
                seen_fnames.add(fname)
                fnames.append(fname)

            # Email
            email = str(row.get("email", "")).strip()
            if email and email not in seen_emails and email != "None" and email != "N/A":
                seen_emails.add(email)
                emails.append(email)

            # Address
            addr = str(row.get("address", "")).strip()
            if addr and addr not in seen_addr and addr != "None":
                seen_addr.add(addr)
                addresses.append(addr)

            # Circle
            circle = str(row.get("circle", "")).strip()
            if circle and circle not in seen_circles and circle != "None":
                seen_circles.add(circle)
                circles.append(circle)

            # Operator ID
            oid = str(row.get("operator_id", "")).strip()
            if oid and oid != "None":
                op_ids.append(oid)

        return {
            "seed": seed,
            "phones": phones,
            "names": names,
            "fnames": fnames,
            "emails": emails,
            "addresses": addresses,
            "circles": circles,
            "op_ids": op_ids,
            "total_records": len(rows),
            "total_phones": len(phones),
        }

    # ── Utility Methods ────────────────────────────────────────────

    @retry_on_lock
    async def search_by_name(self, name: str) -> list[dict[str, Any]]:
        """LIKE search on name — full scan, limited results."""
        query = "SELECT * FROM users WHERE name LIKE ? LIMIT ?"
        async with self.conn.execute(query, (f"%{name}%", MAX_RESULTS)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    @retry_on_lock
    async def get_row_count(self) -> int:
        """Get approximate row count (fast for large tables)."""
        query = "SELECT MAX(rowid) FROM users"
        async with self.conn.execute(query) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 0

    @retry_on_lock
    async def get_db_size(self) -> int:
        """Get database page count * page size = file size in bytes."""
        async with self.conn.execute("PRAGMA page_count") as c1:
            page_count = (await c1.fetchone())[0]
        async with self.conn.execute("PRAGMA page_size") as c2:
            page_size = (await c2.fetchone())[0]
        return page_count * page_size


# ── Singleton instance ─────────────────────────────────────────────
db = DatabaseManager()
