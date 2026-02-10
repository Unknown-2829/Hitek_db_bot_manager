"""
User Command Handlers
Handles /start, /help, /search, /stats, and direct text (mobile number only).
Uses deep-link search to find all connected records.
"""

import logging
import re
import time
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

from bot.database import db
from bot.formatters import (
    format_profile,
    format_welcome,
    format_help,
    format_stats,
)
from bot.user_store import user_store

logger = logging.getLogger(__name__)
router = Router(name="user")

# ── Global counters ────────────────────────────────────────────────
search_count: int = 0
start_time: float = time.time()


def get_search_count() -> int:
    return search_count


def get_uptime() -> str:
    elapsed = int(time.time() - start_time)
    days, rem = divmod(elapsed, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def _log_search(user_id: int, username: str | None, query: str, results: int):
    """Log search to the search history log file."""
    global search_count
    search_count += 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uname = username or "N/A"
    logger.info(
        f"[SEARCH] {timestamp} | User: {user_id} (@{uname}) | "
        f"Query: {query} | Results: {results}"
    )


def _clean_mobile(raw: str) -> tuple[str | None, bool]:
    """
    Extract a clean 10-digit Indian mobile number from any format.
    Returns (10-digit string or None, was_auto_corrected).
    """
    digits = re.sub(r"[^\d]", "", raw)

    if not digits:
        return None, False

    original_digits = digits

    # Strip leading country code / trunk prefix
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    elif len(digits) == 13 and digits.startswith("091"):
        digits = digits[3:]

    # Must be exactly 10 digits now
    if len(digits) == 10 and digits[0] in "6789":
        was_corrected = original_digits != digits
        return digits, was_corrected

    return None, False


# ── /start ─────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_store.add_user(message.from_user.id)
    await message.answer(format_welcome(), parse_mode="HTML")


# ── /help ──────────────────────────────────────────────────────────
@router.message(Command("help"))
async def cmd_help(message: Message):
    user_store.add_user(message.from_user.id)
    await message.answer(format_help(), parse_mode="HTML")


# ── /stats ─────────────────────────────────────────────────────────
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    user_store.add_user(message.from_user.id)
    import bot.state as state

    text = format_stats(
        total_searches=search_count,
        total_users=user_store.user_count,
        bot_mode=state.bot_mode,
        uptime=get_uptime(),
    )
    await message.answer(text, parse_mode="HTML")


# ── /search <number> ──────────────────────────────────────────────
@router.message(Command("search"))
async def cmd_search(message: Message):
    user_store.add_user(message.from_user.id)
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "⚠️ <b>Usage:</b> <code>/search 9876543210</code>",
            parse_mode="HTML",
        )
        return

    await _do_mobile_search(message, args[1].strip())


# ── Direct text messages → mobile search ──────────────────────────
@router.message(F.text & ~F.text.startswith("/"))
async def handle_direct_text(message: Message):
    user_store.add_user(message.from_user.id)
    query = message.text.strip()
    if not query:
        return
    await _do_mobile_search(message, query)


# ── Core mobile search logic ──────────────────────────────────────
async def _do_mobile_search(message: Message, raw_input: str):
    """Clean the input, validate as 10-digit mobile, deep search."""

    mobile, was_corrected = _clean_mobile(raw_input)

    if mobile is None:
        await message.reply(
            "❌ <b>Invalid input.</b> Send a 10-digit mobile number.\n"
            "✅ Example: <code>9876543210</code>",
            parse_mode="HTML",
        )
        return

    # Simple auto-correct note — no verbose warnings
    correct_note = ""
    if was_corrected:
        correct_note = f"  🔄 <code>{raw_input}</code> → <code>{mobile}</code>\n"

    processing = await message.reply(
        f"🔍 <b>Searching:</b> <code>{mobile}</code>\n"
        f"{correct_note}"
        f"⏳ <i>Running deep-link analysis...</i>",
        parse_mode="HTML",
    )

    try:
        t_start = time.perf_counter()
        profile = await db.deep_search(mobile)
        elapsed_ms = int((time.perf_counter() - t_start) * 1000)

        text = format_profile(profile, elapsed_ms=elapsed_ms)
        _log_search(
            message.from_user.id,
            message.from_user.username,
            mobile,
            profile.get("total_records", 0),
        )
        await processing.edit_text(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Deep search error: {e}")
        await processing.edit_text(f"❌ <b>Error:</b> <code>{e}</code>", parse_mode="HTML")
