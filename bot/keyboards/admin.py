from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional

# ═══════════════════════════════════════════════════════════════
# Admin Reply Keyboard (5 tugma, 2x3)
# ═══════════════════════════════════════════════════════════════

ADMIN_BUTTONS = {
    "stats": "📊 Statistika",
    "broadcast": "📢 Xabar yuborish",
    "channels": "🔗 Kanallar",
    "movies": "🎬 Kinolar",
    "settings": "⚙️ Sozlamalar",
}


def admin_main_reply_kb() -> ReplyKeyboardMarkup:
    """Admin asosiy reply keyboard (5 tugma, 2x3 layout)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_BUTTONS["stats"]), KeyboardButton(text=ADMIN_BUTTONS["broadcast"])],
            [KeyboardButton(text=ADMIN_BUTTONS["channels"]), KeyboardButton(text=ADMIN_BUTTONS["movies"])],
            [KeyboardButton(text=ADMIN_BUTTONS["settings"])],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def remove_reply_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ═══════════════════════════════════════════════════════════════
# Kino boshqaruvi sub-menu
# ═══════════════════════════════════════════════════════════════

def movie_menu_kb() -> InlineKeyboardMarkup:
    """Kino boshqaruv menu — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="movie_add"),
            InlineKeyboardButton(text="📺 Serial qo'shish", callback_data="series_add"),
        ],
        [
            InlineKeyboardButton(text="📋 Kinolar", callback_data="movie_list:0"),
            InlineKeyboardButton(text="📋 Seriallar", callback_data="series_list:0"),
        ],
        [
            InlineKeyboardButton(text="🔍 Qidiruv", callback_data="movie_search"),
            InlineKeyboardButton(text="🔙 Yopish", callback_data="admin_close"),
        ],
    ])


def movie_list_kb(movies: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Kino ro'yxati paginatsiya bilan."""
    builder = InlineKeyboardBuilder()
    for m in movies:
        builder.row(InlineKeyboardButton(
            text=f"🎬 {m.code} — {m.title}",
            callback_data=f"movie_view:{m.id}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"movie_list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"movie_list:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="movie_menu"))
    return builder.as_markup()


def movie_detail_kb(movie_id: int) -> InlineKeyboardMarkup:
    """Kino tafsilotlar — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"movie_edit:{movie_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"movie_del:{movie_id}"),
        ],
        [
            InlineKeyboardButton(text="📤 Kanalga yub.", callback_data=f"movie_resend:{movie_id}"),
            InlineKeyboardButton(text="📊 Statistika", callback_data=f"movie_stats:{movie_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Ro'yxatga", callback_data="movie_list:0")],
    ])


def movie_edit_kb(movie_id: int) -> InlineKeyboardMarkup:
    """Kino tahrirlash maydonlari — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Nom", callback_data=f"medit:{movie_id}:title"),
            InlineKeyboardButton(text="📄 Tavsif", callback_data=f"medit:{movie_id}:description"),
        ],
        [
            InlineKeyboardButton(text="🎭 Janrlar", callback_data=f"medit:{movie_id}:genres"),
            InlineKeyboardButton(text="📅 Yil", callback_data=f"medit:{movie_id}:year"),
        ],
        [
            InlineKeyboardButton(text="🎞 Video", callback_data=f"medit:{movie_id}:video"),
            InlineKeyboardButton(text="🔢 Kod", callback_data=f"medit:{movie_id}:code"),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"movie_view:{movie_id}")],
    ])


# ═══════════════════════════════════════════════════════════════
# Serial sub-menu
# ═══════════════════════════════════════════════════════════════

