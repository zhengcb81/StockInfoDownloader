# SID S3/S4 公告匹配策略边界

正式分支 `v2-clean-rewrite@ab50c8f`。只在本仓隔离工区。提供者 adapter 已有纯标题匹配服务，但从私有别名导入，而 downloader 另保留两份相同函数。改为两入口使用 owner `disclosure_matching` 的公开谓词，保留必要旧导入引用和所有筛选语义。

先复现两入口缺同一个公开接口，以明确的标题和值回归取代两份实现彼此比较，再保留 provider mapping、CLI 预算和下载器的现有测试。确认旧带日期匹配、空关键词规则及排除顺序原样有效。真实网络、下载和生产日志均不使用。本仓 PWF 与主工区的在途文档独立。

RED 1 failed、9 behavioral passed、22 deselected。旧 adapter 无 canonical 公开匹配名，旧 downloader 另有实现。共用叶子接线完成，和既有入口采用同一逻辑。适配层兼容原列表/元组参数并减少重复复制。旧外部调用语义、筛选顺序、原日期格式保留。

## 验证

5 文件离线组合包括 downloader、CNINFO adapter、真实模块 CLI 包装、预算回执及 G5 provider。首轮 84 过，13 项在进入业务前失败。11 项 fixture 试图在外部源码工区下创建 `.planning/test-tmp`，2 项浏览器静态断言要求 cwd 是源码根。按根因改为独占 TemporaryDirectory 和基于测试文件的源码定位，业务断言原样保留，复跑全组 97 项通过（22.18 秒）。Git diff 和定向 Ruff 通过。非作者复核两套旧实现、兼容入口、空关键词和大小写与实际日期过滤、临时目录归属并复跑 11 项（含真实 CLI 测试），ACCEPT。发布以远端正式分支实际 SHA 为准。
