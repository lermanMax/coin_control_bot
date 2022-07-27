import logging

from services.market_base import Market, Coin
import services.api_config

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('api_test')

btc_coin = Coin(
    name='btc',
    alter_names={
        '1inch': 'wbtc'
    }
)


def test_all_markets():
    for market in Market.all_markets:
        try:
            market.get_cup(
                coin=btc_coin,
                base_coin=Market.usdt_coin,
                depth=10
            )
            log.info(f'get_cup() for {market.name} returned something')
        except Exception:
            log.error(f'get_cup() for {market.name} does not work')

        try:
            best_price = market.get_price(
                coin=btc_coin,
                base_coin=Market.usdt_coin
            )
            log.info((
                f'get_price() for {market.name} returned: '
                f'{best_price.best_ask.number}'))
        except Exception:
            log.error(f'get_price() for {market.name} does not work')

        print('------')


if __name__ == '__main__':
    test_all_markets()
