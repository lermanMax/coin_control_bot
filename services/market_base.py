from __future__ import annotations
from typing import List, NamedTuple, Tuple
import logging
from datetime import datetime
from signal import signal, SIGALRM, alarm

from persistent import Persistent
from persistent.dict import PersistentDict
from ZODB import DB
import transaction

from .coin_db.db_config import DB_NAME

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('business_logic')


class CoinNotFound(Exception):
    pass

class MarketTimeOut(Exception):
    pass


class Coin(Persistent):
    con = DB(DB_NAME).open()
    _all_coins: List[Coin] = []

    @classmethod
    def get_coin_by_name(cls, name: str) -> Coin:
        for coin in cls._all_coins:
            if coin.get_name() == name.lower():
                return coin
        return None

    @classmethod
    def new_coin(cls, name: str) -> Coin:
        """Adding coin and saving it in memory.

        Args:
            name (str): _description_

        Returns:
            Coin: _description_
        """
        coin = cls.get_coin_by_name(name)
        if coin:
            return coin
        coin = Coin(name)

        if len(cls.con.root.coins) != 0:
            new_key = cls.con.root.coins.maxKey() + 1
        else:
            new_key = 1
        cls.con.root.coins[new_key] = coin
        transaction.commit()

        cls._all_coins.append(coin)
        return coin

    @classmethod
    def update_coins_from_db(cls):
        cls._all_coins = [coin for coin in cls.con.root.coins.values()]

    @classmethod
    def delete_coin(cls, name: str) -> None:
        for key, coin in cls.con.root.coins.items():
            if coin.get_name() == name.lower():
                cls.con.root.coins.pop(key)
                transaction.commit()
                break
        cls.update_coins_from_db()

    @classmethod
    def get_all_coins(cls) -> List[Coin]:
        return cls._all_coins

    def __init__(
            self, name: str,
            address: str = None,
            alter_names: dict = None):
        if alter_names is None:
            alter_names = {}

        self.name = name.lower()
        self.address = address
        self.alter_names = PersistentDict()

        for market_name, name in alter_names.items():
            self.alter_names[market_name] = name

    def get_upper_name(self, market: Market = None) -> str:
        name = self.get_name(market)
        return name.upper()

    def get_name(self, market: Market = None) -> int:
        if market:
            if market.name in self.alter_names:
                return self.alter_names[market.name]
        return self.name

    def get_address(self) -> str:
        return self.address

    def put_new_name(self, name: str, market: Market) -> None:
        """new alter specific name for market"""
        self.alter_names[market.name] = name.lower()
        transaction.commit()

    def put_new_address(self, address: str) -> None:
        """new alter specific name for market"""
        self.address = address
        transaction.commit()


class CupEntry(NamedTuple):
    """запись из биржевого стакана (depth of market)"""
    price: float
    amount: float


class Cup(NamedTuple):
    """запись из биржевого стакана (depth of market)
    asks - предложения по продажи
    bids - заявки на покупку
    """
    asks: List[CupEntry]
    bids: List[CupEntry]


class Price(NamedTuple):
    coin: Coin
    number: float
    base_coin: Coin
    market: Market


class BestPrice(NamedTuple):
    """цена на покупку и продажу
    bid - заявка на покупку
    ask - просят за продажу
    best_ask - лучшая цена за которую сейчас я могу купить
    best_bid - лучшая цена за которую сейчас я могу продать
    """
    best_ask: Price
    best_bid: Price


