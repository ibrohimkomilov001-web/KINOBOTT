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
    field = State()   # qaysi maydon o'zgaradi
    value = State()   # yangi qiymat


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
    """Kanal qo'shish FSM."""
    chat_id = State()       # 1. Chat ID kiritish
    is_required = State()   # 2. Majburiy obuna?
    confirm = State()       # 3. Tasdiqlash


# ═══════════════════════════════════════════════════════════════
# Broadcast
# ═══════════════════════════════════════════════════════════════

class BroadcastSG(StatesGroup):
    """Broadcast FSM — maximum API."""
    mode = State()          # 1. Rejim tanlash (yangi/forward/copy)
    content = State()       # 2. Xabar mazmuni (matn + media)
    buttons = State()       # 3. Tugmalar (ixtiyoriy)
    segment = State()       # 4. Segmentlash (ixtiyoriy)
    preview = State()       # 5. Ko'rik + tasdiqlash


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


# ═══════════════════════════════════════════════════════════════
# Reklama
# ═══════════════════════════════════════════════════════════════

class AdSG(StatesGroup):
    """Reklama yaratish FSM."""
    content = State()    # Matn + media
    buttons = State()    # Tugmalar
    duration = State()   # Muddat (kunlar)
    confirm = State()    # Tasdiqlash
