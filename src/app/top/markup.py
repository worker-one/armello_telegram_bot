from telebot import types

from ..match.models import Clan


def create_top_selection_markup(lang: str) -> types.InlineKeyboardMarkup:
    """Create markup for top selection menu"""
    markup = types.InlineKeyboardMarkup()
    
    markup.add(
        types.InlineKeyboardButton(
            text="Топ-10 игроков по общему рейтингу",
            callback_data="top_players_overall"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="Топ-10 игроков на герое",
            callback_data="top_players_by_hero"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="Топ-10 игроков клана",
            callback_data="top_players_by_clan"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="Топ-24 героев по общему рейтингу",
            callback_data="top_heroes"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="Топ-6 кланов по общему рейтингу",
            callback_data="top_clans"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="Выход",
            callback_data="top_exit"
        )
    )
    
    return markup


def create_clan_selection_markup(lang: str, clans: list[Clan]) -> types.InlineKeyboardMarkup:
    """Create markup for clan selection"""
    markup = types.InlineKeyboardMarkup()
    
    for clan in clans:
        markup.add(
            types.InlineKeyboardButton(
                text=clan.name,
                callback_data=f"top_clan_{clan.id}"
            )
        )
    
    markup.add(
        types.InlineKeyboardButton(
            text="Назад",
            callback_data="top_back"
        )
    )
    
    return markup