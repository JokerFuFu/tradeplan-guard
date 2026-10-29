# TradePlan Guard · 现货交易计划助手

让 AI 在下单前，把数量、预算、手续费和订单内容算清楚。

TradePlan Guard 提供两个入口：可安装到 Coding Agent 的中文 Skill，以及可独立运行的策略机器人。它读取 OKX 公共现货行情，根据你给定的预算和风险参考值计算交易数量；机器人使用本地虚拟账户，Skill 保留官方 CLI 订单预览与逐笔确认流程。

**当前为 v0.3 申请原型。** 已移除网页助手；机器人通过命令行或 Skill 管理，无需浏览器。机器人尚未接入交易所执行。Skill 的发布者 Builder Code 仍为空，交易命令生成被阻止。尚未完成 OKX 模拟盘下单、成交、工作台归因或返佣验证。

## 30 秒体验

需要 Python 3.9+，无需第三方 Python 依赖、交易账号或密钥。在项目根目录查看机器人演示配置：

```bash
python3 bot.py sample
python3 bot.py --help
```

机器人创建后默认暂停，配置和启动流程见 [机器人快速开始](docs/BOT-QUICKSTART.md)。Mac 可双击 `start.command` 启动前台运行器，不会打开浏览器，也不会自动创建策略。

独立 Skill 的离线演示：

```bash
python3 skills/okx-tradeplan-guard/scripts/tradeplan.py demo
```

这是固定虚构 `DEMO-USDT` 数据的离线演示，输出标记为 `illustrative_plan`。它不会读取真实账户，也不能用于下单。

读取真实公共行情：

```bash
python3 skills/okx-tradeplan-guard/scripts/tradeplan.py quote --site global --symbol BTC-USDT
```

如果网络或站点不可用，程序会明确失败。Skill 的完整操作见 [快速开始](docs/QUICKSTART.md)。

## 能做什么

- **先算数量**：预算与预期亏损两种约束同时满足，计入双边手续费、滑点和最小数量要求。
- **再看情景**：比较指定退出价下的假设盈亏。止损参考价只参与估算，未自动附加止损订单。
- **本地模拟执行**：虚拟账户初始为 10,000 USDT；定时定额与到价机器人创建后暂停，启动后按每笔/总预算、间隔和次数上限运行，可暂停、停止并查询记录。
- **Skill 核对订单**：真实 Builder Code 配置后，生成带 `--aiBuilderCode` 的官方 CLI 现货限价买单命令。Skill 核对账户和余额，获得逐笔确认后才调用 CLI。

独立 Skill 支持 OKX Global、账户模式 1/2 的 cash 现货限价买入。凭证保留在使用者自己的官方 CLI 配置中，语言理解由加载 Skill 的宿主提供。机器人提供 BTC-USDT、ETH-USDT、SOL-USDT 的演示行情，也可读取 OKX 公共 USDT 现货行情；成交始终为本地模拟。项目根目录入口默认使用 `data/paper.sqlite3`；单独安装 Skill 的入口默认使用用户数据目录。用同一 `--db` 绝对路径可共享账本。只有前台运行器或单次 tick 运行时才检查策略。

本地模拟成交是虚拟账本记录；OKX 模拟盘成交需要交易所账户和订单回执；实盘成交涉及真实资金。当前机器人只实现第一种，不产生 Builder 归因或返佣。

## 安装与使用

把 `skills/okx-tradeplan-guard` 整个目录放入你的 Agent 技能目录，保留其中的脚本和 `builder.json`。例如 Codex 使用 `~/.codex/skills/okx-tradeplan-guard/`。不要只复制 `SKILL.md`。

在支持 Skill 的 Agent 中说：

> 使用 okx-tradeplan-guard，先演示如何按预算和止损参考价计算一笔现货计划。

可以从本仓库安装：

```bash
npx skills add JokerFuFu/tradeplan-guard
```

发布者流程见 [发布说明](docs/PUBLISHING.md)。

## Builder 返佣披露

启用后的订单会携带本项目发布者的 Builder Code。符合 OKX 规则的实际成交可能为发布者带来手续费分成；实际费用以用户账户费率和 OKX 系统为准。本项目不额外收取服务费。请按自己的交易需要使用，返佣不是增加交易频率的理由。

获批、命令生成、订单受理、成交、归因和返佣到账是不同状态。原型尚未取得这些交易与返佣结果。规则以 [OKX 官方说明](https://www.okx.com/zh-hans/help/ai-builder-program-commission-rules) 为准。

## 验证与许可

```bash
python3 -m unittest discover -s tests -v
python3 skills/okx-tradeplan-guard/scripts/tradeplan.py doctor
```

`doctor` 只检查 CLI 版本、命令参数及 Code 格式，不证明账户授权或返佣资格。当前验证记录见 [验证报告](docs/VALIDATION.md)。项目使用 [MIT License](LICENSE)。
