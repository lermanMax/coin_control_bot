from __future__ import annotations
from typing import List, NamedTuple, Tuple
import logging

from persistent import Persistent
from persistent.dict import PersistentDict
from ZODB import DB
import transaction

from .coin_db.db_config import DB_NAME

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('bisness_logic')


class CoinNotFound(Exception):
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

    def __init__(self, name: str):
        self.name = name.lower()
        self.alter_names = PersistentDict()

    def get_upper_name(self, market: Market = None) -> str:
        name = self.get_name(market)
        return name.upper()

    def get_name(self, market: Market = None) -> int:
        if market:
            if market.name in self.alter_names:
                return self.alter_names[market.name]
        return self.name

    def put_new_name(self, name: str, market: Market) -> None:
        """new alter spicific name for market"""
        self.alter_names[market.name] = name.lower()
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

    usd_coin = Coin('usd')
    usdt_coin = Coin('usdt')
    base_coins = (usd_coin, usdt_coin)

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

    def __init__(self, name: str) -> None:
        self.name = name
        self.__class__.all_markets.append(self)

    def get_price(self, coin: Coin, base_coin: Coin = None) -> BestPrice:
        """выдает цену койна в базовой валюте

        Args:
            coin (Coin): монета, цена которой интересует
            base_coin (Coin): монета, в которой выражается первая монета

        Raises:
            CoinNotFound: ранок не найден на бирже

        Returns:
            BestPrice: цена на покупку и продажу
        """
        if not base_coin:
            base_coin = self.usdt_coin

        try:
            cup = self.get_cup(coin, base_coin)
        except Exception:
            raise CoinNotFound

        if cup.asks:
            best_ask = cup.asks[0].price
        else:
            best_ask = 999_999_999_999.99

        if cup.bids:
            best_bid = cup.bids[0].price
        else:
            best_bid = 0.0

        return BestPrice(
            best_ask=Price(coin=coin, number=best_ask, base_coin=base_coin),
            best_bid=Price(coin=coin, number=best_bid, base_coin=base_coin)
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
