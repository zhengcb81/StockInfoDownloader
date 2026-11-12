# MB-SID — 独立施工卡

## A0：先把11项有价值但未完成的WIP安全接收（2026-11-11新增）

先读总计划 `reconciliation.md` 及 `review/repo_reconciliation_20261111/acquisition_review.md` §4 SID逐文件表。6个refs都已进入正式 `v2-clean-rewrite`，不存在待合旧分支；问题是主工区11项未提交旧CW-2.27D/H下载器改进（743增/94删）。它们有价值但没有绑定当前内容的完整验收，不能直接commit或当垃圾restore。

保留输入精确11路径：`README.md`、`config_template.json`、`main.py`、`src/browser.py`、`src/downloader.py`、`src/logger.py`、`src/mapping.py`、`src/models.py`、`tests/e2e/official_e2e_test.py`、`tests/unit/test_downloader.py`、`tests/unit/test_official_e2e_contract.py`。额外 `scripts/capture_byd_fy2024_fixture.py` 是现有离线fixture的唯一生成出处，保留到测试工具/说明，不能执行成新公司特判采集。公司名单是用户输入，保留。原件/运行config不动。

在本卡新工区中按单一职责读入上述差量并先写行为RED，允许本卡原写集合增加这些legacy browser/downloader/日志/映射/命令模块与测试：

1. 同一实例先收到CONFIRMED_EMPTY、再处理不同公司/期次；第二请求必须重新取得对应状态，不能继承第一次空。不可只预置私有属性模拟证明已接好真实API。
2. 目的目录组件正确匹配：POSIX合法路径、Windows大小写/分隔符，以及`raw/prospectus`与`raw/prospectus-extra`必须区分。不能反斜杠替换后做字符串子串判断。
3. active tab为空、非活动tab有公告：必须保持当前筛选范围，不退回整个页面下载其他类型/期次。测试真实DOM行为，不检查browser源码字符串凑绿。
4. JSON模式stdout只有协议结果、诊断走stderr；有效配置/CLI/业务模型保持兼容。legacy浏览器用fake DOM/response，测试不真实下载；官方E2E改动只记录既有受控入口，不以7月139测试/旧README数字冒当前结果。

随后将通用改进分成可回退的小提交，完成原SID-01 typed错误、SID-02纯metadata边界。C阶段集中运行受影响unit/协议测试与独审；可选真实采集只有确有验收需求才由ROOT安排，不每步下载。旧WIP原工区在本卡交付且ROOT确认等价接收后才清理；SID G4三份PWF镜像先保留唯一历史说明再回收。此A0直接进入原A/B/C，无需ROOT另行批准每个小步骤。

## 任务定位与唯一工区

- 原仓：`C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite`；基线 `c0f07e12d4ba3e232d712bb6e5e491832023b0a0`；目标主线 `v2-clean-rewrite`。
- 新工区：`C:/Users/郑曾波/Projects/mb11-sid`；分支 `codex/mb11-sid`。本卡尚未开工，不把准备好的卡称为已派发。
- 本仓PWF：`docs/plans/mb11-sid-2026-11-11/`。先建立 task_plan.md、findings.md、progress.md，记录真实基线与工作量；本卡及公共接口说明可复制到该目录inputs。
- 总控计划：`C:/Users/郑曾波/Projects/company-wiki/docs/plans/module-boundaries-2026-11-11/`。开工只需读本卡、该目录 interfaces.md、acceptance.md、runtime_verification.md 和本仓AGENTS；无需回放旧聊天/全部历史PWF。

```powershell
git -C 'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite' worktree add -b codex/mb11-sid 'C:/Users/郑曾波/Projects/mb11-sid' c0f07e12d4ba3e232d712bb6e5e491832023b0a0
```

若工区/分支已存在，先只读核归属；不能 reset、清别人的目录或接管未知工作区。可以用新的唯一后缀并记录。用仓库实际可用的Python/离线依赖；不要重新抓取原件或部署到全局技能目录。

## 全卡共用完成规则

- 先列本仓实际交付runtime的活动入口、逻辑模块、公开面、状态owner和依赖方向；包含兼容/退休分类。确认缺口只是入口，不是允许忽略其他已登记模块。发现同根绕行在本卡owner内归并修复，新增业务需求交父计划。
- 保留现有公开协议；各模块只写自己代码和状态。公开协议真需要改时先把失败例和最小兼容方案交ROOT协调，继续其余独立工作；不擅自改邻仓。
- A写行为/隔离测试 → B修owner根因 → C模块验收。A/B/C是工程步骤，完成A即可继续B/C，不需ROOT或用户逐步批准。
- 接口负例应体现实际能力/依赖错误；fixture/缺依赖/沙箱权限失败不冒作产品RED。已有边界通过就保留，不为凑改动重写。
- 只在模块最终交付前调用独立审查agent，审完整度、架构归属、回归和所有新增测试。修复所有本卡可行动问题并复核，才交付；非本范围新发现明确列给ROOT。
- 测试用新临时目录，恢复初始状态；生产原件/配置/既有WIP不动。只运行受影响测试与必要最终包级CI，不每小步重跑全量，不删断言换绿。
- 提交并推送自己的交付分支（存在remote时）；不自行合并主线、不修改ROOT总PWF。交付本仓PWF下 handoff.md/json、独审报告、测试/恢复证据索引，格式见总计划handoff_contract.md。

