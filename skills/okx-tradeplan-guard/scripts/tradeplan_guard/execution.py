"""Prepare an order for explicit user review. This module never sends orders."""

import hashlib
import json
import re
import shlex
import time
from decimal import Decimal

from .planner import make_plan


def preview(plan, builder_code, mode, profile, account_mode, now_ms=None):
    if not isinstance(builder_code, str) or not re.fullmatch(r'[A-Za-z0-9]{1,16}', builder_code):
        raise ValueError('发布者尚未配置有效 Builder Code；无法生成归因订单。')
    if mode not in ('demo', 'live'):
        raise ValueError('交易模式必须为 demo 或 live。')
    if not isinstance(profile, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', profile):
        raise ValueError('请使用明确的本地 CLI profile 名称（字母、数字、下划线、连字符）。')
    if str(account_mode) not in ('1', '2'):
        raise ValueError('首版仅支持账户模式 1/2 下的 cash 现货；请勿自动修改账户模式。')
    now = int(time.time() * 1000) if now_ms is None else now_ms
    if not isinstance(plan, dict) or plan.get('kind') != 'spot_buy_plan':
        raise ValueError('必须使用实时行情生成的现货买入计划。')
    snapshot = plan.get('snapshot')
    if not isinstance(snapshot, dict) or snapshot.get('source') != 'okx_public_api':
        raise ValueError('离线示例不能用于下单。')
    created, expires = plan.get('created_at_ms'), plan.get('expires_at_ms')
    if type(created) is not int or type(expires) is not int or not created <= now <= expires:
        raise ValueError('计划已过期或时间无效，请重新获取行情并生成计划。')
    # Both original arithmetic and current market-data freshness must still pass.
    original = make_plan(plan['snapshot'], plan['inputs'], now_ms=created)
    if original != plan:
        raise ValueError('计划内容被修改，请用原始参数重新生成并重新确认。')
    make_plan(plan['snapshot'], plan['inputs'], now_ms=now)
    intent = json.dumps({'plan': plan, 'mode': mode, 'profile': profile, 'code': builder_code},
                        sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    client_id = 'tpg' + hashlib.sha256(intent.encode()).hexdigest()[:24]
    argv = ['okx', '--profile', profile]
    argv.append('--live' if mode == 'live' else '--demo')
    argv += ['spot', 'place', '--instId', plan['symbol'], '--tdMode', 'cash',
             '--side', 'buy', '--ordType', 'limit', '--sz', plan['quantity'],
             '--px', format(Decimal(plan['inputs']['entry']), 'f'), '--clOrdId', client_id,
             '--aiBuilderCode', builder_code]
    return {'mode': mode, 'argv': argv, 'command': shlex.join(argv), 'clOrdId': client_id,
            'requires_user_confirmation': True, 'requires_account_preflight': True,
            'order_submitted': False, 'stop_is_order': False,
            'notice': '仅生成待审核命令。须核对 Global 站点、profile 模拟/实盘属性、余额、费率及限额；'
                      '用户确认后由官方 CLI 执行。止损价仅用于估算，本订单未附带止损。'}
