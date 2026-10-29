# 发布与启用

## 原型发布

v0.3 以 MIT 许可发布为申请原型。以下说明发布内容边界及后续交易启用流程。原有 `dist/tradeplan-guard-0.1.0-prototype.zip` 和包含旧网页的 `dist/tradeplan-guard-0.2.0-local.zip` 保留为历史恢复包，不覆盖、不当作 v0.3 分发。

原型可以展示真实已实现能力，用于申请项目链接；必须保留 `builder.json` 的 null Code 和未完成交易验证说明。先审阅拟公开内容，再由项目所有者明确授权发布。公共仓库：https://github.com/JokerFuFu/tradeplan-guard。

推荐发布物：一个独立 GitHub 仓库、一份带固定离线演示的 README、一份含 Skill 与独立机器人的完整项目压缩包，以及一份自包含 Skill 压缩包。Skill 包包含机器人程序，不包含虚拟账本。仓库地址确认后，再生成可复制的 `npx skills add` 安装命令；不要提前写入不存在的地址。

原型传播文案：

> 让 AI 在下单前把预算、数量和费用算清楚。TradePlan Guard 提供独立 Skill 与可由命令行管理的模拟策略机器人，Python 标准库即可体验，无需浏览器。机器人仅使用虚拟资金，交易所执行连接器尚未实现；Skill 交易流程仍待 Builder Code 和交易所模拟盘验证。

先让少量愿意试用的人完成“安装—离线演示—真实行情—交易计划”，收集失败原因，再改进安装与使用体验。未经同意不发送推广消息，不把下载数当活跃用户，不把预览数当成交量。

## 具体公开文件清单

v0.3 完整项目仅从本项目目录按以下白名单打包，不递归打包整个目录：

- `README.md`、`LICENSE`、`start.command`、`bot.py`
- `docs/QUICKSTART.md`、`docs/BOT-QUICKSTART.md`、`docs/APPLICATION.md`、`docs/PUBLISHING.md`、`docs/VALIDATION.md`（验证记录完成后纳入）
- `skills/okx-tradeplan-guard/SKILL.md`
- `skills/okx-tradeplan-guard/builder.json`
- `skills/okx-tradeplan-guard/scripts/tradeplan.py`、`skills/okx-tradeplan-guard/scripts/bot.py`
- `skills/okx-tradeplan-guard/scripts/tradeplan_guard/market.py`
- `skills/okx-tradeplan-guard/scripts/tradeplan_guard/planner.py`
- `skills/okx-tradeplan-guard/scripts/tradeplan_guard/execution.py`
- `tests/test_market.py`、`tests/test_planner.py`、`tests/test_execution.py`、`tests/test_cli.py`
- `skills/okx-tradeplan-guard/scripts/tradeplan_guard/bot_engine.py`、`skills/okx-tradeplan-guard/scripts/tradeplan_guard/bot_quotes.py`
- `tests/test_engine.py`、`tests/test_bot_cli.py`

独立 Skill 包只包含上列 `skills/okx-tradeplan-guard/` 下的九个文件。实际新增模块或测试须经审阅后逐项加入清单。明确排除 `data/`、`evidence/`、`__pycache__/`、`.env` 及其变体、`PROGRESS.md`、`docs/superpowers/`、既有 `dist/` 产物，以及私人投资目录、账户配置、密钥、真实持仓/交易记录、日志和工作过程文件。测试中的 Code 是测试数据，不能复制到发布者配置或用于真实订单。

当前版本不包含网页助手及其模型服务配置。白名单打包后应检查实际归档条目，不能把文件生成成功当成已公开发布。

## 取得 Builder Code 后

以下步骤针对独立 Skill。机器人的交易所执行连接器仍需另行实现和验证，取得 Code 不会让机器人转为交易所交易。

1. 在 OKX 官方申请页面提交真实项目资料，读取 Builder 工作台状态；Code 必须来自本人获批/待审的实际申请，不使用示例或他人的值。
2. 只修改本项目 `builder.json` 的 `builder_code` 为真实值。Code 是公开归因标识，不能把 API 凭证放入这个文件。
3. 用 Global 模拟盘 profile 完成账户、费率和交易规格预检，再逐笔确认并提交一笔合规测试订单。
4. 分别验证命令带 Code、订单受理、实际成交、工作台交易识别。按实际可观察范围记录；没有某项证据就保留未验证。
5. 根据工作台的审核/激活状态和适用规则判断返佣资格；Code 格式正确或命令可运行都不能替代此判断。
6. 更新 README 的状态与真实验证记录，重新跑测试和独立审阅，再发布启用版。

首次实盘由用户明确选择并逐笔确认。返佣按合格净手续费及适用规则结算，不以自营交易或增加无必要交易量为推广目标。

## 发布后的衡量

只记录经用户同意且有证据的数据：安装成功反馈、完成计划的用户数、实际带 Code 的订单数、合格成交及工作台返佣。先建立本地或人工验证记录；首版未实现遥测、统计后台或自动推广。