## 目标与基线注意

SID当前正式provider在v2-clean-rewrite分支；不创建假的main/master，不处理旧StockInfoDownloader。只从已提交c0f07e1创建新工区，再按本卡A0逐职责受测接收已明确的11项WIP差量；不复制整个旧工作树。原始WIP保持到ROOT接收后再清理。

本卡合并两个同根问题：fetch包装丢失CninfoApiError.error_code/retryable；底层cninfo_api反向调用上层adapter私有_report_metadata。让错误和公告元数据归纯provider domain，API/adapter分别依赖它，保持现有公开JSON1.0。

## 写集合

`src/company_wiki_adapter.py`、`src/company_wiki_adapter_cli.py`、`src/cninfo_api.py`、新增`src/cninfo_report_metadata.py`或现有等价纯模块；对应 `tests/unit/test_company_wiki_adapter.py`、`test_company_wiki_adapter_cli_budget.py`、`test_cninfo_api_budget.py`、`test_g5_provider_runtime.py` 和新增 `test_provider_error_contract.py`、`test_provider_dependency_direction.py`。本仓PWF和最小引用文档可写。

本卡可以在新工区按A0修改已登记的standalone链，但不写原工区11项WIP、生产config/cache/canonical目录、CWP/FF/Dayu。纯metadata模块仍不依赖browser/downloader上层。发生真实语义冲突时用失败例与ROOT协调，不能reset别人的工区。

## A/B/C与测试

1. RED：host不允许、无PDF魔数、内容过小三个非retryable失败，以及真正可重试timeout，全部经公开adapter CLI验证稳定code/retryable/usage。现在前者被默认包装成upstream_unavailable/retryable=true，不能只测“发生异常”。
2. RED：API纯读取/过滤在拒绝import company_wiki_adapter、browser/downloader的子进程仍工作；用已有年/半年/季报/类型/期间fixture锁过滤语义，合法多市场/期次不凭公司名字改。
3. GREEN：保留typed cause从transport→adapter→CLI全链；测量usage不丢，unknown不写0。将_report_metadata纯解析移动到domain模块，API和adapter使用同一函数；保留必要旧兼容仅在adapter侧重导出，下层不反查它。
4. 组合：独立临时runtime+公开`python -m src.company_wiki_adapter_cli discover|fetch`，HTTP由本地fixture供应；只写本次staging，失败.part清理、成功hash/receipt一致；无CWP内部库/浏览器运行时。
5. 独立审查全部本卡变化及测试，再修复交付。ROOT接收A0经过修复和证明的WIP与原provider边界改动；两部分分提交、同一大节点验收，不原样顺带提交旧11文件。

```powershell
python -B -m pytest tests/unit/test_company_wiki_adapter.py tests/unit/test_company_wiki_adapter_cli.py tests/unit/test_company_wiki_adapter_cli_budget.py tests/unit/test_cninfo_api_budget.py tests/unit/test_g5_provider_runtime.py -q -p no:cacheprovider
python -B -m pytest tests/unit/test_provider_error_contract.py tests/unit/test_provider_dependency_direction.py -q -p no:cacheprovider
```

## 出口

API→domain←adapter依赖单向；错误类别/可重试性/计量贯通；staging-only/预算/旧入口无退化，独审通过，目标分支和现有owner WIP的关系在handoff清楚。

## 并线交接步骤（目标分支：`v2-clean-rewrite`）

1. 作者提交并推送卡片分支，交付最终tip、精确diff、包级测试、独审绑定tip及隔离测试恢复记录；未提交11项旧WIP不得作为已完成交付。
2. ROOT在独立集成工区核对最新目标分支、提交祖先关系与本卡写集合，只接收经过测试的修复提交；保留原工区未提交状态，不能恢复掉未核销文件。
3. 在集成后SID树集中运行本卡受影响suite一次。若冲突解决改变源码，测试和独审绑定最终代码tip；不创建假的`main/master`，不修改旧StockInfoDownloader。
4. 通过后由ROOT推送 `v2-clean-rewrite`，在本卡handoff与总控reconciliation记录实际SHA、测试和状态`MERGED`；具体失败交回SID作者。
