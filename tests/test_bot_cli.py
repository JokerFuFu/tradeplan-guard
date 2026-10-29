import json, os, signal, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'bot.py'
SKILL=ROOT/'skills/okx-tradeplan-guard/scripts/bot.py'
class BotCLITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.db=self.home/'paper.db'
 def tearDown(self):self.tmp.cleanup()
 def call(self,*args,entry=ENTRY,db=True):
  command=[sys.executable,str(entry)]+(['--db',str(self.db)] if db else [])+list(args)
  return subprocess.run(command,cwd=self.home,capture_output=True,text=True,env={**os.environ,'XDG_DATA_HOME':str(self.home/'xdg')},timeout=15)
 def result(self,*args,**kwargs):
  r=self.call(*args,**kwargs);self.assertEqual(r.returncode,0,r.stderr);return json.loads(r.stdout)
 def create(self,**changes):
  config=self.result('sample');config.update(changes);p=self.home/'config.json';p.write_text(json.dumps(config));return self.result('create','--config',str(p))
 def test_sample_no_db_and_portable_standalone(self):
  c=self.result('sample',entry=SKILL,db=False);self.assertEqual(c['market_mode'],'demo');self.assertFalse((self.home/'xdg').exists());self.assertFalse(self.db.exists())
 def test_create_start_tick_pause_and_persistence(self):
  bot=self.create();self.assertEqual(bot['status'],'paused');self.assertEqual(self.result('list')[0]['id'],bot['id'])
  self.result('start','--id',bot['id']);s=self.result('run','--once');self.assertEqual(s['bots'][0]['run_count'],1);self.assertTrue(s['orders'][0]['paper'])
  self.result('pause','--id',bot['id']);self.result('tick');self.assertEqual(self.result('status','--id',bot['id'])['run_count'],1)
  self.result('stop','--id',bot['id']);self.assertNotEqual(self.call('start','--id',bot['id']).returncode,0)
 def test_price_trigger_and_records(self):
  b=self.create(type='price',trigger_price='1');self.result('start','--id',b['id']);self.result('tick');self.assertEqual(self.result('orders'),[]);self.assertTrue(self.result('events'))
 def test_bad_config_controlled(self):
  for body in ('null','['*2000,'{"name":NaN}','x'*65537):
   p=self.home/'bad.json';p.write_text(body);r=self.call('create','--config',str(p));self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)
 def test_invalid_db_path_controlled(self):
  self.db.mkdir();r=self.call('list');self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)
 def test_bad_ids_and_poll_are_controlled(self):
  self.assertEqual(self.call('pause','--id','missing').returncode,2)
  self.assertEqual(self.call('run','--once','--poll-seconds','0').returncode,2)
 def test_foreground_interrupt_preserves_strategy_state(self):
  bot=self.create();self.result('start','--id',bot['id'])
  process=subprocess.Popen([sys.executable,str(ENTRY),'--db',str(self.db),'run'],cwd=self.home,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   first=json.loads(process.stdout.readline());self.assertEqual(first['runner'],'started');self.assertEqual(first['mode'],'paper')
   process.send_signal(signal.SIGINT);out,err=process.communicate(timeout=10)
   self.assertEqual(process.returncode,0,err);self.assertIn('"runner": "stopped"',out)
   self.assertEqual(self.result('status','--id',bot['id'])['status'],'running')
  finally:
   if process.poll() is None:process.kill();process.communicate()
 def test_standalone_default_data_home(self):
  self.result('status',entry=SKILL,db=False);self.assertTrue((self.home/'xdg/tradeplan-guard/paper.sqlite3').is_file())
if __name__=='__main__':unittest.main()
