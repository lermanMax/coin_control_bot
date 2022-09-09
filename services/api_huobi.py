from huobi.client.market import MarketClient

from .market_base import Market, Coin, Cup, CupEntry


class Huobi(Market):

    def __init__(self) -> None:
        super().__init__('Huobi')
        self.market_client = MarketClient()

    def make_name_for_market(self, coin: Coin, base_coin: Coin) -> str:
        return f'{coin.get_name(self)}{base_coin.get_name(self)}'

    def get_cup(self, coin: Coin, base_coin: Coin, depth: int = 1) -> Cup:
        symbol = self.make_name_for_market(coin, base_coin)
        depth = self.market_client.get_pricedepth(
            symbol=symbol,
            depth_size=depth,
            depth_type='step0')
        asks = [CupEntry(entry.price, entry.amount) for entry in depth.asks]
        bids = [CupEntry(entry.price, entry.amount) for entry in depth.bids]

        return Cup(asks, bids)

    def make_link_to_market(self, coin: Coin, base_coin: Coin) -> str:
        market_name = f'{coin.get_name(self)}_{base_coin.get_name(self)}'
        return f'https://www.huobi.com/exchange/{market_name}'