def series_list_kb(series_list: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in series_list:
        builder.row(InlineKeyboardButton(
            text=f"📺 {s.code} — {s.title}",
            callback_data=f"series_view:{s.id}"
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"series_list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"series_list:{page + 1}"))
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="movie_menu"))
    return builder.as_markup()


def series_detail_kb(series_id: int) -> InlineKeyboardMarkup:
    """Serial tafsilotlar — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Sezon", callback_data=f"season_add:{series_id}"),
            InlineKeyboardButton(text="➕ Epizod", callback_data=f"episode_add:{series_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"series_edit:{series_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"series_del:{series_id}"),
        ],
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data=f"series_stats:{series_id}"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="series_list:0"),
        ],
    ])


def series_edit_kb(series_id: int) -> InlineKeyboardMarkup:
    """Serial tahrirlash maydonlari — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Nom", callback_data=f"sedit:{series_id}:title"),
            InlineKeyboardButton(text="📄 Tavsif", callback_data=f"sedit:{series_id}:description"),
        ],
        [
            InlineKeyboardButton(text="🎭 Janrlar", callback_data=f"sedit:{series_id}:genres"),
            InlineKeyboardButton(text="📅 Yil", callback_data=f"sedit:{series_id}:year"),
        ],
        [
            InlineKeyboardButton(text="🔢 Kod", callback_data=f"sedit:{series_id}:code"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"series_view:{series_id}"),
        ],
    ])


def season_episodes_kb(episodes: list, series_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ep in episodes:
        title = ep.title or f"Epizod {ep.episode_number}"
        builder.row(InlineKeyboardButton(text=f"▶️ {ep.episode_number}. {title}", callback_data=f"ep_play:{ep.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"series_view:{series_id}"))
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════
# Kanal boshqaruvi
# ═══════════════════════════════════════════════════════════════

def channels_kb(channels: list) -> InlineKeyboardMarkup:
    """Kanallar ro'yxati — 2 ustunli."""
    builder = InlineKeyboardBuilder()
    pairs = []
    for ch in channels:
        req = "✅" if ch.is_required else "❌"
        type_emoji = {"public": "📢", "private": "🔒", "request_join": "✋"}.get(ch.type, "📋")
        title = ch.title[:18] + "…" if len(ch.title) > 18 else ch.title
        pairs.append(InlineKeyboardButton(
            text=f"{req}{type_emoji} {title}",
            callback_data=f"ch_view:{ch.id}"
        ))
    # 2 ustun joylash
    for i in range(0, len(pairs), 2):
        row = pairs[i:i+2]
        builder.row(*row)
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="ch_add"))
    return builder.as_markup()


def channel_type_kb() -> InlineKeyboardMarkup:
    """Kanal turini tanlash — 1 ustun (uzun matnlar)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Oddiy kanal (public)", callback_data="ch_type:public")],
        [InlineKeyboardButton(text="🔒 Yopiq kanal (invite link)", callback_data="ch_type:private")],
        [InlineKeyboardButton(text="✋ So'rovli kanal/guruh", callback_data="ch_type:request_join")],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="ch_cancel")],
    ])


def channel_required_kb() -> InlineKeyboardMarkup:
    """Majburiy obuna so'rovi — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, majburiy", callback_data="ch_req:yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="ch_req:no"),
        ]
    ])


def channel_detail_kb(ch) -> InlineKeyboardMarkup:
    """Kanal tafsilotlar — 2 ustunli (auto-invite olib tashlandi)."""
    req_text = "❌ Majburiyni o'chirish" if ch.is_required else "✅ Majburiyga"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=req_text, callback_data=f"ch_toggle:{ch.id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"ch_del:{ch.id}"),
        ],
        [
            InlineKeyboardButton(text="🔗 Linkni ko'rish", callback_data=f"ch_link:{ch.id}"),
            InlineKeyboardButton(text="📊 Statistika", callback_data=f"ch_stats:{ch.id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ch_list")],
    ])


# ═══════════════════════════════════════════════════════════════
# Broadcast — Maximum API
# ═══════════════════════════════════════════════════════════════

