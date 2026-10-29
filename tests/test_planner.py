import copy
import sys
import unittest
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/okx-tradeplan-guard/scripts'))
from tradeplan_guard import planner

NOW = 1800000000000

def snapshot():
    return {'schema_version': 1, 'site': 'global', 'source': 'okx_public_api', 'retrieved_at_ms': NOW,
            'instrument': {'instId': 'BTC-USDT', 'instType': 'SPOT', 'state': 'live', 'baseCcy': 'BTC', 'quoteCcy': 'USDT', 'lotSz': '0.01', 'minSz': '0.01', 'tickSz': '0.01'},
            'ticker': {'instId': 'BTC-USDT', 'instType': 'SPOT', 'last': '10', 'bidPx': '9.99', 'askPx': '10.01', 'ts': str(NOW)}}

def inputs(**kw):
    d = dict(budget='100', max_loss='5', entry='10', stop='9', fee_bps='0', slippage_bps='0')
    d.update(kw)
    return d

class PlannerTests(unittest.TestCase):
    def test_hand_calculation_risk_bound(self):
        p = planner.make_plan(snapshot(), inputs(), NOW)
        self.assertEqual(p['quantity'], '5')
        self.assertEqual(p['estimated_cost'], '50')
        self.assertEqual(p['estimated_loss'], '5')
        self.assertFalse(p['stop_is_order'])
        self.assertEqual(planner.scenario(p, '12')['estimated_pnl'], '10')

    def test_both_sides_fees_slippage(self):
        p = planner.make_plan(snapshot(), inputs(fee_bps='100', slippage_bps='100'), NOW)
        # C=10.201, V=8.8209; floor((5/1.3801)/.01)*.01=3.62
        self.assertEqual(p['quantity'], '3.62')
        self.assertEqual(Decimal(p['estimated_cost']), Decimal('36.92762'))
        self.assertEqual(Decimal(p['estimated_loss']), Decimal('4.995962'))
        self.assertEqual(Decimal(planner.scenario(p, '12')['estimated_pnl']), Decimal('5.647924'))

    def test_budget_bound_and_minimum(self):
        p = planner.make_plan(snapshot(), inputs(budget='20', max_loss='10'), NOW)
        self.assertEqual(p['quantity'], '2')
        with self.assertRaises(ValueError):
            planner.make_plan(snapshot(), inputs(budget='0.001', max_loss='0.001'), NOW)

    def test_invalid_inputs(self):
        for value in ['NaN','Infinity','-Infinity','1e999999','1e-99999','-1','0', True, 1.2, None, '9'*100]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                planner.make_plan(snapshot(), inputs(budget=value), NOW)
        for kw in [dict(stop='10'),dict(stop='11'),dict(entry='10.001'),dict(stop='9.001'),dict(max_loss='101'),dict(fee_bps='10000'),dict(slippage_bps='-1')]:
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                planner.make_plan(snapshot(), inputs(**kw), NOW)

    def test_freshness_boundaries(self):
        for offset in [-30000,5000]:
            s=snapshot();s['ticker']['ts']=str(NOW+offset)
            planner.make_plan(s, inputs(), NOW)
        for offset in [-30001,5001]:
            s=snapshot();s['ticker']['ts']=str(NOW+offset)
            with self.assertRaises(ValueError): planner.make_plan(s,inputs(),NOW)

    def test_bad_instruments_and_quotes(self):
        changes=[('instrument','instType','SWAP'),('instrument','state','suspend'),('instrument','lotSz','0'),('instrument','minSz','NaN'),('instrument','tickSz','0'),('instrument','quoteCcy','USD'),('ticker','instId','ETH-USDT'),('ticker','bidPx','11'),('ticker','askPx','0'),('ticker','last',''),('ticker','ts',True)]
        for section,key,value in changes:
            s=snapshot();s[section][key]=value
            with self.subTest(change=(section,key,value)),self.assertRaises(ValueError): planner.make_plan(s,inputs(),NOW)
        for key,value in [('source','unknown'),('site','us'),('schema_version',True),('retrieved_at_ms',NOW+5001)]:
            s=snapshot();s[key]=value
            with self.assertRaises(ValueError): planner.make_plan(s,inputs(),NOW)

    def test_offline_demo_remains_illustrative(self):
        s=snapshot();s['source']='offline_fixture'
        p=planner.make_plan(s,inputs(),NOW)
        self.assertEqual(p['kind'],'illustrative_plan')
        self.assertEqual(p['snapshot']['source'],'offline_fixture')
        self.assertEqual(planner.scenario(p,'12')['kind'],'illustrative_scenario')
        self.assertFalse(planner.scenario(p,'12')['actual_trade'])

    def test_snapshots_are_copied(self):
        s=snapshot();i=inputs();p=planner.make_plan(s,i,NOW)
        s['ticker']['last']='20';i['budget']='200'
        self.assertEqual(p['snapshot']['ticker']['last'],'10')
        self.assertEqual(p['inputs']['budget'],'100')

    def test_scenario_rejects_tampering_and_invalid_exit(self):
        p=planner.make_plan(snapshot(),inputs(),NOW)
        for key,value in [('quantity','10'),('estimated_cost','0'),('expires_at_ms',NOW+999999),('kind','swap')]:
            edited=copy.deepcopy(p);edited[key]=value
            with self.assertRaises(ValueError): planner.scenario(edited,'12')
        for price in ['NaN','0','-1',2.0]:
            with self.assertRaises(ValueError): planner.scenario(p,price)

    def test_high_precision_quantity_never_exceeds_bounds(self):
        s=snapshot();s['instrument']['lotSz']='0.000000000000000001';s['instrument']['minSz']='0.000000000000000001'
        p=planner.make_plan(s,inputs(budget='100',max_loss='1',fee_bps='7.123456789',slippage_bps='3.456789'),NOW)
        self.assertLessEqual(Decimal(p['estimated_cost']),Decimal('100'))
        self.assertLessEqual(Decimal(p['estimated_loss']),Decimal('1'))

if __name__=='__main__': unittest.main()
