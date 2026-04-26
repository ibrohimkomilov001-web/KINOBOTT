from aiogram.fsm.state import State, StatesGroup


# ═══════════════════════════════════════════════════════════════
# Kino boshqaruvi
# ═══════════════════════════════════════════════════════════════

class AddMovieSG(StatesGroup):
    """Kino qo'shish FSM."""
    video = State()        # 1. Video/fayl yuklash
    code = State()         # 2. Kod (auto-tavsiya yoki qo'lda)
    title = State()        # 3. Kino nomi
    description = State()  # 4. Tavsif (ixtiyoriy)
    confirm = State()      # 5. Tasdiqlash


class EditMovieSG(StatesGroup):
    """Kino tahrirlash."""
    field = State()   # qaysi maydon o'zgaradi (tugma orqali)
    value = State()   # yangi qiymat (matn yoki video)


class SearchMovieSG(StatesGroup):
    """Admin uchun kino qidiruv."""
    query = State()


class EditSeriesSG(StatesGroup):
    """Serial tahrirlash."""
    field = State()
    value = State()


# ═══════════════════════════════════════════════════════════════
# Serial boshqaruvi
# ═══════════════════════════════════════════════════════════════

class AddSeriesSG(StatesGroup):
    """Serial qo'shish FSM."""
    title = State()
    code = State()
    description = State()
    confirm = State()


class AddSeasonSG(StatesGroup):
    """Sezon qo'shish."""
    select_series = State()
    season_number = State()
    confirm = State()


class AddEpisodeSG(StatesGroup):
    """Epizod qo'shish."""
    select_series = State()
    select_season = State()
    episode_number = State()
    title = State()
    video = State()
    confirm = State()


# ═══════════════════════════════════════════════════════════════
# Kanal boshqaruvi
# ═══════════════════════════════════════════════════════════════

class AddChannelSG(StatesGroup):
    """Kanal qo'shish FSM (3 turi: public/private/request_join)."""
    channel_type = State()       # 1. Tur tanlash (public/private/request_join)
    chat_id = State()            # 2. Chat ID kiritish
    invite_link_input = State()  # 3. (private/request_join uchun) admin invite link kiritadi
    is_required = State()        # 4. Majburiy obuna?
    confirm = State()            # 5. Tasdiqlash


# ═══════════════════════════════════════════════════════════════
# Broadcast
# ═══════════════════════════════════════════════════════════════

class BroadcastSG(StatesGroup):
    """Broadcast FSM — maximum API."""
    mode = State()             # 1. Rejim tanlash (custom/forward/copy/rich)
    content = State()          # 2. Xabar mazmuni (matn + media)
    buttons = State()          # 3. Tugmalar (rich format)
    segment = State()          # 4. Asosiy segment tanlash
    segment_custom = State()   # 5. Custom multi-AND filter
    preview = State()          # 6. Ko'rik + tasdiqlash


# ═══════════════════════════════════════════════════════════════
# Admin boshqaruvi
# ═══════════════════════════════════════════════════════════════

class AddAdminSG(StatesGroup):
    """Admin qo'shish."""
    user_input = State()


# ═══════════════════════════════════════════════════════════════
# Sozlamalar
# ═══════════════════════════════════════════════════════════════

class SettingsSG(StatesGroup):
    """Sozlamalar FSM."""
    broadcast_rate = State()    # Broadcast tezligi kiritish
    base_channel = State()      # Baza kanal ID kiritish
    restore_file = State()      # Backup fayl qabul qilish


# ═══════════════════════════════════════════════════════════════
# Komment
# ═══════════════════════════════════════════════════════════════

class CommentSG(StatesGroup):
    """Komment yozish FSM."""
    text = State()   # Komment matnini kiritish
