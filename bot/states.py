from aiogram.fsm.state import State, StatesGroup


class AddMovieSG(StatesGroup):
    """States for adding a movie."""
    
    title = State()
    code = State()
    genres = State()
    year = State()
    duration = State()
    video = State()
    confirm = State()


class AddSeriesSG(StatesGroup):
    """States for adding a series."""
    
    title = State()
    code = State()
    genres = State()
    year = State()
    confirm = State()


class AddSeasonSG(StatesGroup):
    """States for adding a season."""
    
    series_id = State()
    season_number = State()
    confirm = State()


class AddEpisodeSG(StatesGroup):
    """States for adding an episode."""
    
    season_id = State()
    episode_number = State()
    title = State()
    duration = State()
    video = State()
    confirm = State()


class AddChannelSG(StatesGroup):
    """States for adding a subscription channel."""
    
    tg_chat_id = State()
    title = State()
    channel_type = State()
    is_required = State()
    confirm = State()


class BroadcastSG(StatesGroup):
    """States for creating a broadcast."""
    
    text = State()
    media = State()
    media_type = State()  # photo, video, animation, audio, voice, document
    buttons = State()
    button_layout = State()  # 2col, 1col, custom
    segment = State()
    segment_lang = State()
    segment_active_days = State()
    segment_joined_after = State()
    confirm = State()


class AddAdminSG(StatesGroup):
    """States for adding an admin."""
    
    user_input = State()


class SearchSG(StatesGroup):
    """States for search interaction."""
    
    query = State()
    category = State()  # movie, series, all