def broadcast_mode_kb() -> InlineKeyboardMarkup:
    """Broadcast rejim tanlash — 2 ustunli + tarix."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Yangi xabar", callback_data="bc_mode:custom"),
            InlineKeyboardButton(text="↗️ Forward", callback_data="bc_mode:forward"),
        ],
        [
            InlineKeyboardButton(text="📋 Copy", callback_data="bc_mode:copy"),
            InlineKeyboardButton(text="🎨 Rich tugmali", callback_data="bc_mode:rich"),
        ],
        [
            InlineKeyboardButton(text="📜 Tarix", callback_data="bc_history"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="bc_cancel"),
        ],
    ])


def broadcast_after_content_kb() -> InlineKeyboardMarkup:
    """Content qabul qilingandan keyin — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Tugma qo'shish", callback_data="bc_add_buttons"),
            InlineKeyboardButton(text="🎯 Segmentlash", callback_data="bc_segment"),
        ],
        [
            InlineKeyboardButton(text="👁 Ko'rik", callback_data="bc_preview"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="bc_cancel"),
        ],
    ])


def broadcast_segment_kb(target_count: int = 0) -> InlineKeyboardMarkup:
    """Segment tanlash — 2 ustunli, real-time maqsad soni."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Barchaga", callback_data="bc_seg:all"),
            InlineKeyboardButton(text="⭐ Premium", callback_data="bc_seg:premium"),
        ],
        [
            InlineKeyboardButton(text="🆕 Yangi (1k)", callback_data="bc_seg:new_1"),
            InlineKeyboardButton(text="🆕 Yangi (7k)", callback_data="bc_seg:new_7"),
        ],
        [
            InlineKeyboardButton(text="🔥 Faol (1k)", callback_data="bc_seg:active_1"),
            InlineKeyboardButton(text="📅 Faol (7k)", callback_data="bc_seg:active_7"),
        ],
        [
            InlineKeyboardButton(text="🗓 Faol (30k)", callback_data="bc_seg:active_30"),
            InlineKeyboardButton(text="🎯 Custom filter", callback_data="bc_seg:custom"),
        ],
        [
            InlineKeyboardButton(text=f"🎯 Maqsad: {target_count}", callback_data="noop"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="bc_back_content"),
        ],
    ])


def broadcast_custom_segment_kb(filters: dict, target_count: int = 0) -> InlineKeyboardMarkup:
    """Custom multi-AND filter — har filter bir qatorda."""
    active = filters.get("active", "all")    # all/1/7/30
    new_filter = filters.get("new", "all")
    lang = filters.get("lang", "all")
    premium = filters.get("premium", "all")

    def mark(value: str, current: str) -> str:
        return "✅" if value == current else "▫️"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Faollik", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{mark('all', active)} ∞", callback_data="bc_cf:active:all"),
            InlineKeyboardButton(text=f"{mark('1', active)} 1k", callback_data="bc_cf:active:1"),
            InlineKeyboardButton(text=f"{mark('7', active)} 7k", callback_data="bc_cf:active:7"),
            InlineKeyboardButton(text=f"{mark('30', active)} 30k", callback_data="bc_cf:active:30"),
        ],
        [InlineKeyboardButton(text="🆕 Yangilik", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{mark('all', new_filter)} ∞", callback_data="bc_cf:new:all"),
            InlineKeyboardButton(text=f"{mark('1', new_filter)} 1k", callback_data="bc_cf:new:1"),
            InlineKeyboardButton(text=f"{mark('7', new_filter)} 7k", callback_data="bc_cf:new:7"),
            InlineKeyboardButton(text=f"{mark('30', new_filter)} 30k", callback_data="bc_cf:new:30"),
        ],
        [InlineKeyboardButton(text="🌍 Til", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{mark('all', lang)} Hammasi", callback_data="bc_cf:lang:all"),
            InlineKeyboardButton(text=f"{mark('uz', lang)} UZ", callback_data="bc_cf:lang:uz"),
            InlineKeyboardButton(text=f"{mark('ru', lang)} RU", callback_data="bc_cf:lang:ru"),
            InlineKeyboardButton(text=f"{mark('en', lang)} EN", callback_data="bc_cf:lang:en"),
        ],
        [InlineKeyboardButton(text="⭐ Premium", callback_data="noop")],
        [
            InlineKeyboardButton(text=f"{mark('all', premium)} Hammasi", callback_data="bc_cf:premium:all"),
            InlineKeyboardButton(text=f"{mark('yes', premium)} Faqat Premium", callback_data="bc_cf:premium:yes"),
            InlineKeyboardButton(text=f"{mark('no', premium)} Premium emas", callback_data="bc_cf:premium:no"),
        ],
        [
            InlineKeyboardButton(text=f"🎯 Maqsad: {target_count}", callback_data="bc_cf:refresh"),
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="bc_cf:apply"),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="bc_segment")],
    ])


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    """Yuborish tasdiqlash — 2 ustunli + test."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 Yuborish", callback_data="bc_confirm"),
            InlineKeyboardButton(text="🧪 Menga test", callback_data="bc_test"),
        ],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="bc_cancel")],
    ])


