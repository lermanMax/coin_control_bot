from __future__ import annotations
import logging
import typing

from aiogram import Bot, Dispatcher, executor
from aiogram.types import Message, \
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery
from aiogram.utils import callback_data
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types.message import ContentType

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers import cron

# Import modules of this project
from config import ADMINS_TG, API_TOKEN
from services.market_base import BestPrice, Coin, CoinNotFound, \
    Market, MarketTimeOut
import services.api_config


# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('paperwork_bot')

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# Initialize scheduler
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# Structure of callback buttons
button_cb = callback_data.CallbackData(
    'btn', 'question', 'answer', 'data')

# Preparations
Coin.update_coins_from_db()
for coin in Coin.get_all_coins():
    if coin.get_address():
        try:
            oneinch = Market.get_market_by_name('1inch')
            oneinch._add_coin_to_tokenbook(coin)
        except Exception:
            pass


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
    for answer in answers:  # make a button for every answer
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


async def send_message_to_admins(
        text: str, disable_notification: bool = None):
    for admin_id in ADMINS_TG:
        await bot.send_message(
            chat_id=admin_id,
            text=text,
            disable_notification=disable_notification,
            disable_web_page_preview=True
        )


#  -------------------------------------------------------------- ФУНКЦИОНАЛ
async def user_from_white_list(message: Message) -> bool:
    if message.from_user.id in ADMINS_TG:
        return True
    else:
        log.info('message from NOT admin: %r', message.from_user.id)
        await message.answer('ауф-АУФ!')
        return False


@dp.message_handler(
    lambda message: is_message_private(message),
    commands=['start'], state="*")
async def start_command(message: Message, state: FSMContext):
    log.info('start command from: %r', message.from_user.id)
    if not await user_from_white_list(message):
        return
    scheduler.remove_all_jobs()
    trigger = cron.CronTrigger(
        minute='1-59', hour='0,1,8-23', timezone='Europe/Moscow')
    log.info('adding job')
    scheduler.add_job(
        func=check_all_coins,
        trigger=trigger
    )
    await message.answer(text='Запущен поиск сделок')


@dp.message_handler(
    lambda message: is_message_private(message),
    commands=['stop'], state="*")
async def stop_command(message: Message, state: FSMContext):
    log.info('stop command from: %r', message.from_user.id)
    if not await user_from_white_list(message):
        return
    scheduler.remove_all_jobs()
    await message.answer(text='Поиск сделок остановлен')


@dp.message_handler(
    lambda message: is_message_private(message),
    commands=['restart'], state="*")
async def restart_command(message: Message, state: FSMContext):
    log.info('restart command from: %r', message.from_user.id)
    if not await user_from_white_list(message):
        return
    scheduler.remove_all_jobs()
    Market.clear_cache()
    await message.answer('Сканер перезагружен')
    await start_command(message, state)


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
    log.info('all_coins_command from: %r', message.from_user.id)
    if not await user_from_white_list(message):
        return
    text = '<b>Все монеты:</b>\n'
    for coin in Coin.get_all_coins():
        text += f'{coin.get_upper_name()}\n'

    keyboard = make_keyboard_with_coins()

    await message.answer(text=text, reply_markup=keyboard)


@dp.message_handler(
    lambda message: is_message_private(message),
    commands=['clear'], state="*")
async def clear_command(message: Message, state: FSMContext):
    log.info('clear from: %r', message.from_user.id)
    if not await user_from_white_list(message):
        return
    await message.answer(text="remove", reply_markup=ReplyKeyboardRemove)


button_all_prices = 'Посмотреть цены'
button_best_prices = 'Лучшие цены'
button_find_deal = 'Найти пару для сделки'
button_alter_name = 'Добавить имя'
button_address = 'Добавить контракт'
button_delete = 'Удалить'
buttons_for_coin = [
    button_all_prices,
    button_best_prices,
    button_find_deal,
    button_alter_name,
    button_address,
    button_delete]


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
    for market in Market.all_markets:
        text_price = None
        time_is_out = False
        for base_coin in Market.base_coins:
            try:
                price = market.get_price(coin, base_coin).best_ask
                text_price = f'{price.number} {price.base_coin.get_name()}'
                break
            except CoinNotFound:
                continue
            except MarketTimeOut:
                time_is_out = True
                continue

        if not text_price:
            if time_is_out:
                text_price = '<i>timeout</i>'
            else:
                text_price = '<i>not_found</i>'
        text += f'{market.name} - {text_price}\n'
        await query.message.edit_text(
            text=text
        )


