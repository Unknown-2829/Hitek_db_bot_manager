"""
Result Formatters — Professional OSINT Intelligence Output
Consolidated profile view: all linked phones, addresses, identities grouped.
"""

import re
from html import escape
from typing import Any


def clean_address(raw: str | None) -> str:
    """Clean garbage from address field."""
    if not raw:
        return ""
    addr = raw.strip()
    addr = addr.replace("!!", ", ").replace("!", ", ")
    addr = addr.lstrip(", ")
    addr = re.sub(r"[,\s]{2,}", ", ", addr)
    addr = addr.rstrip(", ").strip()
    return addr


def _safe(value: Any) -> str:
    """HTML-escape a value, return empty for None."""
    if value is None:
        return ""
    s = str(value).strip()
    if s in ("None", "N/A", ""):
        return ""
    return escape(s)


def format_profile(profile: dict[str, Any], elapsed_ms: int = 0) -> str:
    """
    Format consolidated OSINT profile — all linked data grouped.
    Similar to professional OSINT tools.
    """
    time_str = f"  ⏱ <code>{elapsed_ms}ms</code>" if elapsed_ms else ""

    phones = profile.get("phones", [])
    names = profile.get("names", [])
    fnames = profile.get("fnames", [])
    emails = profile.get("emails", [])
    addresses = profile.get("addresses", [])
    circles = profile.get("circles", [])
    total_records = profile.get("total_records", 0)
    seed = profile.get("seed", "")

    if total_records == 0:
        return (
            "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
            "  ❌ <b>TARGET NOT FOUND</b>\n"
            "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n\n"
            f"  🎯 Target : <code>{escape(seed)}</code>{time_str}\n\n"
            "<i>Verify the number and try again.</i>"
        )

    # ── Build profile output ──
    lines = []

    # Header
    lines.append("▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")
    lines.append(f"  🎯 <b>TARGET LOCATED</b>{time_str}")
    lines.append("▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓")
    lines.append("")

    # Phones
    for phone in phones:
        lines.append(f"📞 Telephone:  <code>{escape(phone)}</code>")

    if phones:
        lines.append("")

    # Addresses
    for addr in addresses:
        cleaned = escape(clean_address(addr))
        if cleaned:
            lines.append(f"🏘 Address:  {cleaned}")

    if addresses:
        lines.append("")

    # Names
    for name in names:
        lines.append(f"👤 Full Name:  {escape(name)}")

    # Father names
    for fname in fnames:
        lines.append(f"👨 Father:  {escape(fname)}")

    if names or fnames:
        lines.append("")

    # Emails
    for email in emails:
        lines.append(f"📧 Email:  <code>{escape(email)}</code>")

    if emails:
        lines.append("")

    # Circles / Region
    if circles:
        region = ";".join(circles)
        lines.append(f"🗺 Region:  {escape(region)}")
        lines.append("")

    # Footer
    lines.append(f"<code>{'─' * 31}</code>")
    lines.append(
        f"📊 <b>{total_records}</b> records"
        f" · <b>{len(phones)}</b> phone{'s' if len(phones) != 1 else ''}"
        f" | ⚡ <b>HiTek OSINT</b>"
    )

    return "\n".join(lines)


def format_welcome() -> str:
    """Welcome — professional OSINT tool branding."""
    return (
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
        "       ⚡ <b>HiTek OSINT</b> ⚡\n"
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n\n"
        "  📊  <b>1.78B</b> Records Indexed\n"
        "  ⚡  Deep-Link Intelligence\n"
        "  🔒  Encrypted &amp; Secure\n\n"
        "<code>─────────────────────────────────</code>\n\n"
        "📱 <b>Quick Start:</b>\n"
        "  ▸ Send any <b>10-digit mobile</b>\n"
        "  ▸ <code>/search 9876543210</code>\n\n"
        "📋 <b>Commands:</b>\n"
        "  /help   — Command list\n"
        "  /stats  — Statistics"
    )


def format_help() -> str:
    """Help — compact command reference."""
    return (
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
        "        📖 <b>Command List</b>\n"
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n\n"
        "<b>🔍 Search:</b>\n"
        "  /search <code>&lt;number&gt;</code>\n"
        "  <i>Or just type a 10-digit number</i>\n\n"
        "<b>📊 Info:</b>\n"
        "  /stats — Bot statistics\n"
        "  /help  — This menu\n\n"
        "<b>📱 Input:</b>\n"
        "  ✅ <code>9876543210</code>\n"
        "  🔄 <code>+91 98765 43210</code> → auto-fix\n"
        "  🔄 <code>09876543210</code> → auto-fix"
    )


def format_admin_help() -> str:
    """Admin panel."""
    return (
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
        "        🔐 <b>Admin Panel</b>\n"
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n\n"
        "<b>⚙️ System:</b>\n"
        "  /setmode <code>&lt;public|private&gt;</code>\n"
        "  /getmode — Current mode\n\n"
        "<b>📝 Logs:</b>\n"
        "  /logs     — Download log\n"
        "  /clearlog — Clear log\n\n"
        "<b>📊 Stats:</b>\n"
        "  /dbstats — Database info\n"
        "  /users   — User count\n\n"
        "<b>📡 Broadcast:</b>\n"
        "  /alert <code>&lt;msg&gt;</code>\n\n"
        "<b>🚫 Moderation:</b>\n"
        "  /ban <code>&lt;id&gt;</code>  · /unban <code>&lt;id&gt;</code>  · /banlist"
    )


def format_stats(
    total_searches: int,
    total_users: int,
    bot_mode: str,
    uptime: str,
) -> str:
    """Bot statistics."""
    mode_emoji = "🌐" if bot_mode.lower() == "public" else "🔒"
    return (
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
        "       📊 <b>Statistics</b>\n"
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n\n"
        f"  🔍  Searches  :  <code>{total_searches:,}</code>\n"
        f"  👥  Users     :  <code>{total_users:,}</code>\n"
        f"  {mode_emoji}  Mode      :  <code>{bot_mode.upper()}</code>\n"
        f"  ⏱  Uptime    :  <code>{uptime}</code>"
    )


def format_dbstats(row_count: int, size_str: str) -> str:
    """Database statistics."""
    return (
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n"
        "       💾 <b>Database Info</b>\n"
        "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n\n"
        f"  📊  Rows    :  <code>{row_count:,}</code>\n"
        f"  💽  Size    :  <code>{size_str}</code>\n"
        f"  📁  Path    :  <code>/data/users.db</code>\n"
        f"  🔧  Journal :  <code>WAL</code>\n"
        f"  💾  Cache   :  <code>64MB</code>\n"
        f"  🗺  MMap    :  <code>2GB</code>"
    )