def broadcast_controls(broadcast_id: int) -> InlineKeyboardMarkup:
    """Davom etayotgan broadcast — 2 ustun."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏸ Pauza", callback_data=f"bc_pause:{broadcast_id}"),
            InlineKeyboardButton(text="▶️ Davom", callback_data=f"bc_resume:{broadcast_id}"),
        ],
        [InlineKeyboardButton(text="❌ To'xtatish", callback_data=f"bc_stop:{broadcast_id}")],
    ])


def broadcast_history_kb(broadcasts: list) -> InlineKeyboardMarkup:
    """Broadcast tarixi — har broadcast 1 qator."""
    builder = InlineKeyboardBuilder()
    for bc in broadcasts:
        emoji = {"completed": "✅", "running": "🚀", "paused": "⏸", "failed": "❌", "draft": "📝"}.get(bc.status, "❓")
        builder.row(InlineKeyboardButton(
            text=f"{emoji} #{bc.id} | {bc.sent_count}/{bc.target_count}",
            callback_data=f"bc_info:{bc.id}"
        ))
    builder.row(
        InlineKeyboardButton(text="📤 CSV eksport", callback_data="bc_export"),
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data="bc_back_mode"),
    )
    return builder.as_markup()


# ═══════════════════════════════════════════════════════════════
# Sozlamalar (Adminlar shu yerda)
# ═══════════════════════════════════════════════════════════════

def settings_kb(auto_code: bool, force_sub: bool, maintenance: bool) -> InlineKeyboardMarkup:
    """Sozlamalar — 2 ustunli + Adminlar shu yerda."""
    ac = "🟢" if auto_code else "🔴"
    fs = "🟢" if force_sub else "🔴"
    mt = "🟢" if maintenance else "🔴"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{ac} Auto kod", callback_data="set_toggle:auto_code"),
            InlineKeyboardButton(text=f"{fs} Majburiy obuna", callback_data="set_toggle:force_subscription"),
        ],
        [
            InlineKeyboardButton(text=f"{mt} Texnik ish.", callback_data="set_toggle:maintenance_mode"),
            InlineKeyboardButton(text="📊 BC tezligi", callback_data="set_bc_rate"),
        ],
        [
            InlineKeyboardButton(text="💾 Backup olish", callback_data="set_backup"),
            InlineKeyboardButton(text="📥 Backup tiklash", callback_data="set_restore"),
        ],
        [
            InlineKeyboardButton(text="📺 Baza kanal", callback_data="set_base_channel"),
            InlineKeyboardButton(text="👥 Adminlar", callback_data="admin:list"),
        ],
        [InlineKeyboardButton(text="🔙 Yopish", callback_data="admin_close")],
    ])


# ═══════════════════════════════════════════════════════════════
# Adminlar
# ═══════════════════════════════════════════════════════════════

def admins_kb(admins: list) -> InlineKeyboardMarkup:
    """Adminlar ro'yxati."""
    builder = InlineKeyboardBuilder()
    for a in admins:
        builder.row(InlineKeyboardButton(
            text=f"👤 {a.user_id} — {a.role}",
            callback_data=f"adm_view:{a.user_id}"
        ))
    builder.row(
        InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="adm_add"),
        InlineKeyboardButton(text="⬅️ Sozlamalarga", callback_data="admin:settings"),
    )
    return builder.as_markup()


