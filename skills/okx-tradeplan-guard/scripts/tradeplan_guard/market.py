"""Public, credential-free OKX Global spot market snapshots.

Definitions: OKX V5 docs 0.3.0, Global /public/instruments and /market/ticker.
Quote freshness belongs to the planning stage; acquisition preserves exchange ts.
"""
import json
import re
import time
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

_BASE = 'https://www.okx.com'
_MAX_BODY = 1024 * 1024
_SYMBOL = re.compile(r'[A-Z0-9]{1,32}-[A-Z0-9]{1,32}\Z')
_NUMBER = re.compile(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z')


class MarketError(ValueError):
    """Unavailable or invalid public market data, never a zero-price substitute."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'Redirects are disabled', headers, fp)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MarketError('duplicate JSON field')
        result[key] = value
    return result


def _get(path, params):
    if path not in ('/api/v5/public/instruments', '/api/v5/market/ticker'):
        raise MarketError('unsupported public endpoint')
    request = Request(_BASE + path + '?' + urlencode(params), headers={
        'Accept': 'application/json', 'User-Agent': 'TradePlanGuard/0.1',
    }, method='GET')
    try:
        with build_opener(_NoRedirect()).open(request, timeout=12) as response:
            if response.status != 200:
                raise MarketError('public market HTTP response was not 200')
            body = response.read(_MAX_BODY + 1)
    except (URLError, OSError, TimeoutError) as exc:
        raise MarketError('public market request failed; check network and site availability') from exc
    if len(body) > _MAX_BODY:
        raise MarketError('public market response exceeds 1 MiB')
    try:
        payload = json.loads(body.decode('utf-8'), object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise MarketError('invalid public market JSON response') from exc
    if not isinstance(payload, dict) or payload.get('code') != '0':
        raise MarketError('OKX public market API did not return success')
    data = payload.get('data')
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise MarketError('expected exactly one public market record')
    return data[0]


def _positive(row, field):
    value = row.get(field)
    if not isinstance(value, str) or len(value) > 64 or not _NUMBER.fullmatch(value):
        raise MarketError('invalid decimal field: ' + field)
    result = Decimal(value)
    if result <= 0:
        raise MarketError('nonpositive decimal field: ' + field)
    return result


def collect_snapshot(symbol):
    """Return a validated raw SPOT instrument/ticker snapshot for Global.

    Does not read credentials, query accounts, trade, or silently change site.
    Stale timestamps remain visible for the planner to reject.
    """
    if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
        raise MarketError('use an uppercase spot symbol such as BTC-USDT')
    instrument = _get('/api/v5/public/instruments', {'instType': 'SPOT', 'instId': symbol})
    base, quote = symbol.split('-')
    expected = {'instId': symbol, 'instType': 'SPOT', 'state': 'live', 'baseCcy': base, 'quoteCcy': quote}
    if any(instrument.get(key) != value for key, value in expected.items()):
        raise MarketError('instrument is not the requested live spot market')
    for field in ('lotSz', 'minSz', 'tickSz'):
        _positive(instrument, field)
    ticker = _get('/api/v5/market/ticker', {'instId': symbol})
    if ticker.get('instId') != symbol or ticker.get('instType') != 'SPOT':
        raise MarketError('ticker does not match requested spot instrument')
    for field in ('last', 'bidPx', 'askPx', 'bidSz', 'askSz'):
        _positive(ticker, field)
    if Decimal(ticker['bidPx']) > Decimal(ticker['askPx']):
        raise MarketError('crossed book is not usable for this spot workflow')
    timestamp = ticker.get('ts')
    if not isinstance(timestamp, str) or not re.fullmatch(r'[0-9]{10,16}', timestamp) or int(timestamp) <= 0:
        raise MarketError('ticker has no valid exchange timestamp')
    return {
        'schema_version': 1, 'site': 'global', 'source': 'okx_public_api',
        'retrieved_at_ms': int(time.time() * 1000),
        'instrument': instrument, 'ticker': ticker,
    }
