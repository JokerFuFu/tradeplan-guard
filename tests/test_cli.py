import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENTRY = Path(__file__).resolve().parents[1] / 'skills/okx-tradeplan-guard/scripts/tradeplan.py'


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ENTRY), *args], capture_output=True, text=True)

    def test_demo_is_labeled_and_needs_no_account(self):
        result = self.run_cli('demo')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['kind'], 'illustrative_plan')
        self.assertEqual(data['snapshot']['source'], 'offline_fixture')

    def test_publisher_code_is_not_faked(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = str(Path(tmp) / 'plan.json')
            made = self.run_cli('demo', '--out', dest)
            self.assertEqual(made.returncode, 0, made.stderr)
            result = self.run_cli('order-preview', '--plan', dest, '--profile', 'demo', '--account-mode', '1')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Builder Code', result.stderr)

    def test_does_not_overwrite_saved_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = str(Path(tmp) / 'plan.json')
            self.assertEqual(self.run_cli('demo', '--out', dest).returncode, 0)
            result = self.run_cli('demo', '--out', dest)
            self.assertNotEqual(result.returncode, 0)

    def test_historical_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = str(Path(tmp) / 'plan.json')
            self.run_cli('demo', '--out', dest)
            result = self.run_cli('scenario', '--plan', dest, '--exit-price', '110')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsInstance(json.loads(result.stdout), dict)

    def test_malformed_json_files_have_controlled_errors(self):
        for content in ('[' * 2000 + '0' + ']' * 2000, 'null', '[]'):
            with self.subTest(content=content[:20]), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'bad.json'
                path.write_text(content)
                result = self.run_cli('scenario', '--plan', str(path), '--exit-price', '110')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertIn('error', json.loads(result.stderr))


if __name__ == '__main__':
    unittest.main()
