import logging
import typing

from aiogram import Bot, Dispatcher, executor
from aiogram.types import Message, \
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery
from aiogram.utils import callback_data, exceptions
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import ContentType

from datetime import datetime, timedelta
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

# Import modules of this project
from config import ADMINS_TG, API_TOKEN
from services.market_base import BestPrice, Coin, CoinNotFound, Market
import services.api_config


# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('paperwork_bot')

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# Initialize scheduler
scheduler = AsyncIOScheduler()
scheduler.start()

# Sructure of callback buttons
button_cb = callback_data.CallbackData(
    'btn', 'question', 'answer', 'data')

# Preparatons
Coin.update_coins_from_db()


#  ------------------------------------------------------------ ВСПОМОГАТЕЛЬНОЕ
def get_empty_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    return keyboard


def make_inline_keyboard(
        question: str,
        answers: list,
        data=0) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для сообщений

    Args:
        question (str): Под каким сообщение кнопка
        answers (list): список кнопок
        data (int, optional): Дополнительные данные. Defaults to 0.

    Returns:
        InlineKeyboardMarkup
    """
    if not answers:
        return None

    keyboard = InlineKeyboardMarkup()
    row = []
    for answer in answers:  # make a botton for every answer
        cb_data = button_cb.new(
            question=question,
            answer=answer,
            data=data)
        row.append(InlineKeyboardButton(
            answer, callback_data=cb_data)
        )
    if len(row) <= 2:
        keyboard.row(*row)
    else:
        for button in row:
            keyboard.row(button)

    return keyboard


def make_replay_keyboard(answers: typing.List[str]) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for answer_text in answers:
        keyboard.add(KeyboardButton(text=answer_text))
    return keyboard


def is_message_private(message: Message) -> bool:
    """Сообщение из личного чата с ботом?"""
    if message.chat.type == 'private':
        return True
    else:
        return False


#  -------------------------------------------------------------- ВХОД ТГ ЮЗЕРА
@dp.message_handler(
    lambda message: is_message_private(message),
    commands=['start'], state="*")
async def start_command(message: Message, state: FSMContext):
    log.info('start command from: %r', message.from_user.id)

    await message.answer(text='hello_text')


def make_keyboard_with_coins() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    coin_names = [coin.get_upper_name() for coin in Coin.get_all_coins()]
    row = [KeyboardButton(text=name) for name in coin_names]
    for _ in range(len(row)//3):
        keyboard.row(*row[:4])
        row = row[4:]
    keyboard.row(*row)
    return keyboard


@dp.message_handler(
    lambda message: is_message_private(message),
    commands=['all_coins'], state="*")
async def all_coins_command(message: Message, state: FSMContext):
    log.info('start command from: %r', message.from_user.id)
    text = '<b>Все монеты:</b>\n'
    for coin in Coin.get_all_coins():
        text += f'{coin.get_upper_name()}\n'

    keyboard = make_keyboard_with_coins()

    await message.answer(text=text, reply_markup=keyboard)


button_all_prices = 'Посмотреть цены'
button_best_prices = 'Лучшие цены'
button_find_deal = 'Найти пару для сделки'
button_alter_name = 'Добавить имя'
button_delete = 'Удалить'
buttons_for_coin = [
    button_all_prices,
    button_best_prices,
    button_find_deal,
    button_alter_name,
    button_delete]


async def send_price(chat_id: int, coin: Coin):
    log.info('send_price to: %r', chat_id)

    text = f'<b>{coin.get_upper_name()}</b>\n'
    market_list = Market.all_markets
    for market in market_list:
        try:
            text_price = f'{market.get_price(coin).best_ask}$'
        except CoinNotFound:
            text_price = 'not_found'
        text += f'{market.name} - {text_price}\n'

    await bot.send_message(chat_id=chat_id, text=text)


@dp.callback_query_handler(
    button_cb.filter(answer=button_all_prices),
    state='*')
async def callback_all_prices(
        query: CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)
    coin_name = callback_data['question']
    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await query.message.edit_text('Ошибка: Монета не найдена')
        return

    text = f'<b>{coin.get_upper_name()}</b>\n'
    market_list = Market.all_markets
    for market in market_list:
        try:
            price = market.get_price(coin).best_ask
            text_price = f'{price.number} {price.base_coin.get_name()}'
        except CoinNotFound:
            text_price = 'not_found'
        text += f'{market.name} - {text_price}\n'

    await query.message.edit_text(
        text=text
    )


def make_message_for_best_price(best_prices: BestPrice) -> str:
    coin = best_prices.best_ask.coin

    procent = (
        (best_prices.best_bid.number / best_prices.best_ask.number - 1)
        * 100
    )

    link_for_buy = best_prices.best_ask.market.make_link_to_market(
        coin=coin,
        base_coin=best_prices.best_ask.base_coin
    )
    market_for_buy = best_prices.best_ask.market.name

    link_for_sell = best_prices.best_bid.market.make_link_to_market(
        coin=coin,
        base_coin=best_prices.best_bid.base_coin
    )
    market_for_sell = best_prices.best_bid.market.name

    text = (
        f'<b>{coin.get_upper_name()}</b>\n'
        f'{round(procent, 2)}%\n'
        f'<a href="{link_for_buy}">{market_for_buy}</a>'
        f' - {best_prices.best_ask.number}'
        f' {best_prices.best_ask.base_coin.get_name()}\n'
        f'<a href="{link_for_sell}">{market_for_sell}</a>'
        f' - {best_prices.best_bid.number}'
        f' {best_prices.best_bid.base_coin.get_name()}\n'
    )
    return text


@dp.callback_query_handler(
    button_cb.filter(answer=button_best_prices),
    state='*')
async def callback_best_prices(
        query: CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)
    coin_name = callback_data['question']
    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await query.message.edit_text('Ошибка: Монета не найдена')
        return

    try:
        best_prices = Market.get_best_price(coin)
    except CoinNotFound:
        await query.message.edit_text('Монета не найдена ни на одной бирже')
        return

    text = (
        f'Лучшие цены, доступные сейчас\n'
        f'{make_message_for_best_price(best_prices)}'
    )
    await query.message.edit_text(text=text)


@dp.callback_query_handler(
    button_cb.filter(answer=button_find_deal),
    state='*')
async def callback_find_deal(
        query: CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)
    coin_name = callback_data['question']
    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await query.message.edit_text('Ошибка: Монета не найдена')
        return

    try:
        best_prices = Market.find_couple_for_best_deal(coin)
    except CoinNotFound:
        await query.message.edit_text(
            'Монета не найдена ни на одной бирже')
        return
    if not best_prices:
        await query.message.edit_text(
            'Сейчас нет хорошего варианта для сделки')
        return

    text = (
        f'Лучший вариант сделки, доступный сейчас\n\n'
        f'{make_message_for_best_price(best_prices)}'
    )
    await query.message.edit_text(text=text)


@dp.callback_query_handler(
    button_cb.filter(answer=button_delete),
    state='*')
async def callback_delete(
        query: CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)
    coin_name = callback_data['question']
    Coin.delete_coin(coin_name)
    await query.message.edit_text(
        text=f'Удалено: {coin_name}'
    )


@dp.callback_query_handler(
    button_cb.filter(answer=button_alter_name),
    state='*')
async def callback_alter_name(
        query: CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)
    coin_name = callback_data['question']
    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await query.message.edit_text('Ошибка: Монета не найдена')
        return

    text = f'<b>{coin.get_upper_name()}</b>\n'
    for market_name, alter_name in coin.alter_names.items():
        text += f'{market_name}: {alter_name} \n'
    text += '\nВыберете, к какому рынку вы хотите добавить имя для монеты'

    keybord = make_inline_keyboard(
        question=button_alter_name,
        answers=Market.get_market_names(),
        data=coin_name
    )
    await query.message.edit_text(
        text=text,
        reply_markup=keybord
    )


class CustomerState(StatesGroup):
    waiting_for_coin_name = State()


@dp.callback_query_handler(
    button_cb.filter(
        question=button_alter_name),
    state='*')
async def callback_choise_market(
        query: CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)
    await query.message.edit_reply_markup(reply_markup=None)

    coin_name = callback_data['data']
    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await query.message.edit_text('Ошибка: Монета не найдена')
        return

    market_name = callback_data['answer']
    await CustomerState.waiting_for_coin_name.set()
    await state.update_data(coin_name=coin_name)
    await state.update_data(market_name=market_name)
    await query.message.answer(
        f'Введите алтернативное имя {coin_name} для биржи {market_name}')


@dp.message_handler(
    lambda message: is_message_private(message),
    content_types=[ContentType.TEXT],
    state=CustomerState.waiting_for_coin_name)
async def new_name_for_coin(message: Message, state: FSMContext):
    log.info('new_name_for_coin from: %r', message.from_user.id)
    state_data = await state.get_data()
    coin_name = state_data['coin_name']
    market_name = state_data['market_name']

    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await message.answer('Ошибка: Монета не найдена')
        return

    market = Market.get_market_by_name(market_name)
    if not market:
        await message.answer('Ошибка: Биржа не найдена')
        return

    coin.put_new_name(name=message.text, market=market)
    await message.reply(
        f'Записано алтернативное имя {coin_name} для биржи {market_name}')
    await state.finish()


@dp.message_handler(
    lambda message: is_message_private(message),
    content_types=[ContentType.TEXT],
    state="*")
async def new_text(message: Message, state: FSMContext):
    log.info('new_coin_name from: %r', message.from_user.id)
    coin = Coin.get_coin_by_name(message.text)

    if not coin:
        coin = Coin.new_coin(message.text)
        text = f'Добавлена монета: <b>{coin.get_upper_name()}</b>\n'
    else:
        text = f'<b>{coin.get_upper_name()}</b>\n'

    keybord = make_inline_keyboard(
        question=coin.get_name(),
        answers=buttons_for_coin
    )
    await message.answer(
        text=text,
        reply_markup=keybord
    )


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False)
