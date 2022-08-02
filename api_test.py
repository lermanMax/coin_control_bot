import logging

from services.market_base import Market, Coin
import services.api_config

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger('api_test')

btc_coin = Coin(
    name='btc',
    alter_names={
        '1inch': 'wbtc',
        'kraken': 'XBT'
    }
)


def test_all_markets():
    for market in Market.all_markets:
        print('------')
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
                f'ask = {best_price.best_ask.number} '
                f'bid = {best_price.best_ask.number} '
            ))
        except Exception:
            log.error(f'get_price() for {market.name} does not work')
            continue

        if type(best_price.best_ask.number) == float:
            log.info('best_ask is float')
        else:
            log.error('best_ask is not float')
        
        if type(best_price.best_bid.number) == float:
            log.info('best_bid is float')
        else:
            log.error('best_bid is not float')
        
        if best_price.best_ask.number > best_price.best_bid.number:
            log.info('best_ask more then best_bid')
        else:
            log.error('best_bid more then best_ask')


if __name__ == '__main__':
    test_all_markets()
