import sys,tempfile,unittest,threading
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'skills/okx-tradeplan-guard/scripts'))
from tradeplan_guard.bot_engine import Engine
class EngineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.now=1800000000000;self.ask='100';self.quote_fails=False
  self.e=Engine(Path(self.tmp.name)/'state.db',self.quote,lambda:self.now)
 def tearDown(self):self.e.close();self.tmp.cleanup()
 def quote(self,symbol,mode):
  if self.quote_fails:raise ValueError('network unavailable')
  return {'schema_version':1,'site':'global','source':'offline_fixture' if mode=='demo' else 'okx_public_api','retrieved_at_ms':self.now,'instrument':{'instType':'SPOT','instId':symbol,'baseCcy':symbol.split('-')[0],'quoteCcy':'USDT','state':'live','tickSz':'0.1','lotSz':'0.001','minSz':'0.001'},'ticker':{'instType':'SPOT','instId':symbol,'last':self.ask,'askPx':self.ask,'bidPx':self.ask,'ts':str(self.now)}}
 def inputs(self,budget='100'):
  return dict(budget=budget,max_loss='5',entry='100',stop='90',fee_bps='10',slippage_bps='10')
 def config(self,**kw):
  d=dict(name='test',symbol='BTC-USDT',type='interval',market_mode='demo',per_order_budget='100',total_budget='200',interval_seconds=10,max_runs=2,trigger_price=None,fee_bps='10',slippage_bps='10');d.update(kw);return d
 def test_plan_reserve_later_fill_and_idempotent_confirm(self):
  p=self.e.create_plan('BTC-USDT',self.inputs(),'demo');o=self.e.confirm_plan(p['id'])
  self.assertEqual(o['status'],'pending');self.assertGreater(Decimal(self.e.state()['account']['reserved']),0)
  self.assertEqual(self.e.confirm_plan(p['id'])['id'],o['id']);self.e.tick();self.assertEqual(self.e.state()['orders'][0]['status'],'pending')
  self.now+=1000;self.e.tick();s=self.e.state();self.assertEqual(s['orders'][0]['status'],'filled');self.assertEqual(s['account']['reserved'],'0');self.assertLessEqual(Decimal(s['orders'][0]['fill_price']),Decimal('100'))
  cash=s['account']['cash'];self.e.tick();self.assertEqual(cash,self.e.state()['account']['cash'])
 def test_expired_plan_and_reservation_limit(self):
  p=self.e.create_plan('BTC-USDT',self.inputs(),'demo');self.now+=31000
  with self.assertRaises(ValueError):self.e.confirm_plan(p['id'])
  v=self.inputs('100000');v.update(max_loss='100000',stop='99.9')
  p=self.e.create_plan('BTC-USDT',v,'demo')
  with self.assertRaises(ValueError):self.e.confirm_plan(p['id'])
 def test_bot_pause_budget_maxruns_and_persistence(self):
  b=self.e.create_bot(self.config());self.e.tick();self.assertEqual(self.e.state()['orders'],[])
  self.e.set_bot_status(b['id'],'running');self.e.tick();self.e.tick();self.assertEqual(self.e.state()['bots'][0]['run_count'],1)
  self.e.set_bot_status(b['id'],'paused');self.now+=20000;self.e.tick();self.assertEqual(self.e.state()['bots'][0]['run_count'],1)
  self.e.set_bot_status(b['id'],'running');self.e.tick();b=self.e.state()['bots'][0];self.assertEqual(b['status'],'completed');self.assertEqual(b['run_count'],2);self.assertLessEqual(Decimal(b['spent']),200)
  self.e.close();self.e=Engine(Path(self.tmp.name)/'state.db',self.quote,lambda:self.now);self.assertEqual(self.e.state()['bots'][0]['run_count'],2)
 def test_bot_price_condition_error_and_no_catchup(self):
  b=self.e.create_bot(self.config(type='price',trigger_price='90',max_runs=10,total_budget='1000'));self.e.set_bot_status(b['id'],'running');self.e.tick();self.assertEqual(self.e.state()['orders'],[])
  self.now+=10000;self.ask='89';self.e.tick();self.assertEqual(self.e.state()['bots'][0]['run_count'],1)
  self.now+=1000000;self.e.tick();self.assertEqual(self.e.state()['bots'][0]['run_count'],2)
  self.now+=10000;self.quote_fails=True;self.e.tick();self.assertEqual(self.e.state()['bots'][0]['status'],'paused')
 def test_preexisting_future_quote_cannot_fill_pending(self):
  original=self.quote
  def future(symbol,mode):
   q=original(symbol,mode);q['ticker']['ts']=str(self.now+3000);return q
  self.e.quote_provider=future
  p=self.e.create_plan('BTC-USDT',self.inputs(),'demo');self.e.confirm_plan(p['id']);self.e.tick()
  self.assertEqual(self.e.state()['orders'][0]['status'],'pending')
 def test_invalid_config(self):
  for kw in ({'per_order_budget':'NaN'},{'total_budget':'Infinity'},{'max_runs':True},{'interval_seconds':9},{'symbol':'BTC-USD'},{'market_mode':'live'},{'fee_bps':'10000'}):
   with self.subTest(kw=kw),self.assertRaises(ValueError):self.e.create_bot(self.config(**kw))
 def test_concurrent_tick_does_not_duplicate(self):
  b=self.e.create_bot(self.config());self.e.set_bot_status(b['id'],'running')
  threads=[threading.Thread(target=self.e.tick) for _ in range(5)]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertEqual(self.e.state()['bots'][0]['run_count'],1)
 def test_pending_quote_error_keeps_reservation_and_no_fill(self):
  p=self.e.create_plan('BTC-USDT',self.inputs(),'demo');self.e.confirm_plan(p['id']);self.now+=1000;self.quote_fails=True;self.e.tick();self.assertEqual(self.e.state()['orders'][0]['status'],'pending')
if __name__=='__main__':unittest.main()
