# AI Builder 申请材料草稿

状态：v0.3 申请原型；申请结果以 OKX 工作台为准。以下项目描述可作为申请初稿；提交前核对实际发布版本和表单要求。

## 项目名称

TradePlan Guard（现货交易计划助手）

## 项目类型

AI Skill / 独立本地模拟策略机器人，当前为原型阶段。

## 项目链接

https://github.com/JokerFuFu/tradeplan-guard

## 中文简介

TradePlan Guard 提供独立 Coding Agent Skill 和可独立运行的策略机器人两个入口。用户提供预算、预期亏损约束、入场和止损参考价，工具读取 OKX Global 公共行情及交易规格，计算符合数量步进的交易计划，并展示手续费、滑点和退出价格情景。项目已实现公共行情客户端、十进制风险计算、Skill 情景分析及官方 CLI 命令预览；AI 交互由安装 Skill 的宿主提供。

定时定额和到价机器人随 Skill 一同安装，也可通过项目根目录命令行管理，使用 SQLite 持久化虚拟账户。支持固定演示行情与 OKX 公共行情，成交均为本地模拟。机器人创建后暂停，需主动启动，受单次预算、总预算、间隔及次数限制；前台运行器或单次 tick 才处理策略，不安装系统定时任务。机器人尚未实现交易所执行连接器。本地虚拟成交不是 OKX 模拟盘成交或实盘成交，不产生归因和返佣。

项目计划通过使用者本地的官方 OKX CLI 完成账户授权与执行，在逐笔展示订单并取得用户确认后，以 `--aiBuilderCode` 带入项目发布者的真实 Builder Code。用户凭证保留在本地 CLI。首版限于账户模式 1/2 的 cash 现货限价买入。获得 Code 后将完成官方模拟盘下单、成交与工作台归因验证，再开放经验证的交易流程。

## English description

TradePlan Guard has two entry points: a standalone AI Skill and independent local paper strategy bots. It uses OKX Global public market data and instrument specifications to size a user's proposed spot purchase within budget and hypothetical loss constraints, including fee and slippage assumptions. The prototype implements a public data client, decimal-based sizing, Skill scenario analysis and official CLI command preparation. Natural-language interaction is provided by the user's AI host.

Interval and price-triggered bots are bundled with the Skill and can also be managed through a project command-line entry point. They use a persistent SQLite virtual account. Fixed demo quotes and public quotes both lead only to local paper fills. Bots start paused, require an explicit start, and are bounded by per-order and total budgets, intervals and maximum runs. A foreground runner or an explicit single tick checks strategies; no system scheduler is installed. An exchange execution connector for the bots has not been implemented. Local paper fills generate no Builder attribution or commission.

The intended execution flow uses the user's locally configured official OKX CLI and explicit confirmation of each order, with the publisher's assigned Builder Code passed through `--aiBuilderCode`. Credentials remain in the local CLI. The initial scope is cash spot limit buys in account modes 1 and 2. Exchange demo execution, fills and Builder dashboard attribution will be validated after the Builder Code is issued.

## 提交时如实填写

- 阶段：原型；尚无已核实的活跃用户、交易量或返佣收入。
- 已完成：以当前代码、测试记录和实际演示为准。
- 待完成：机器人交易所执行连接器开发、真实 Builder Code、Skill 账户及官方模拟盘验证、工作台归因验证、面向真实交易的正式启用。正式状态以实际发布版本和 OKX 工作台为准。
- 申请人及联系邮箱：使用本人确认的资料，在 OKX 官方表单填写；本文件不保存身份或联系资料。
- 产品不承诺盈利；风险和止损数值是情景假设，不是已执行止损或收益保证。

提交前展示实际表单内容和适用条款，取得确认。技术接入不能证明审核、激活、归因或返佣成功。