class Market:
    all_markets: List[Market] = []
    timeout_for_get = 3  # sec

    usd_coin = Coin('usd')
    usdt_coin = Coin('usdt')
    usdc_coin = Coin('usdc')
    base_coins = (usd_coin, usdt_coin, usdc_coin)

    @classmethod
    def get_market_names(cls) -> Tuple[str]:
        names = [market.name for market in cls.all_markets]
        return tuple(names)

    @classmethod
    def get_market_by_name(cls, name: str) -> Market:
        for market in cls.all_markets:
            if market.name == name:
                return market
        return None

    @classmethod
    def get_best_price(cls, coin: Coin) -> BestPrice:
        """Ищет лучшую цену среди всех маркетов

        Args:
            coin (Coin): монета, цена которой интересует

        Raises:
            CoinNotFound: монета ни где не найдена

        Returns:
            BestPrice: цена на покупку и продажу
        """
        log.info('started serching prices')
        best_ask: Price = None
        best_bid: Price = None
        for market in cls.all_markets:
            for base_coin in cls.base_coins:
                try:
                    price = market.get_price(coin, base_coin)
                except CoinNotFound:
                    continue
                except MarketTimeOut:
                    continue
                # print(
                #     f'best_ask:{price.best_ask.number}{price.best_ask.base_coin.get_upper_name()}{price.best_ask.market.name}'
                #     f'\nbest_bid:{price.best_bid.number}{price.best_bid.base_coin.get_upper_name()}{price.best_bid.market.name}')

                if not best_bid:
                    best_ask = price.best_ask
                    best_bid = price.best_bid
                    continue

                if price.best_ask.number < best_ask.number:
                    best_ask = price.best_ask
                if price.best_bid.number > best_bid.number:
                    best_bid = price.best_bid

        if not best_bid:
            raise CoinNotFound

        return BestPrice(best_ask=best_ask, best_bid=best_bid)

    @classmethod
    async def find_couple_for_best_deal(cls, coin: Coin) -> BestPrice:
        """ находит лучшую цену с достаточным объемом
        Raises:
            CoinNotFound: монета не существует ни где

        Returns:
            BestPrice: цена на покупку и продажу
            None: нет хорошего предложения
        """
        target_size = 500  # $
        minimal_profit = 0.02  # %

        prices = cls.get_best_price(coin)
        log.info('started price control')
        if not prices:
            return
        if ((prices.best_bid.number / prices.best_ask.number)
                < (1 + minimal_profit)):
            return

        asks = prices.best_ask.market.get_asks(
            coin=coin,
            base_coin=prices.best_ask.base_coin,
            depth=100
        )
        ask_size = 0
        ask_count = 0
        for entry in asks:
            target_count_coins = (target_size - ask_size)/entry.price
            if entry.amount < target_count_coins:
                ask_size += entry.price * entry.amount
                ask_count += entry.amount
            else:
                ask_size += entry.price * target_count_coins
                ask_count += target_count_coins
                break

        bids = prices.best_bid.market.get_bids(
            coin=coin,
            base_coin=prices.best_bid.base_coin,
            depth=100
        )
        bid_size = 0
        bid_count = ask_count
        for entry in bids:
            if entry.amount < bid_count:
                bid_size += entry.price * entry.amount
                bid_count -= entry.amount
            else:
                bid_size += entry.price * bid_count
                bid_count = 0
                break

        if (bid_size / ask_size) < (1 + minimal_profit):
            return

        return prices

    def __init__(self, name: str) -> None:
        self.name = name
        self.__class__.all_markets.append(self)

        self.date_info = datetime.today().date()
        self.info_non_existent_coins = []

    def handler_timeout(self, signum, frame):
        raise MarketTimeOut(f'time for {self.name} is out')

    def is_info_topical(self) -> bool:
        if self.date_info == datetime.today().date():
            return True
        else:
            self.date_info = datetime.today().date()
            self.info_non_existent_coins = []
            return False

    def coin_not_exist(self, coin: Coin, base_coin: Coin) -> bool:
        """если пара в списке несуществующих на этой бирже
        и информация акутальная (сегодняшняя)
        """
        pair_name = f'{coin.get_name(self)}{base_coin.get_name(self)}'
        if pair_name in self.info_non_existent_coins:
            if self.is_info_topical():
                return True
        return False

    def get_price(self, coin: Coin, base_coin: Coin) -> BestPrice:
        """выдает цену койна в базовой валюте

        Args:
            coin (Coin): монета, цена которой интересует
            base_coin (Coin): монета, в которой выражается первая монета

        Raises:
            CoinNotFound: ранок не найден на бирже

        Returns:
            BestPrice: цена на покупку и продажу
        """
        if self.coin_not_exist(coin, base_coin):
            raise CoinNotFound

        log.info(f'get price from: {self.name}')
        signal(SIGALRM, self.handler_timeout)
        alarm(self.timeout_for_get)
        try:
            cup = self.get_cup(coin, base_coin)
        except MarketTimeOut:
            raise MarketTimeOut
        except Exception:
            alarm(0)
            self.info_non_existent_coins.append(
                f'{coin.get_name(self)}{base_coin.get_name(self)}'
            )
            raise CoinNotFound
        alarm(0)

        if cup.asks:
            best_ask = cup.asks[0].price
        else:
            best_ask = 999_999_999_999.99

        if cup.bids:
            best_bid = cup.bids[0].price
        else:
            best_bid = 0.0

        return BestPrice(
            best_ask=Price(
                coin=coin, number=best_ask, base_coin=base_coin, market=self),
            best_bid=Price(
                coin=coin, number=best_bid, base_coin=base_coin, market=self)
        )

    def get_asks(
            self, coin: Coin,
            base_coin: Coin,
            depth: int = 10) -> List[CupEntry]:
        cup = self.get_cup(coin, base_coin, depth)
        return cup.asks

    def get_bids(
            self, coin: Coin,
            base_coin: Coin,
            depth: int = 10) -> List[CupEntry]:
        cup = self.get_cup(coin, base_coin, depth)
        return cup.bids

    # переопределить в потомках
    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        log.error('make_name_for_market from Market')
        return f'{coin.get_name()}_{base_coin.get_name()}'

    # переопределить в потомках
    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        log.error('get_cup from Market')
        return Cup(
            [CupEntry(0.0, 0.0), CupEntry(0.0, 0.0)],
            [CupEntry(0.0, 0.0), CupEntry(0.0, 0.0)]
        )

    # переопределить в потомках
    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        log.error('make_link_to_market from Market')
        return f'https://exemple.com/{coin.get_name()}_{base_coin.get_name()}'
