"""Durable, bounded local paper trading. Never calls an exchange order API."""
import copy
import json
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from tradeplan_guard.planner import make_plan, _decimal, _snapshot, _text


class Engine:
    def __init__(self, db_path, quote_provider, clock=None):
        self.clock = clock or (lambda: int(time.time()*1000))
        self.quote_provider = quote_provider
        self.lock = threading.RLock()
        if str(db_path) != ':memory:':
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), check_same_thread=False, timeout=15)
        self.db.execute('CREATE TABLE IF NOT EXISTS paper_state (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
        initial = dict(account=dict(mode='paper', currency='USDT', cash='10000'), plans=[], orders=[], bots=[], events=[])
        self.db.execute('INSERT OR IGNORE INTO paper_state VALUES(1,?)', (json.dumps(initial),))
        self.db.commit()

    def close(self):
        with self.lock:
            self.db.close()

    @contextmanager
    def _transaction(self):
        with self.lock, localcontext() as ctx:
            ctx.prec = 256
            self.db.execute('BEGIN IMMEDIATE')
            try:
                state = json.loads(self.db.execute('SELECT body FROM paper_state WHERE id=1').fetchone()[0])
                yield state
                self.db.execute('UPDATE paper_state SET body=? WHERE id=1', (json.dumps(state, allow_nan=False),))
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def _id(self):
        return uuid.uuid4().hex

    def _event(self, state, kind, message):
        state['events'].append(dict(id=self._id(), type=kind, message=message, created_at_ms=self.clock()))
        state['events'] = state['events'][-500:]

    def _available(self, state):
        reserved = sum((Decimal(o['reserved']) for o in state['orders'] if o['status']=='pending'), Decimal(0))
        return Decimal(state['account']['cash'])-reserved, reserved

    def state(self):
        with self._transaction() as s:
            result = copy.deepcopy(s)
            available, reserved = self._available(s)
            result['account'].update(reserved=_text(reserved), available_cash=_text(available))
            return result

    @staticmethod
    def _market(symbol, mode):
        if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9]{1,20}-USDT', symbol):
            raise ValueError('首版仅支持 USDT 计价现货。')
        if mode not in ('demo','public'):
            raise ValueError('行情模式必须是 demo 或 public；成交始终是本地模拟。')

    def _quote(self, symbol, mode, now):
        self._market(symbol, mode)
        q = self.quote_provider(symbol, mode)
        _snapshot(q, now)
        if q['instrument']['instId'] != symbol or q['source'] != ('offline_fixture' if mode=='demo' else 'okx_public_api'):
            raise ValueError('行情来源或交易对不匹配。')
        return q

    def create_plan(self, symbol, inputs, market_mode):
        now = self.clock()
        q = self._quote(symbol, market_mode, now)
        plan = make_plan(q, inputs, now_ms=now)
        row = dict(id=self._id(), plan=plan, market_mode=market_mode, created_at_ms=now, status='ready')
        with self._transaction() as s:
            s['plans'].append(row)
            s['plans'] = s['plans'][-200:]
            self._event(s,'plan_created','已生成本地模拟交易计划。')
        return copy.deepcopy(row)

    def confirm_plan(self, plan_id):
        with self._transaction() as s:
            for o in s['orders']:
                if o.get('plan_id') == plan_id:
                    return copy.deepcopy(o)
            row = next((p for p in s['plans'] if p['id']==plan_id), None)
            if row is None:
                raise ValueError('计划不存在。')
            p = row['plan']; now=self.clock()
            if now > p['expires_at_ms'] or now < p['created_at_ms']:
                raise ValueError('计划已过期，请重新生成。')
            if make_plan(p['snapshot'],p['inputs'],now_ms=p['created_at_ms']) != p:
                raise ValueError('计划校验失败。')
            reserve=Decimal(p['estimated_cost'])
            if reserve > self._available(s)[0]:
                raise ValueError('模拟可用余额不足。')
            if len(s['orders']) >= 1000:
                raise ValueError('模拟订单数量已达本地上限。')
            o=dict(id=self._id(),symbol=p['symbol'],status='pending',paper=True,mode='paper',quantity=p['quantity'],limit_price=p['inputs']['entry'],fill_price=None,cost=None,reserved=_text(reserve),market_mode=row['market_mode'],plan_id=plan_id,bot_id=None,created_at_ms=now,filled_at_ms=None,stop_is_order=False,fee_bps=p['inputs']['fee_bps'],slippage_bps=p['inputs']['slippage_bps'],initial_quote_ts=int(p['snapshot']['ticker']['ts']))
            s['orders'].append(o);row['status']='confirmed'
            self._event(s,'order_pending','已确认本地模拟限价买入，等待后续行情。')
            return copy.deepcopy(o)

    def create_bot(self, config):
        if not isinstance(config,dict):raise ValueError('机器人配置必须是对象。')
        c=copy.deepcopy(config)
        self._market(c.get('symbol'),c.get('market_mode'))
        if c.get('type') not in ('interval','price'):raise ValueError('不支持的机器人类型。')
        if not isinstance(c.get('name'),str) or not 1<=len(c['name'].strip())<=80:raise ValueError('名称长度应为 1–80。')
        for key in ('interval_seconds','max_runs'):
            if type(c.get(key)) is not int:raise ValueError('执行间隔和次数必须为整数。')
        if not 10<=c['interval_seconds']<=31536000 or not 1<=c['max_runs']<=1000:raise ValueError('执行间隔或次数超出范围。')
        per=_decimal(c.get('per_order_budget'),'per_order_budget');total=_decimal(c.get('total_budget'),'total_budget')
        if per>total:raise ValueError('单次预算不能大于总预算。')
        for key in ('fee_bps','slippage_bps'):
            if _decimal(c.get(key),key,True)>=10000:raise ValueError('费率必须低于 10000 bps。')
        if c['type']=='price':_decimal(c.get('trigger_price'),'trigger_price')
        now=self.clock()
        # Persist only the supported, bounded schema; never arbitrary client fields.
        fields=('name','symbol','type','market_mode','per_order_budget','total_budget','interval_seconds','max_runs','fee_bps','slippage_bps')
        b={key:c[key] for key in fields}
        b.update(trigger_price=c.get('trigger_price') if c['type']=='price' else None,id=self._id(),status='paused',spent='0',remaining_budget=c['total_budget'],run_count=0,next_run_at_ms=None,last_error=None,last_quote_ts=None,created_at_ms=now,updated_at_ms=now)
        with self._transaction() as s:
            if len(s['bots'])>=100:raise ValueError('本地机器人最多 100 个。')
            s['bots'].append(b);self._event(s,'bot_created','机器人已创建，当前暂停；所有成交均为本地模拟。')
        return copy.deepcopy(b)

    def set_bot_status(self, bot_id, status):
        if status not in ('running','paused','stopped'):raise ValueError('状态无效。')
        with self._transaction() as s:
            b=next((b for b in s['bots'] if b['id']==bot_id),None)
            if b is None:raise ValueError('机器人不存在。')
            if b['status'] in ('completed','stopped'):raise ValueError('已完成或已停止的机器人不能重新运行。')
            if b['status']==status:return copy.deepcopy(b)
            b['status']=status;b['updated_at_ms']=self.clock();b['last_error']=None
            b['next_run_at_ms']=self.clock() if status=='running' else None
            self._event(s,'bot_status','机器人状态变更：'+status)
            return copy.deepcopy(b)

    def _fill_pending(self,s,o,now):
        try:
            q=self._quote(o['symbol'],o['market_mode'],now)
            ts=int(q['ticker']['ts']);ask=Decimal(q['ticker']['askPx']);limit=Decimal(o['limit_price'])
            if ts<=max(o['created_at_ms'],o.get('initial_quote_ts',o['created_at_ms'])) or ask>limit:return
            lot=Decimal(q['instrument']['lotSz']);quantity=Decimal(o['quantity'])
            if quantity<Decimal(q['instrument']['minSz']) or quantity%lot:return
            price=min(limit,ask*(1+Decimal(o['slippage_bps'])/10000))
            cost=quantity*price*(1+Decimal(o['fee_bps'])/10000)
            if cost>Decimal(o['reserved']):raise ValueError('模拟订单成本超过预留预算。')
            s['account']['cash']=_text(Decimal(s['account']['cash'])-cost)
            o.update(status='filled',fill_price=_text(price),cost=_text(cost),reserved='0',filled_at_ms=now,quote_ts=ts)
            self._event(s,'paper_fill','本地模拟限价订单已成交；未发送至欧易。')
        except (ValueError,OSError):
            # Keep cash reserved and order pending; never guess a fill on missing data.
            return

    def _run_bot(self,s,b,now):
        if b['status']!='running' or now<b['next_run_at_ms']:return
        b['next_run_at_ms']=now+b['interval_seconds']*1000;b['updated_at_ms']=now
        try:
            q=self._quote(b['symbol'],b['market_mode'],now);ts=int(q['ticker']['ts'])
            if b['last_quote_ts'] is not None and ts<=b['last_quote_ts']:return
            b['last_quote_ts']=ts
            ask=Decimal(q['ticker']['askPx'])
            if b['type']=='price' and ask>Decimal(b['trigger_price']):return
            budget=min(Decimal(b['per_order_budget']),Decimal(b['total_budget'])-Decimal(b['spent']))
            available=self._available(s)[0]
            if budget>available:raise ValueError('模拟可用余额不足，机器人已暂停。')
            fee=Decimal(b['fee_bps'])/10000;slip=Decimal(b['slippage_bps'])/10000
            price=ask*(1+slip);unit=price*(1+fee);lot=Decimal(q['instrument']['lotSz'])
            ratio=Fraction(budget)/Fraction(unit*lot)
            qty=Decimal(ratio.numerator//ratio.denominator)*lot
            if qty<=0 or qty<Decimal(q['instrument']['minSz']):
                b['status']='completed';b['next_run_at_ms']=None;self._event(s,'bot_completed','剩余模拟预算低于最小数量，机器人已完成。');return
            if len(s['orders'])>=1000:raise ValueError('模拟订单数量已达本地上限。')
            cost=qty*unit
            if cost>budget or cost>available:raise ValueError('模拟预算校验失败。')
            o=dict(id=self._id(),symbol=b['symbol'],status='filled',paper=True,mode='paper',quantity=_text(qty),limit_price=None,fill_price=_text(price),cost=_text(cost),reserved='0',market_mode=b['market_mode'],plan_id=None,bot_id=b['id'],created_at_ms=now,filled_at_ms=now,quote_ts=ts,stop_is_order=False)
            s['orders'].append(o);s['account']['cash']=_text(Decimal(s['account']['cash'])-cost)
            b['spent']=_text(Decimal(b['spent'])+cost);b['remaining_budget']=_text(Decimal(b['total_budget'])-Decimal(b['spent']));b['run_count']+=1
            if b['run_count']>=b['max_runs'] or Decimal(b['remaining_budget'])<=0:
                b['status']='completed';b['next_run_at_ms']=None
            self._event(s,'bot_paper_fill','机器人完成一次本地模拟买入；未发送至欧易。')
        except (ValueError,OSError) as exc:
            b['status']='paused';b['next_run_at_ms']=None;b['last_error']='行情或模拟预算检查失败，请核对后手动恢复。'
            self._event(s,'bot_paused_error',b['last_error'])

    def tick(self):
        with self._transaction() as s:
            now=self.clock()
            for o in s['orders']:
                if o['status']=='pending':self._fill_pending(s,o,now)
            for b in s['bots']:
                self._run_bot(s,b,now)
        return self.state()
