# StockInfoDLSimple 候选交接

Owner 基线为 `v2-clean-rewrite@9b0c07c91a76789a09b458aaa796d8dfd2d1957a`。以下更改在 company-wiki 内的隔离候选，实际 owner 工作区、技能副本和配置没有写入。

## 行为

- 页数上限不触发额外点击。正向及反向返回前检查真实目标位置，缺控件或动作失败保留原原因。第一页已完成的文件保持原样，整项失败且按原 run/attempt 查得到页、目标、失败类型和已确认文件数。
- 浏览器列表与详情使用分开的页面。文件先写临时位置再原子落地，已经观察到的文件响应发生写入失败时保持原始原因，不再切换方式重发。失败细节独立于后续整体分类。
- `RunReceipt` 复用于普通 CLI 和适配器，先建立运行号，再进配置读取、输入等待和供应商调用。原来已经存在的原生回告协议保留。运行记录追加到同一 `runs` 下的安全流水，冷查可以按回执区分请求准备、发出意图、响应、落盘和已知未发。完成回读不会再启动 provider。
- 适配器官方披露 API、身份查询和 PDF 运输使用一次 owner 回调来记录每次分页、原阶段和局部返回。日志、收件箱及运行目录都拒写时，stderr 给出原身份及不可用提示，失败 JSON 仍为最后一行。

## 复跑

从隔离候选目录运行。测试并不接触外部 API、真实浏览器或资料库。

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONPATH=(Get-Location).Path
C:/Miniconda/python.exe -B -m pytest -q -o addopts= -p no:cacheprovider --tb=short --basetemp ../sidverify tests/unit/test_sid_runtime_closure.py tests/unit/test_cninfo_api.py tests/unit/test_cninfo_api_budget.py tests/unit/test_cninfo_api_fixture_contract.py
```

最后一批实测 53 项通过。加入每页 API 事件前，下载、适配器协议与 F4 owner 扩展组合 103 项通过。推荐在最终版本另加 `test_legacy_download_contract.py`、`test_s5_adapter_logging.py`、`test_s1_logging_and_browser_errors.py`、`test_company_wiki_adapter_cli.py`、`test_company_wiki_adapter_cli_budget.py`、`test_feedback_observation.py`、`test_feedback_owner.py` 和该节点的 provider 错误协议。专有测试入口的收集能力由仓内快 CI 持续检查。

## 交付范围

补丁及逐文件哈希在隔离候选旁的 `sid-runtime-remediation.patch` 和 `sid-runtime-remediation.manifest.json`。前端在全部诊断介质不可用时只能接收同一运行标识的即时告警。真实 Chromium、现场下载路由与 Windows 两进程共写同一个轮转日志的证明仍需独立验证。显式 OUT 仍为旧的调用方一次性投递路径，原尝试可以从本仓账本查回。新版本的部署、CI 远端结果和独审签收均未发生。
