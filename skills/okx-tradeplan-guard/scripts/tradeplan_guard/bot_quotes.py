"""Fixed demonstration or public market quotes; never reads an account."""
import time
from .market import collect_snapshot


def quote(symbol, mode):
    if mode == 'public':
        return collect_snapshot(symbol)
    prices = {'BTC-USDT': ('80000', '79999.9', '0.1', '0.00001'),
              'ETH-USDT': ('3000', '2999.99', '0.01', '0.0001'),
              'SOL-USDT': ('150', '149.99', '0.01', '0.01')}
    if mode != 'demo' or symbol not in prices:
        raise ValueError('演示行情支持 BTC-USDT、ETH-USDT、SOL-USDT；成交始终是本地模拟。')
    ask, bid, tick, lot = prices[symbol]
    now = int(time.time() * 1000)
    return {'schema_version': 1, 'site': 'global', 'source': 'offline_fixture',
            'retrieved_at_ms': now,
            'instrument': {'instType': 'SPOT', 'instId': symbol, 'baseCcy': symbol.split('-')[0],
                           'quoteCcy': 'USDT', 'state': 'live', 'tickSz': tick, 'lotSz': lot, 'minSz': lot},
            'ticker': {'instType': 'SPOT', 'instId': symbol, 'ts': str(now), 'last': ask,
                       'bidPx': bid, 'askPx': ask, 'bidSz': '10', 'askSz': '10'},
            'notice': '固定虚构演示报价；时间仅用于本地模拟事件排序。'}
