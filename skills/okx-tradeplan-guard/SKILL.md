---
name: okx-tradeplan-guard
description: 用 OKX Global 公共现货行情计算预算和风险约束下的限价买入计划、退出价情景，并为用户逐笔确认后的官方 CLI 订单准备发布者 Builder 归因。适用于现货交易前核对及本地模拟策略机器人的创建、运行、暂停和查询；不用于合约、实盘自动调仓或托管交易。
---

# TradePlan Guard

## 本地入口与当前状态

本文件所在目录为 Skill 根目录。定位该目录后，使用其中 `scripts/tradeplan.py` 的绝对路径运行 Python 3.9+；不要假定用户当前目录就是项目目录。所有支持代码与 `builder.json` 随 Skill 一同安装。

本 Skill 随包提供独立机器人入口 `scripts/bot.py`，无需网页服务。语言理解由当前宿主 Agent 提供，无需另行配置模型服务密钥。机器人使用 SQLite 虚拟账户，不调用本 Skill 的交易所下单流程，不是 OKX 模拟盘，也不产生 Builder 返佣。

当前原型的 `builder.json` 中 Code 为 null，交易命令生成会停止。仍可使用 demo、quote、plan、scenario。不要编造 Code、采用示例 Code、修改检查绕过阻断，或声称原型已取得成交和返佣。

先运行 `python3 脚本绝对路径 demo` 可以展示固定虚构数据；输出 `illustrative_plan` 不能当成实时行情、OKX 模拟盘测试或实际交易记录。`doctor` 的 ready 仅指本地版本、参数和 Code 格式，不代表授权、激活或归因验证。

## 生成计划

1. 明确用户选择 OKX Global。首版只支持现货限价买入；不根据用户 IP 推断账户站点。
2. 收集用户决定的交易对、预算、最大预期亏损、入场价、止损参考价、双边手续费与滑点假设。预算和亏损以计价币表示，费率输入是每侧 bps。缺失参数先补问，不默认投入金额、方向或止损。
3. `quote --site global --symbol BTC-USDT` 查询公共数据；实际交易对使用用户选择值。
4. 调用 `plan --site global --symbol … --budget … --max-loss … --entry … --stop … --fee-bps … --slippage-bps … --out …`。为每次计划选择新文件，别覆盖用户记录。
5. 展示数量、预期成本、预期亏损、报价时间、输入假设及有效期。明确：**止损价只是计算参考，本项目生成的买单未附加止损订单**。实际跳空、费用和流动性会使结果不同。
6. 如用户要求，调用 `scenario --plan … --exit-price …` 比较假设退出结果，保留情景/实际交易的区别。

## 管理本地模拟策略机器人

使用本 Skill 中 `scripts/bot.py` 的绝对路径，无需 Web 服务。该入口与 `tradeplan.py` 分开：前者管理本地虚拟策略，后者负责现货计划和交易所命令预览。

1. 首次确定一个持久化账本路径，后续始终传 `--db 账本绝对路径`，放在子命令之前。独立 Skill 默认使用 `$XDG_DATA_HOME/tradeplan-guard/paper.sqlite3`，未设置该变量则为 `~/.local/share/tradeplan-guard/paper.sqlite3`；完整项目根目录的 `bot.py` 默认使用项目 `data/paper.sqlite3`。不能把不同账本当成同一账户，不自动删除记录。
2. `sample` 只显示固定配置，不写账本。仅在用户要求演示时使用该样例；实际策略需要用户确定币种、`interval`/`price`、`demo`/`public` 行情、每笔与总预算、间隔、次数、费用和滑点。到价型还需 `trigger_price`。金额为十进制字符串，间隔与次数为整数。
3. 将用户确定的配置写入本地 JSON，用 `create --config 配置文件` 创建；初始暂停。创建、查看已授权本地配置无须反复请求批准。用 `list` 或 `status --id 实际ID` 读回参数。
4. 用户明确授权启动该具体策略后，执行 `start --id 实际ID`。不能把安装 Skill、创建暂停策略或希望赚取返佣当作启动授权。预算、次数和行情来源必须与已授权配置一致。
5. `run --once`（或 `tick`）检查一轮；`run --poll-seconds 2` 前台持续检查。没有运行器就不处理策略，不另建系统定时任务或云自动化。新账本的 10,000 USDT 是虚拟资金；所有记录均是本地模拟，`public` 只表示行情来自公开接口。
6. 用 `pause --id 实际ID` 暂停，`stop --id 实际ID` 终止，`orders`/`events` 查询记录。按 Ctrl+C 只退出运行器，策略状态保留；重启会继续检查原来运行中的策略，不补跑错过的每轮。若用户要求停止运行，明确区分暂停策略和退出进程，并按其意图执行。
7. 行情或模拟余额检查失败会暂停策略；核对失败原因再按用户意图恢复，不擅自增资、增预算或改交易所账户。到价条件持续成立可按间隔多次模拟买入，不将其描述成只触发一次。

