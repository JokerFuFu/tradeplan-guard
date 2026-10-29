"""Decimal spot-buy sizing and hypothetical outcomes; never places orders."""
import copy
import re
import time
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction

_FIELDS = ('budget', 'max_loss', 'entry', 'stop', 'fee_bps', 'slippage_bps')
_NUMBER = re.compile(r'^[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]{1,3})?$')
_SYMBOL = re.compile(r'^[A-Z0-9]{1,20}-[A-Z0-9]{1,20}$')


def _decimal(value, name, allow_zero=False):
    if not isinstance(value, str) or len(value) > 80 or not _NUMBER.fullmatch(value):
        raise ValueError('%s must be a bounded positive decimal string' % name)
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid %s' % name) from exc
    parts = number.as_tuple()
    if not number.is_finite() or len(parts.digits) > 40 or not -24 <= parts.exponent <= 24 or number.adjusted() > 24:
        raise ValueError('%s exceeds numeric limits' % name)
    if number < 0 or (not allow_zero and number == 0):
        raise ValueError('%s must be positive' % name)
    return number


def _text(value):
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _milliseconds(value, name, string=False):
    if string:
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,16}', value):
            raise ValueError('%s must be an integer timestamp string' % name)
        value = int(value)
    if type(value) is not int or not 0 < value <= 9007199254740991:
        raise ValueError('%s must be positive integer milliseconds' % name)
    return value


def _snapshot(snapshot, now):
    if not isinstance(snapshot, dict) or type(snapshot.get('schema_version')) is not int or snapshot.get('schema_version') != 1:
        raise ValueError('Unsupported snapshot schema')
    if snapshot.get('site') != 'global' or snapshot.get('source') not in ('okx_public_api', 'offline_fixture'):
        raise ValueError('Only Global OKX public API or explicit offline fixture snapshots are supported')
    retrieved = _milliseconds(snapshot.get('retrieved_at_ms'), 'retrieved_at_ms')
    instrument, ticker = snapshot.get('instrument'), snapshot.get('ticker')
    if not isinstance(instrument, dict) or not isinstance(ticker, dict):
        raise ValueError('Instrument and ticker are required')
    symbol = instrument.get('instId')
    if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
        raise ValueError('Invalid spot symbol')
    if instrument.get('instType') != 'SPOT' or instrument.get('state') != 'live':
        raise ValueError('Instrument must be live SPOT')
    if ticker.get('instId') != symbol or ticker.get('instType') != 'SPOT':
        raise ValueError('Ticker instrument mismatch')
    base, quote = symbol.split('-')
    if instrument.get('baseCcy') != base or instrument.get('quoteCcy') != quote:
        raise ValueError('Instrument currency mismatch')
    lot = _decimal(instrument.get('lotSz'), 'lotSz')
    minimum = _decimal(instrument.get('minSz'), 'minSz')
    tick = _decimal(instrument.get('tickSz'), 'tickSz')
    _decimal(ticker.get('last'), 'last')
    bid = _decimal(ticker.get('bidPx'), 'bidPx')
    ask = _decimal(ticker.get('askPx'), 'askPx')
    if bid > ask:
        raise ValueError('Crossed bid/ask quote')
    ts = _milliseconds(ticker.get('ts'), 'ticker.ts', string=True)
    if any(not -5000 <= now - t <= 30000 for t in (ts, retrieved)):
        raise ValueError('Market snapshot is stale or in the future')
    return symbol, quote, lot, minimum, tick, min(now + 30000, ts + 30000, retrieved + 30000)


def make_plan(snapshot, inputs, now_ms=None):
    """Return a copy-owned, JSON-ready plan. All monetary inputs are strings.

    Quote age: at most 30 seconds; future tolerance: 5 seconds. Stop is only
    a scenario reference. Fees/slippage apply independently on both sides.
    """
    now = _milliseconds(int(time.time() * 1000) if now_ms is None else now_ms, 'now_ms')
    if not isinstance(inputs, dict) or set(inputs) != set(_FIELDS):
        raise ValueError('Exactly budget,max_loss,entry,stop,fee_bps,slippage_bps are required')
    with localcontext() as ctx:
        ctx.prec = 256
        symbol, quote, lot, minimum, tick, expiry = _snapshot(snapshot, now)
        v = {k: _decimal(inputs[k], k, k.endswith('_bps')) for k in _FIELDS}
        budget, risk, entry, stop = (v[k] for k in _FIELDS[:4])
        if stop >= entry or risk > budget:
            raise ValueError('Require entry > stop and max_loss <= budget')
        if entry % tick or stop % tick:
            raise ValueError('Entry and stop must align with tickSz')
        fee, slip = v['fee_bps'] / 10000, v['slippage_bps'] / 10000
        if fee >= 1 or slip >= 1:
            raise ValueError('Fee and slippage must be below 10000 bps per side')
        cost = entry * (1 + slip) * (1 + fee)
        proceeds = stop * (1 - slip) * (1 - fee)
        loss = cost - proceeds
        # Exact rational division avoids rounding an almost-full lot up.
        lots = min(Fraction(budget) / Fraction(cost * lot), Fraction(risk) / Fraction(loss * lot))
        quantity = Decimal(lots.numerator // lots.denominator) * lot
        if quantity <= 0 or quantity < minimum:
            raise ValueError('Budget/risk allows less than the instrument minimum quantity')
        estimated_cost, estimated_loss = quantity * cost, quantity * loss
        if estimated_cost > budget or estimated_loss > risk:
            raise ValueError('Sizing exceeded the budget or risk bound')
        return {'schema_version': 1, 'kind': ('illustrative_plan' if snapshot['source'] == 'offline_fixture' else 'spot_buy_plan'), 'symbol': symbol,
                'quote_currency': quote, 'quantity': _text(quantity),
                'estimated_cost': _text(estimated_cost), 'estimated_loss': _text(estimated_loss),
                'unit_cost': _text(cost), 'unit_stop_proceeds': _text(proceeds),
                'stop_is_order': False, 'inputs': copy.deepcopy(inputs),
                'snapshot': copy.deepcopy(snapshot), 'created_at_ms': now, 'expires_at_ms': expiry}


def scenario(plan, exit_price):
    """Historical what-if estimate: revalidate original math, not wall-clock age."""
    if not isinstance(plan, dict):
        raise ValueError('Plan must be an object')
    created = _milliseconds(plan.get('created_at_ms'), 'created_at_ms')
    rebuilt = make_plan(plan.get('snapshot'), plan.get('inputs'), created)
    if plan != rebuilt:
        raise ValueError('Plan was edited or is not a supported generated plan')
    with localcontext() as ctx:
        ctx.prec = 256
        price = _decimal(exit_price, 'exit_price')
        fee = _decimal(plan['inputs']['fee_bps'], 'fee_bps', True) / 10000
        slip = _decimal(plan['inputs']['slippage_bps'], 'slippage_bps', True) / 10000
        quantity = Decimal(plan['quantity'])
        net = quantity * price * (1 - slip) * (1 - fee)
        return {'kind': ('illustrative_scenario' if plan['kind'] == 'illustrative_plan' else 'hypothetical_scenario'), 'symbol': plan['symbol'],
                'quote_currency': plan['quote_currency'], 'exit_price': exit_price,
                'estimated_net_proceeds': _text(net),
                'estimated_pnl': _text(net - Decimal(plan['estimated_cost'])),
                'actual_trade': False, 'stop_is_order': False}
