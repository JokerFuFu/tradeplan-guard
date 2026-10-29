#!/usr/bin/env python3
"""Standalone, foreground paper strategy runner. No exchange order capability."""
import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from tradeplan_guard.bot_engine import Engine
from tradeplan_guard.bot_quotes import quote


def sample():
    return dict(name='定额买入演示',symbol='BTC-USDT',type='interval',market_mode='demo',
                per_order_budget='20',total_budget='100',interval_seconds=60,max_runs=5,
                trigger_price=None,fee_bps='10',slippage_bps='10')


def read_config(path):
    with open(path, 'rb') as f:
        data=f.read(65537)
    if len(data)>65536:
        raise ValueError('策略配置不得超过 64 KiB。')
    def constant(_):
        raise ValueError('配置含非法数值。')
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('配置包含重复字段。')
            result[key]=value
        return result
    try:
        config=json.loads(data,parse_constant=constant,object_pairs_hook=unique)
    except RecursionError as exc:
        raise ValueError('策略配置嵌套过深。') from exc
    if not isinstance(config,dict):raise ValueError('策略配置必须为 JSON 对象。')
    return config


def emit(value):
    print(json.dumps(value,ensure_ascii=False,allow_nan=False),flush=True)


def default_database():
    base=os.environ.get('XDG_DATA_HOME')
    path=Path(base).expanduser() if base else Path.home()/'.local/share'
    if not path.is_absolute():
        path=Path.home()/'.local/share'
    return path/'tradeplan-guard/paper.sqlite3'


def main(argv=None, default_db=None):
    parser=argparse.ArgumentParser(description='本地模拟策略机器人，不连接交易账户、不产生返佣。')
    parser.add_argument('--db',default=str(default_db or default_database()),help='持久化虚拟账本路径，放在子命令之前')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('sample',help='输出可保存的演示配置，不创建账本')
    create=sub.add_parser('create',help='创建暂停的策略')
    create.add_argument('--config',required=True)
    sub.add_parser('list',help='列出所有策略')
    status=sub.add_parser('status',help='查看账本或指定策略')
    status.add_argument('--id')
    for name in ('start','pause','stop'):
        p=sub.add_parser(name);p.add_argument('--id',required=True)
    for name in ('orders','events','tick'):
        sub.add_parser(name)
    run=sub.add_parser('run',help='前台持续处理运行中的策略；Ctrl+C 停止进程')
    run.add_argument('--once',action='store_true')
    run.add_argument('--poll-seconds',type=int,choices=range(2,61),default=2,metavar='2..60')
    args=parser.parse_args(argv)
    engine=None
    try:
        if args.command=='sample':
            emit(sample());return 0
        config=read_config(args.config) if args.command=='create' else None
        engine=Engine(Path(args.db).expanduser(),quote)
        if args.command=='create':result=engine.create_bot(config)
        elif args.command=='list':result=engine.state()['bots']
        elif args.command=='status':
            result=engine.state()
            if args.id:
                result=next((b for b in result['bots'] if b['id']==args.id),None)
                if result is None:raise ValueError('策略不存在。')
        elif args.command in ('start','pause','stop'):
            result=engine.set_bot_status(args.id,{'start':'running','pause':'paused','stop':'stopped'}[args.command])
        elif args.command in ('orders','events'):result=engine.state()[args.command]
        elif args.command=='tick' or args.once:
            result=engine.tick()
        else:
            seen={e['id'] for e in engine.state()['events']}
            emit({'runner':'started','mode':'paper','poll_seconds':args.poll_seconds,
                  'notice':'仅处理本地模拟策略。Ctrl+C 停止进程；策略状态保留，重启会恢复运行中的策略。'})
            try:
                while True:
                    state=engine.tick()
                    for event in state['events']:
                        if event['id'] not in seen:emit(event)
                    seen={e['id'] for e in state['events']}
                    time.sleep(args.poll_seconds)
            except KeyboardInterrupt:
                emit({'runner':'stopped','mode':'paper','strategy_states_preserved':True})
            return 0
        emit(result);return 0
    except (ValueError,OSError,sqlite3.Error,TypeError,KeyError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2
    finally:
        if engine is not None:engine.close()


if __name__=='__main__':
    sys.exit(main())
