# 策略机器人快速开始

Python 3.9+，标准库即可，无需浏览器、模型密钥或交易账号。当前机器人只使用本地虚拟资金，不发送欧易订单，也不产生返佣。

## 先选定账本

在项目根目录使用 `python3 bot.py`，默认账本为项目内 `data/paper.sqlite3`。单独安装 Skill 后，入口为该 Skill 下的 `scripts/bot.py`，默认账本为 `$XDG_DATA_HOME/tradeplan-guard/paper.sqlite3`；未设置 `XDG_DATA_HOME` 时使用 `~/.local/share/tradeplan-guard/paper.sqlite3`。

建议首次使用时确定一个账本绝对路径，之后各命令都传相同的 `--db`。该参数放在子命令之前；这样换工作目录或换入口也不会误用另一份虚拟账户。新账本初始为 10,000 虚拟 USDT。不要删除已有账本来重置结果。

## 创建暂停策略

以下在项目根目录运行，演示配置只是固定样例：

```bash
python3 bot.py sample > sample-bot.json
python3 bot.py --db data/paper.sqlite3 create --config sample-bot.json
python3 bot.py --db data/paper.sqlite3 list
```

`sample` 不创建账本。重定向前确认 `sample-bot.json` 不存在，避免覆盖自己的文件。检查或修改配置后再 create；创建结果包含策略 `id`，初始状态为 `paused`。

| 配置 | 含义 |
|---|---|
| `type` | `interval` 定时定额，或 `price` 到价买入 |
| `market_mode` | `demo` 固定演示行情，或 `public` OKX 公开行情；成交均为本地模拟 |
| `per_order_budget` / `total_budget` | 每笔与总预算，USDT 字符串 |
| `interval_seconds` / `max_runs` | 检查间隔和最多执行次数；间隔至少 10 秒 |
| `trigger_price` | 到价策略必填的十进制字符串；卖一价不高于此价才模拟买入 |
| `fee_bps` / `slippage_bps` | 每侧手续费和滑点假设；10 bps = 0.1% |

演示行情支持 BTC-USDT、ETH-USDT、SOL-USDT；公共行情支持程序校验通过的 OKX Global USDT 现货。到价条件持续满足时，可按间隔重复模拟买入，直到预算或次数限制生效。

## 启动、检查和暂停

将下面的 `策略ID` 替换为 create 返回的真实 `id`，核对具体策略后执行：

```bash
python3 bot.py --db data/paper.sqlite3 start --id 策略ID
python3 bot.py --db data/paper.sqlite3 run --once
python3 bot.py --db data/paper.sqlite3 status --id 策略ID
python3 bot.py --db data/paper.sqlite3 pause --id 策略ID
python3 bot.py --db data/paper.sqlite3 orders
python3 bot.py --db data/paper.sqlite3 events
```

`start` 只改变策略状态。`run --once` 或 `tick` 才检查一轮；`run` 会前台持续检查：

```bash
python3 bot.py --db data/paper.sqlite3 run --poll-seconds 2
```

Mac 双击 `start.command` 启动项目默认账本的前台运行器，不打开浏览器、不创建策略、不安装系统定时任务。默认暂停的策略不会因此启动。按 `Ctrl+C` 退出运行器，或在另一个终端用 `pause` 暂停某条策略。`stop --id 策略ID` 将其终止；终止或已完成的策略不能恢复。

关闭运行器后不执行。策略状态和记录保留，重启时原来运行中的策略会继续检查，不补跑停机期间错过的每轮；如不希望重启后执行，退出前先暂停策略。行情或模拟余额检查失败时策略暂停，需核对后手动恢复。

## 与 Skill 一起使用

可以让 AI 助手按你的实际规则整理配置，创建为暂停状态，展示预算、次数和行情来源，再按你的明确指令启动、暂停或查询。仅要求演示时使用样例，不把样例预算默认为你的交易意图。

Skill 的交易计划和官方 CLI 命令预览仍见 [快速开始](QUICKSTART.md)。机器人虚拟账本与欧易账户互不相通；拿到 Builder Code 不会自动把机器人变成实盘程序。
