#!/usr/bin/env python3
"""TradePlan Guard CLI. No order execution or credential collection."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from tradeplan_guard.execution import preview
from tradeplan_guard.market import collect_snapshot
from tradeplan_guard.planner import make_plan, scenario

SKILL_DIR = Path(__file__).resolve().parents[1]


def read_json(path):
    with open(path, 'rb') as stream:
        data = stream.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('JSON 文件超过 1 MiB。')
    try:
        result = json.loads(data)
    except RecursionError as exc:
        raise ValueError('JSON 嵌套过深。') from exc
    if not isinstance(result, dict):
        raise ValueError('JSON 顶层必须是对象。')
    return result


def doctor():
    try:
        version = subprocess.run(['okx', '--version'], capture_output=True, text=True, timeout=10)
        help_result = subprocess.run(['okx', 'spot', 'place', '--help'], capture_output=True,
                                     text=True, timeout=10)
    except FileNotFoundError:
        return {'ready': False, 'reason': '未安装官方 OKX CLI。', 'builder_configured': False}
    match = re.search(r'(?m)^(\d+)\.(\d+)\.(\d+)\b', version.stdout)
    version_ok = bool(match and tuple(map(int, match.groups())) >= (1, 4, 4))
    flags_ok = all(flag in help_result.stdout for flag in ('--aiBuilderCode', '--clOrdId', '--px'))
    code = read_json(SKILL_DIR / 'builder.json').get('builder_code')
    code_ok = isinstance(code, str) and bool(re.fullmatch(r'[A-Za-z0-9]{1,16}', code))
    return {'ready': version_ok and flags_ok and code_ok and version.returncode == 0 and help_result.returncode == 0,
            'cli_version': match.group(0) if match else None, 'cli_version_ok': version_ok,
            'attribution_flags_supported': flags_ok, 'builder_configured': code_ok,
            'account_verified': False, 'exchange_demo_verified': False,
            'notice': '仅检查本地版本、命令能力和 Code 格式；不代表账户授权、Code 激活或归因验证成功。'}


def demo():
    as_of = 1767225600000
    snapshot = {'schema_version': 1, 'site': 'global', 'source': 'offline_fixture',
                'retrieved_at_ms': as_of,
                'instrument': {'instType': 'SPOT', 'instId': 'DEMO-USDT', 'baseCcy': 'DEMO',
                               'quoteCcy': 'USDT', 'state': 'live', 'tickSz': '0.1',
                               'lotSz': '0.001', 'minSz': '0.001'},
                'ticker': {'instType': 'SPOT', 'instId': 'DEMO-USDT', 'ts': str(as_of),
                           'last': '100', 'bidPx': '99.9', 'askPx': '100.1'}}
    inputs = {'budget': '100', 'max_loss': '5', 'entry': '100', 'stop': '90',
              'fee_bps': '10', 'slippage_bps': '10'}
    return make_plan(snapshot, inputs, now_ms=as_of)


def main(argv=None):
    parser = argparse.ArgumentParser(description='交易前核对预算、行情和归因。无账户即可试用 demo。')
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('quote', 'plan'):
        item = sub.add_parser(action)
        item.add_argument('--site', choices=['global'], required=True)
        item.add_argument('--symbol', required=True)
        item.add_argument('--out')
        if action == 'plan':
            for field in ('budget', 'max-loss', 'entry', 'stop', 'fee-bps', 'slippage-bps'):
                item.add_argument('--' + field, required=True)
    sample = sub.add_parser('demo')
    sample.add_argument('--out')
    sim = sub.add_parser('scenario')
    sim.add_argument('--plan', required=True)
    sim.add_argument('--exit-price', required=True)
    order = sub.add_parser('order-preview')
    order.add_argument('--plan', required=True)
    order.add_argument('--profile', required=True)
    order.add_argument('--account-mode', choices=['1', '2'], required=True)
    order.add_argument('--mode', choices=['demo', 'live'], default='demo')
    sub.add_parser('doctor')
    args = parser.parse_args(argv)
    try:
        if args.action == 'demo':
            result = demo()
        elif args.action == 'quote':
            result = collect_snapshot(args.symbol)
        elif args.action == 'plan':
            fields = ('budget', 'max_loss', 'entry', 'stop', 'fee_bps', 'slippage_bps')
            result = make_plan(collect_snapshot(args.symbol), {key: getattr(args, key) for key in fields})
        elif args.action == 'scenario':
            result = scenario(read_json(args.plan), args.exit_price)
        elif args.action == 'order-preview':
            code = read_json(SKILL_DIR / 'builder.json').get('builder_code')
            result = preview(read_json(args.plan), code, args.mode, args.profile, args.account_mode)
        else:
            result = doctor()
        output = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        if getattr(args, 'out', None):
            with open(args.out, 'x', encoding='utf-8') as stream:
                stream.write(output)
        sys.stdout.write(output)
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