def make_message_for_best_price(best_prices: BestPrice) -> str:
    coin = best_prices.best_ask.coin

    percent = (
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
        f'{round(percent, 2)}%\n'
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
        best_prices = await Market.find_couple_for_best_deal(coin)
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

    keyboard = make_inline_keyboard(
        question=button_alter_name,
        answers=Market.get_market_names(),
        data=coin_name
    )
    await query.message.edit_text(
        text=text,
        reply_markup=keyboard
    )


class CustomerState(StatesGroup):
    waiting_for_coin_name = State()
    waiting_for_address = State()


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
    await query.message.edit_text(
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


@dp.callback_query_handler(
    button_cb.filter(answer=button_address),
    state='*')
async def callback_address(
        query: CallbackQuery,
        callback_data: typing.Dict[str, str],
        state: FSMContext):
    log.info('Got this callback data: %r', callback_data)
    coin_name = callback_data['question']
    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await query.message.edit_text('Ошибка: Монета не найдена')
        return

    await CustomerState.waiting_for_address.set()
    await state.update_data(coin_name=coin_name)
    await query.message.edit_text(
        f'Введите контракт(адрес) для {coin_name}')


@dp.message_handler(
    lambda message: is_message_private(message),
    content_types=[ContentType.TEXT],
    state=CustomerState.waiting_for_address)
async def new_address_for_coin(message: Message, state: FSMContext):
    log.info('new_name_for_coin from: %r', message.from_user.id)
    state_data = await state.get_data()
    coin_name = state_data['coin_name']

    coin = Coin.get_coin_by_name(coin_name)
    if not coin:
        await message.answer('Ошибка: Монета не найдена')
        return

    coin.put_new_address(address=message.text)
    # add_address_to_one_inch
    try:
        oneinch = Market.get_market_by_name('1inch')
        oneinch._add_coin_to_tokenbook(coin)
    except Exception:
        log.error(f'Added bad address for: { coin.get_upper_name() }')

    await message.reply(
        f'Записан контракт(адрес) для {coin_name}')
    await state.finish()


@dp.message_handler(
    lambda message: is_message_private(message),
    content_types=[ContentType.TEXT],
    state="*")
async def new_text(message: Message, state: FSMContext):
    log.info('new_coin_name from: %r', message.from_user.id)
    if not await user_from_white_list(message):
        return
    if len(message.text) > 17:
        await message.reply('Ошибка: слишком длинное название монеты')
        return
    coin = Coin.get_coin_by_name(message.text)

    if not coin:
        coin = Coin.new_coin(message.text)
        text = f'Добавлена монета: <b>{coin.get_upper_name()}</b>\n'
    else:
        text = f'<b>{coin.get_upper_name()}</b>\n\n'
        for market_name, alter_name in coin.alter_names.items():
            text += f'{market_name}: {alter_name} \n'
        if coin.get_address():
            text += f'Контракт: {coin.get_address()} \n'

    keyboard = make_inline_keyboard(
        question=coin.get_name(),
        answers=buttons_for_coin
    )
    await message.answer(
        text=text,
        reply_markup=keyboard
    )


#  ----------------------------------------------------- ДЕЙСТВИЯ ПО РАСПИСАНИЮ
next_coin_index = 0


async def check_all_coins():
    """начинает поиск сделки для всех монет"""
    log.info('check_all_coins is starting')
    global next_coin_index
    if next_coin_index >= len(Coin.get_all_coins()):
        next_coin_index = 0
    await find_couple_for_best_deal(
        coin=Coin.get_all_coins()[next_coin_index]
    )
    next_coin_index += 1

    log.info('check_all_coins ended')


async def find_couple_for_best_deal(coin: Coin):
    try:
        best_prices = await Market.find_couple_for_best_deal(coin)
    except CoinNotFound:
        await send_message_to_admins(
            f'Монета {coin.get_upper_name()} не найдена ни на одной бирже',
            disable_notification=True)
        return
    if not best_prices:
        log.info(f"{coin.get_upper_name()} - couple for deal wasn't found")
        return

    text = (
        f'Найден вариант для сделки\n\n'
        f'{make_message_for_best_price(best_prices)}'
    )
    await send_message_to_admins(text)


if __name__ == '__main__':
    scheduler.start()
    executor.start_polling(dp, skip_updates=False)