机器人尚无交易所执行连接器，不读取账户密钥，也不调用官方 CLI 下单。不得将虚拟成交、策略次数或预览当作欧易成交或返佣。

## 交易前检查

只有用户明确要交易时进入本节。执行前必须完成以下检查；任何未知或失败都停止，不替用户改变账户或转入资金。

- 发布者 Code 已真实配置，且其审核/激活状态和适用范围由工作台确认；未验证时不得宣称可得返佣。先告知用户订单将携带本项目 Builder Code，发布者可能获得合格交易手续费分成。
- `okx --version` 至少 1.4.4；检查 `okx spot place --help` 实际支持 `--aiBuilderCode`、`--px` 和 `--clOrdId`。缺少归因参数则停止。
- 本版只支持本地 API-key profile。确认用户实际选择的 profile、Global 站点及 `demo` 属性；不要依赖 profile 名字判断环境。查看本地配置时只向聊天输出 profile 名、站点和模式等必要字段，不输出密钥、secret、passphrase 或完整配置。配置无法明确判定时停止，让用户在官方 CLI 内完成配置；不收集凭证。
- 默认模拟盘。检查当前 CLI 全局帮助，确认支持 `--demo` 强制模拟模式。模拟盘调用显式带 `--profile 实际名称 --demo`，并核对 profile 本身也是模拟盘；实盘只有用户明确选择后使用 `--profile 实际名称 --live`。不得静默回落到默认 profile 或 OAuth。
- 用相同 profile 和明确模式读取 `account config`，仅允许 `acctLv` 为 1 或 2，且使用 `cash`。模式 3/4 暂不支持，不自动改账户设置。
- 读取 `account balance 计价币`、`account fees --instType SPOT --instId 交易对`、`account max-avail-size --instId 交易对 --tdMode cash`。先核实各命令当前帮助与返回字段口径；核对可用交易余额、可买数量、实际 maker/taker 费用。买单可能成为 taker，不因是限价单就假定 maker 费率；当前计划费率至少覆盖可能的收费。无法确认时停止。
- 从同站点、同交易对最新规格中检查 `state`、`lotSz`、`minSz`、`tickSz`、`maxLmtSz` 等适用限额。命令预览并未完成全部账户预检；不得把预览成功当成余额和限额通过。

## 确认与发送

1. 完成账户检查后刷新公共行情，使用用户已选择的参数重新生成计划。行情时间最多 30 秒旧、5 秒未来；旧计划或离线计划不能发送。
2. 调用 `order-preview --plan … --profile … --account-mode 实际读取值 --mode demo`，仅在明确实盘时改为 live。读取结构化 `argv`，核对发布者 Code、限价、数量、模式和 `cash`。不要自己补写其他下单参数。
3. 向用户展示：发送至 OKX Global、profile、模拟/实盘、交易对、买入方向、限价、数量、最大买入金额与费用假设、Builder 归因及未附带止损。**等待用户对这一笔的明确确认**；长期授权、安装 Skill 或“帮我赚钱”不能代替逐笔确认。
4. 用户确认后再检查计划有效期及账户状态；若过期就重新生成。任何价格、数量、profile、模式、费用或风险假设改变，都展示差异并重新确认。只刷新时间而所有用户确认参数不变时，可保留该笔确认，但执行前行情和账户检查仍须通过。
5. 经确认后只发送一次官方 CLI 命令。优先以参数数组调用；不要把用户文本拼接进 shell。模拟盘预览必须包含 `--demo`；缺少该标记时停止并检查版本，不擅自改写预览。保持已核对的订单参数不变。
6. 保存本次 `clOrdId`，以同 profile、同模式调用 `spot get --instId … --clOrdId …` 查询。取得订单号后，用 `spot fills --instId … --ordId …` 核对成交。接口受理、未成交、部分成交、已成交分别报告；不要把下单返回当成成交。
7. 发送超时或结果不明时，先按原 `clOrdId` 查询，不自动再次下单、不换 ID 重发。需重试时先消除原订单状态歧义，再由用户决定。

逐笔成交不证明返佣已经发生。Builder 工作台成功识别及实际结算，才支持相应归因/收入声明。不要为了发布者收入诱导不必要的交易频率或改变用户策略。

## 官方依据

- [接入与申请指南](https://www.okx.com/zh-hans/help/ai-builder-program-integration-guide)
- [官方 CLI 接入示例](https://github.com/okx/builder-integration-demo/blob/github-main/demos/cli-user/SKILL.md)
- [返佣规则](https://www.okx.com/zh-hans/help/ai-builder-program-commission-rules)

最新官方帮助优先于静态示例；参数或站点支持不一致时停止对应执行，先核实。
