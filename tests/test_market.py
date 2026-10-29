import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/okx-tradeplan-guard/scripts'))
from tradeplan_guard import market

INSTRUMENT = dict(instId='BTC-USDT', instType='SPOT', state='live', baseCcy='BTC', quoteCcy='USDT', lotSz='0.00001', minSz='0.00001', tickSz='0.1')
TICKER = dict(instId='BTC-USDT', instType='SPOT', last='100', askPx='100.1', bidPx='99.9', askSz='1', bidSz='2', ts='1800000000000')

class Response(io.BytesIO):
    status = 200
    def __init__(self, body):
        super().__init__(body)

class MarketTests(unittest.TestCase):
    def collect(self, instrument=None, ticker=None, first=None):
        values = [first if first is not None else dict(code='0', data=[instrument or INSTRUMENT]), dict(code='0', data=[ticker or TICKER])]
        opener = MagicMock()
        opener.open.side_effect = [Response(json.dumps(v).encode()) for v in values]
        with patch.object(market, 'build_opener', return_value=opener), patch.object(market.time, 'time', return_value=1800000001):
            result = market.collect_snapshot('BTC-USDT')
        return result, opener

    def test_public_snapshot_keeps_exchange_timestamp_and_fixed_urls(self):
        result, opener = self.collect()
        self.assertEqual(result['source'], 'okx_public_api')
        self.assertEqual(result['site'], 'global')
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['retrieved_at_ms'], 1800000001000)
        self.assertEqual(result['ticker']['ts'], '1800000000000')
        self.assertEqual(result['instrument'], INSTRUMENT)
        urls = [c.args[0].full_url for c in opener.open.call_args_list]
        self.assertEqual(urls, ['https://www.okx.com/api/v5/public/instruments?instType=SPOT&instId=BTC-USDT', 'https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT'])
        self.assertTrue(all(c.kwargs['timeout'] == 12 for c in opener.open.call_args_list))

    def test_symbol_injection_and_derivatives_rejected_before_network(self):
        with patch.object(market, 'build_opener') as network:
            for symbol in ['btc-usdt', 'BTC-USDT-SWAP', 'BTC-USDT&x=y', '', None, 'A'*33+'-USDT']:
                with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                    market.collect_snapshot(symbol)
            network.assert_not_called()

    def test_error_empty_and_multirow_envelopes_rejected(self):
        for body in [dict(code='500',data=[]),dict(code='0',data=[]),dict(code='0',data=[INSTRUMENT,INSTRUMENT]),dict(code=0,data=[INSTRUMENT]), []]:
            with self.subTest(body=body), self.assertRaises(ValueError): self.collect(first=body)

    def test_inactive_wrong_type_and_wrong_identity_rejected(self):
        for field, value in [('state','preopen'),('instType','SWAP'),('instId','ETH-USDT'),('quoteCcy','USD'),('baseCcy','ETH')]:
            row = dict(INSTRUMENT, **{field:value})
            with self.subTest(field=field), self.assertRaises(ValueError): self.collect(instrument=row)

    def test_invalid_decimal_fields_rejected(self):
        for field in ['lotSz','minSz','tickSz']:
            for bad in ['0','-1','NaN','Infinity','1e99999',0.01,'']:
                with self.subTest(field=field,bad=bad), self.assertRaises(ValueError): self.collect(instrument=dict(INSTRUMENT, **{field:bad}))
        for field in ['last','bidPx','askPx','bidSz','askSz']:
            with self.subTest(field=field), self.assertRaises(ValueError): self.collect(ticker=dict(TICKER, **{field:'NaN'}))

    def test_ticker_identity_and_timestamp_required(self):
        for field,value in [('instId','ETH-USDT'),('instType','SWAP'),('ts',''),('ts',1800000000000),('ts','-1')]:
            with self.subTest(field=field), self.assertRaises(ValueError): self.collect(ticker=dict(TICKER, **{field:value}))

    def test_crossed_book_is_unusable(self):
        with self.assertRaises(ValueError): self.collect(ticker=dict(TICKER,bidPx='101'))

    def test_body_limit_and_malformed_json(self):
        for body in [b'x'*(1024*1024+1), b'not json', b'{"code":"0","code":"1","data":[]}']:
            opener=MagicMock(); opener.open.return_value=Response(body)
            with patch.object(market,'build_opener',return_value=opener), self.assertRaises(ValueError): market.collect_snapshot('BTC-USDT')

    def test_network_error_is_controlled(self):
        opener=MagicMock(); opener.open.side_effect=URLError('private diagnostic')
        with patch.object(market,'build_opener',return_value=opener), self.assertRaisesRegex(ValueError,'public market request failed'):
            market.collect_snapshot('BTC-USDT')

    def test_redirect_handler_blocks_redirect(self):
        from urllib.request import Request
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError):
            market._NoRedirect().redirect_request(Request('https://www.okx.com'), None, 302, 'redirect', {}, 'https://example.com')

if __name__ == '__main__': unittest.main()
