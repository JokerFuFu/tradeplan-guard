import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/okx-tradeplan-guard/scripts'))
from tradeplan_guard.execution import preview
from tradeplan_guard.planner import make_plan


def example(now):
    snapshot = {'schema_version': 1, 'site': 'global', 'source': 'okx_public_api',
                'retrieved_at_ms': now,
                'instrument': {'instType': 'SPOT', 'instId': 'BTC-USDT', 'baseCcy': 'BTC',
                               'quoteCcy': 'USDT', 'state': 'live', 'tickSz': '0.1',
                               'lotSz': '0.001', 'minSz': '0.001'},
                'ticker': {'instType': 'SPOT', 'instId': 'BTC-USDT', 'ts': str(now),
                           'last': '100', 'bidPx': '99.9', 'askPx': '100.1'}}
    inputs = {'budget': '100', 'max_loss': '5', 'entry': '100', 'stop': '90',
              'fee_bps': '10', 'slippage_bps': '10'}
    return make_plan(snapshot, inputs, now_ms=now)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.now = int(time.time() * 1000)
        self.plan = example(self.now)

    def call(self, **changes):
        args = dict(plan=self.plan, builder_code='TestCode1', mode='demo',
                    profile='demo', account_mode='1', now_ms=self.now)
        args.update(changes)
        return preview(**args)

    def test_exact_limit_order_and_attribution(self):
        result = self.call()
        argv = result['argv']
        self.assertEqual(argv[:6], ['okx', '--profile', 'demo', '--demo', 'spot', 'place'])
        self.assertEqual(argv[argv.index('--aiBuilderCode') + 1], 'TestCode1')
        self.assertEqual(argv[argv.index('--sz') + 1], self.plan['quantity'])
        self.assertEqual(argv[argv.index('--ordType') + 1], 'limit')
        self.assertNotIn('--live', argv)
        self.assertTrue(result['requires_user_confirmation'])
        self.assertFalse(result['order_submitted'])
        self.assertEqual(result['clOrdId'], self.call()['clOrdId'])

    def test_live_is_explicit_and_separate(self):
        self.assertIn('--live', self.call(mode='live', profile='live')['argv'])

    def test_scientific_input_becomes_plain_cli_price(self):
        self.plan['inputs']['entry'] = '1e2'
        self.plan = make_plan(self.plan['snapshot'], self.plan['inputs'], now_ms=self.now)
        argv = self.call()['argv']
        self.assertEqual(argv[argv.index('--px') + 1], '100')

    def test_invalid_or_missing_code(self):
        for value in (None, '', 'x' * 17, 'code;echo X', 'ABC_1'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.call(builder_code=value)

    def test_no_profile_shell_injection_or_cross_account_mode(self):
        for value in ('x;echo bad', '', '../key'):
            with self.assertRaises(ValueError):
                self.call(profile=value)
        for value in ('3', '4', 'unknown'):
            with self.assertRaises(ValueError):
                self.call(account_mode=value)

    def test_tampered_quantity_is_rejected(self):
        self.plan['quantity'] = '1000000'
        with self.assertRaises(ValueError):
            self.call()

    def test_stale_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            self.call(now_ms=self.now + 31000)

    def test_offline_plan_cannot_generate_order(self):
        self.plan['snapshot']['source'] = 'offline_fixture'
        with self.assertRaises(ValueError):
            self.call()

    def test_null_snapshot_is_controlled_error(self):
        self.plan['snapshot'] = None
        with self.assertRaises(ValueError):
            self.call()


if __name__ == '__main__':
    unittest.main()