def admin_detail_kb(user_id: int) -> InlineKeyboardMarkup:
    """Admin tafsilot — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"adm_del:{user_id}"),
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_list"),
        ],
    ])


# ═══════════════════════════════════════════════════════════════
# Statistika
# ═══════════════════════════════════════════════════════════════

def stats_kb() -> InlineKeyboardMarkup:
    """Statistika qo'shimcha tugmalar — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📈 Top kontent", callback_data="stats_top"),
            InlineKeyboardButton(text="📉 Top qidiruv", callback_data="stats_search"),
        ],
        [
            InlineKeyboardButton(text="👥 Kanallar", callback_data="stats_channels"),
            InlineKeyboardButton(text="📤 CSV eksport", callback_data="stats_export"),
        ],
        [InlineKeyboardButton(text="🔙 Yopish", callback_data="admin_close")],
    ])


# ═══════════════════════════════════════════════════════════════
# Umumiy
# ═══════════════════════════════════════════════════════════════

def confirm_kb(prefix: str) -> InlineKeyboardMarkup:
    """Tasdiqlash — 2 ustunli."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"{prefix}_confirm"),
            InlineKeyboardButton(text="❌ Bekor", callback_data=f"{prefix}_cancel"),
        ]
    ])


def back_kb(callback_data: str = "admin_back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=callback_data)]
    ])


def skip_kb(callback_data: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ O'tkazish", callback_data=callback_data)]
    ])


# ═══════════════════════════════════════════════════════════════
# Rich button parser (multi-row + multi-column)
# ═══════════════════════════════════════════════════════════════

def parse_buttons_text(text: str) -> Optional[InlineKeyboardMarkup]:
    """Parse admin button text into InlineKeyboardMarkup.

    Format:
        Tugma1 | https://link1.com
        Tugma2 | https://link2.com
        ---
        Tugma3 | https://link3.com

    Same row (multi-column) bilan: 'Tugma1 | url1 :: Tugma2 | url2'
    Callback: 'Matn | callback:my_data'
    URL: 'Matn | https://...'

    Web-app qo'llab-quvvatlanmaydi.
    """
    if not text:
        return None

    rows: List[List[InlineKeyboardButton]] = []

    def _make_button(cell: str) -> Optional[InlineKeyboardButton]:
        parts = [p.strip() for p in cell.split("|")]
        if len(parts) < 2:
            return None
        btn_text, btn_data = parts[0], parts[1]
        if not btn_text or not btn_data:
            return None
        if btn_data.startswith("http://") or btn_data.startswith("https://") or btn_data.startswith("tg://"):
            return InlineKeyboardButton(text=btn_text, url=btn_data)
        if btn_data.startswith("callback:"):
            return InlineKeyboardButton(text=btn_text, callback_data=btn_data.replace("callback:", "", 1))
        # Default: treat as URL
        return InlineKeyboardButton(text=btn_text, url=btn_data)

    for raw_line in text.strip().split("\n"):
        line = raw_line.strip()
        if not line or line == "---":
            continue
        # Multi-column in same row separated by '::'
        row: List[InlineKeyboardButton] = []
        for cell in line.split("::"):
            cell = cell.strip()
            if not cell:
                continue
            btn = _make_button(cell)
            if btn:
                row.append(btn)
        if row:
            rows.append(row)

    if not rows:
        return None

    return InlineKeyboardMarkup(inline_keyboard=rows)

