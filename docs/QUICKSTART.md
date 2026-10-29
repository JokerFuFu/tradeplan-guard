# 快速开始

Python 3.9+，标准库即可。以下路径从项目根目录运行；安装为 Skill 后，把脚本路径替换为该 Skill 目录内的绝对路径，工作目录可以任意选择。

## 离线体验

```bash
python3 skills/okx-tradeplan-guard/scripts/tradeplan.py demo --out demo-plan.json
python3 skills/okx-tradeplan-guard/scripts/tradeplan.py scenario --plan demo-plan.json --exit-price 110
```

固定虚构数据，仅用于理解计算。`--out` 不覆盖已有文件；重复尝试请换一个文件名。情景计算不是 OKX 模拟盘，不生成成交或真实收益。

## 真实公共行情与计划

```bash
python3 skills/okx-tradeplan-guard/scripts/tradeplan.py quote --site global --symbol BTC-USDT
python3 skills/okx-tradeplan-guard/scripts/tradeplan.py plan --help
```

生成计划需自行决定并填写 `--budget`、`--max-loss`、`--entry`、`--stop`、`--fee-bps` 和 `--slippage-bps`，再指定 `--site global --symbol BTC-USDT --out my-plan.json`。这些数值不能由工具擅自替你确定。

- 预算和最大预期亏损以交易对计价币表示，BTC-USDT 即 USDT。
- 手续费与滑点均是每侧的基点数，10 bps = 0.1%；买入和退出各算一次。
- 入场价必须高于止损参考价，二者符合价格步进。
- 计划数量向下对齐数量步进，不能突破预算与预期亏损约束。
- 止损参考价不是已挂出的止损单，也不是实际损失上限保证。

计划必须使用 30 秒内的交易所行情；未来时间最多容忍 5 秒。网络错误、缺失数据和过期行情不会被替换为零或虚构数据。历史情景分析允许读取旧计划，但不能用它生成订单命令。

## 交易命令预览

当前 `builder.json` 的发布者 Code 为 null，因此此步骤会拒绝生成命令。拿到真实 Code 后由发布者配置，使用者不应填写测试 Code 或他人的 Code。

完成官方 CLI、Global 模拟盘 profile 配置及账户预检后，用真实计划和实际 profile 名称运行 `order-preview --plan my-plan.json --profile 你的模拟盘配置名 --account-mode 1 --mode demo`。`--account-mode` 必须来自账户实际读取结果，不能为通过检查而随意填写。

程序只输出待审核命令。交易执行由 [Skill](../skills/okx-tradeplan-guard/SKILL.md) 逐项完成预检和用户确认后调用官方 CLI。默认先做模拟盘验证；每笔实盘必须明确选择并确认。

## 常见结果

| 结果 | 含义 |
|---|---|
| `illustrative_plan` | 固定离线演示，不能下单 |
| `spot_buy_plan` | 基于公共行情计算的计划，不是成交 |
| `order_submitted: false` | 只生成命令，尚未提交订单 |
| `ready: false` | 本地能力或发布者配置尚未齐备 |
| 计划过期 | 重新获取行情、生成计划并核对变化 |

独立 Skill 随包提供策略机器人入口 `scripts/bot.py`。使用方法见 [机器人快速开始](BOT-QUICKSTART.md)，仅由前台运行器或单次 tick 检查策略；不安装系统定时任务，不代管密钥，也不自动重试交易所订单。
