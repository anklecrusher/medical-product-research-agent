# LOG.md

本文件用于记录多线程开发中的跨线程变更和关键决定。每个开发线程完成有意义的工作后，都应在这里追加一条简短记录。

## 记录模板

```markdown
## YYYY-MM-DD / 会话名称

修改文件：

- `path/to/file`

改动摘要：

- 本次做了什么。

关键决定：

- 本次做出的重要选择。

后续事项：

- 剩余工作、阻塞点或风险。
```

## 2026-06-15 / 规划基线

修改文件：

- `医疗产品调研Agent开发周期计划表.md`
- `AGENTS.md`
- `LOG.md`

改动摘要：

- 创建医疗产品调研 Agent 的开发周期计划表。
- 新增仓库级多线程协作说明，供后续新线程读取。
- 新增共享日志文件，用于记录跨线程变更。
- 将 `AGENTS.md` 和 `LOG.md` 改为中文表述。

关键决定：

- 使用 workflow 优先架构，LangGraph 作为候选主编排层。
- 将 `paper-qa`、`gpt-researcher`、`STORM` 作为必须参考的设计项目，而不是直接 fork 或硬依赖。
- 先做 CLI 最小闭环，再做 FastAPI 和前端。
- 用户上传的私有资料默认只在本地处理。

后续事项：

- 开始实现时，先创建 Python 项目骨架并更新本日志。
- 在产生本地数据库、缓存、输出报告、API key 前，先创建 `.gitignore`。

## 2026-06-15 / AGENTS 总领文件重写

修改文件：

- `AGENTS.md`
- `LOG.md`

改动摘要：

- 将 `AGENTS.md` 从阶段性开发提示重写为全流程总领文件。
- 新增项目使命、架构原则、模块边界、数据规范、参考项目使用边界、隐私规则、报告质量标准、多线程协作规则、依赖原则和维护演进原则。
- 移除“第一阶段开发风格”这类局部阶段表述，使其适合作为所有后续线程的全局指导。

关键决定：

- `AGENTS.md` 定位为项目宪法式文件，不承担具体排期和任务清单职责。
- 具体阶段任务仍以 `医疗产品调研Agent开发周期计划表.md` 为准。

后续事项：

- 后续若技术选型、隐私策略、模块边界或协作规则变化，应同步更新 `AGENTS.md`。

## 2026-06-15 / Git 工具路径约定

修改文件：

- `AGENTS.md`
- `LOG.md`

改动摘要：

- 在 `AGENTS.md` 中新增 Git 使用约定。
- 明确后续线程涉及 git 操作时，应直接使用完整路径 `D:\Users\gongjx\AppData\Local\Programs\Git\mingw64\bin\git.exe`。
- 记录 GitHub CLI 路径 `C:\Users\gongjx\tools\gh\bin\gh.exe`。

关键决定：

- 不再让后续线程先尝试普通 `git` 命令，避免重复遇到 `error launching git`。

后续事项：

- 本次文档变更需要提交并推送到 GitHub。
## 2026-06-15 / 项目骨架与核心 schema 初始化

修改文件：
- `pyproject.toml`
- `.env.example`
- `README.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/config.py`
- `src/medical_research_agent/schemas.py`
- `tests/test_schemas_import.py`

改动摘要：
- 建立 Python 项目基础结构，补充 `pyproject.toml`、包入口和测试配置。
- 创建本地优先运行配置模块，明确 `data`、`outputs`、`cache`、`uploads` 四个目录约定。
- 定义核心 Pydantic schema，覆盖 `ResearchTask`、`SourceRecord`、`ParsedDocument`、`EvidenceItem`、`ProductSpec`、`Claim`、`ReportSection`、`ReportArtifact`。
- 添加最小导入测试，验证 schema 可以被正常导入并序列化为 JSON 友好结构。

关键决定：
- 先固定 schema 和目录约定，再进入 workflow、connector、报告和 PDF 层。
- 继续坚持本地优先边界，私有资料相关目录默认留在本地，不进入 git。
- 运行依赖尽量保持轻量，只引入 `pydantic`、`pydantic-settings` 和测试依赖。

后续事项：
- 当前机器没有可用 `python` 可执行入口，pytest 只能在有 Python 环境的机器上实际跑。
- 后续线程可以直接基于现有 schema 扩展存储层、workflow 编排和报告模板。

## 2026-06-16 / 本机 Python 环境与 Codex 开发配置

修改文件：
- `README.md`
- `scripts/activate-dev.ps1`
- `LOG.md`

本机新增但不提交的文件/目录：
- `.venv/`
- `.env`
- `.vscode/settings.json`
- `data/`
- `outputs/`
- `cache/`
- `uploads/`

改动摘要：
- 在当前用户目录安装 Python 3.12.9，并在项目根目录创建 `.venv` 虚拟环境。
- 使用 `.venv\Scripts\python.exe -m pip install -e ".[dev]"` 安装项目及测试依赖。
- 创建本地 `.env`，沿用 `data`、`outputs`、`cache`、`uploads` 四个运行目录约定。
- 创建 VS Code/Codex 友好的本地解释器配置，默认指向 `.venv\Scripts\python.exe`。
- 补充 `scripts/activate-dev.ps1` 和 README 开发命令，提醒后续线程优先使用项目内 `.venv`。

关键决定：
- 后续本仓库 Python 命令优先使用 `.venv\Scripts\python.exe`，避免再次命中 Windows Store 的 `python.exe` 占位入口。
- `.env`、`.venv`、`.vscode` 和本地运行目录继续由 `.gitignore` 排除，不进入版本库。

后续事项：
- PowerShell 当前执行策略会阻止直接运行 `.ps1` 激活脚本；必要时可直接使用 `.venv\Scripts\python.exe` 执行命令。
- 目前最小测试已在本机通过：`2 passed`。

## 2026-06-16 / Codex worktree 环境脚本与 Node 预留

修改文件：
- `.codex/setup.ps1`
- `.codex/actions.ps1`
- `.codex/README.md`
- `README.md`
- `LOG.md`

改动摘要：
- 新增 `.codex/setup.ps1`，用于 Codex worktree 初始化：创建 `.venv`、安装 `pyproject.toml` 中的开发依赖、创建本地运行目录。
- 新增 `.codex/actions.ps1`，提供 `test` 和 `doctor` 两个常用动作入口。
- 在 Codex setup 中预留前端逻辑：当未来加入 `package.json` 时自动执行 `npm install`。
- 验证当前环境可用 Node：当前 PATH 中可见 `node v24.14.0`、`npm 11.9.0`，来源为 CodexTools。
- 尝试下载并运行官方 Node 24.16.0 LTS MSI；当前 shell 仍优先解析到 CodexTools Node，后续若需要系统级 Node，可重新用安装器或手工安装。

关键决定：
- 当前阶段不提前创建前端工程，也不新增 `package.json`；只在 Codex setup 中为未来前端安装预留条件分支。
- Python 依赖仍以 `pyproject.toml` 为唯一主来源，暂不新增 `requirements.txt`。
- Codex worktree 初始化优先使用 `.codex/setup.ps1`，避免新 worktree 缺少 `.venv` 或本地目录。

后续事项：
- 在 Codex App 的项目环境设置中，Windows setup script 可填写：`powershell -ExecutionPolicy Bypass -File .codex/setup.ps1`。
- 可添加两个 Codex action：`test` 执行 `.codex/actions.ps1 test`，`doctor` 执行 `.codex/actions.ps1 doctor`。
- 未来开始前端时，再新增 `package.json` 和实际前端目录结构。

## 2026-06-16 / 图文增强弹性报告模板

修改文件：
- `pyproject.toml`
- `README.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/schemas.py`
- `src/medical_research_agent/report_templates.py`
- `src/medical_research_agent/templates/report_markdown.j2`
- `templates/reports/medical_product_research_template.md`
- `tests/test_report_templates.py`

改动摘要：
- 新增图文增强报告模板说明，采用“固定骨架 + 可插拔章节块 + 图文资产位”的方式。
- 新增 Jinja2 Markdown 渲染模板，支持核心结论、动态章节、风险边界、参考来源和来源图嵌入。
- 扩展 schema，新增 `FigureAsset`、`ReportTemplate`、`ReportTemplateBlock` 以及图类型、图状态、模板块类型枚举。
- `ReportSection` 新增 `figure_ids`，用于后续章节规划和图资产挂接。
- 新增 `report_templates.py`，提供最小 Markdown 渲染 helper 和来源图 Markdown 渲染逻辑。
- 新增模板测试，覆盖来源图字段、图注/来源链接渲染、缺图占位。

关键决定：
- 当前阶段只定义模板和图字段，不实现 PDF 裁图、图片下载、自动图表生成或真实报告 workflow。
- 原始来源图可以直接嵌入 Markdown，但每张图必须有标题、图注和来源信息。
- 增加轻量依赖 `Jinja2`，用于后续报告模板渲染；Python 依赖仍以 `pyproject.toml` 为主来源。

后续事项：
- 下一步可进入 LangGraph 工作流骨架或 LLM 调用封装；报告模板已能为后续 `report_planner` 和 `section_writer` 提供结构约束。
- 未来做资料解析时，需要补充图资产抽取/保存逻辑，并把来源页码、图号和版权备注写入 `FigureAsset`。

## 2026-06-16 / LangGraph mock workflow 骨架

修改文件：
- `pyproject.toml`
- `README.md`
- `src/medical_research_agent/workflow/__init__.py`
- `src/medical_research_agent/workflow/state.py`
- `src/medical_research_agent/workflow/graph.py`
- `src/medical_research_agent/workflow/nodes.py`
- `examples/run_mock_workflow.py`
- `tests/test_workflow_mock.py`
- `LOG.md`

改动摘要：
- 新增 `workflow` 包，定义 LangGraph 状态结构、节点日志、调研意图、检索计划和 mock workflow 编排入口。
- 按 `parse_intent -> plan_research -> search_sources -> fetch_and_parse_sources -> extract_evidence -> deduplicate_evidence -> plan_report -> write_report -> verify_claims -> render_outputs` 顺序跑通完整 mock 流程。
- mock 节点使用现有 `ResearchTask`、`SourceRecord`、`ParsedDocument`、`EvidenceItem`、`ProductSpec`、`Claim`、`ReportSection`、`ReportArtifact` schema，不做核心 schema 扩展。
- `render_outputs` 会写出 `sources.json`、`documents.json`、`evidence.json`、`claims.json`、`report.md`、`workflow_state.json` 和 `run.log`，便于后续失败恢复与调试。
- 新增 `examples/run_mock_workflow.py` 和 workflow 测试，验证一句需求可以流转到 mock Markdown report artifact。

关键决定：
- 当前阶段只引入 `langgraph` 作为编排依赖，不实现真实 connector、真实网页/PDF 解析、LLM 写作、PDF 渲染或前端。
- workflow 节点保持函数式接口，后续 connector、parser、extractor、writer、verifier 可替换 mock 节点内部实现并继续沿用状态结构。
- `intermediate` 采用累积合并，`node_logs` 采用追加日志，确保节点日志和中间状态可追踪。

后续事项：
- 后续接入真实 connector 时，应优先替换 `search_sources`，并保持返回 `SourceRecord`。
- 后续接入真实解析和证据抽取时，应分别替换 `fetch_and_parse_sources` 与 `extract_evidence`，并补充错误重试/失败恢复策略。
- PDF 渲染仍未实现；当前只生成 Markdown artifact，符合本轮不实现 PDF 的约束。

## 2026-06-16 / 可替换 LLM 调用层

修改文件：
- `pyproject.toml`
- `.env.example`
- `README.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/config.py`
- `src/medical_research_agent/llm/__init__.py`
- `src/medical_research_agent/llm/models.py`
- `src/medical_research_agent/llm/privacy.py`
- `src/medical_research_agent/llm/client.py`
- `tests/test_llm_client.py`
- `LOG.md`

改动摘要：
- 新增 `llm` 包，提供 provider-neutral 的 `LLMMessage`、`LLMRequest`、`LLMResponse` 和 `LLMUsage` 数据结构。
- 新增 `LLMClient` 抽象接口、默认 `MockLLMClient` 和 OpenAI-compatible `/chat/completions` HTTP 客户端。
- 在 `AppSettings` 中新增 LLM provider、model、base_url、api_key、timeout、retry 和隐私开关配置。
- 在 `.env.example` 和 README 中预留第三方兼容 API 的 `MEDICAL_RESEARCH_LLM_*` 配置项。
- 新增隐私门禁：默认允许公开来源调用外部 LLM，默认阻止用户上传私有资料和内部私有资料发送到外部 LLM。
- 新增 LLM 单元测试，验证默认 mock、mock 响应、缺少 API key 报错和私有来源外发拦截。

关键决定：
- 默认 LLM provider 继续使用 `mock`，保证本地测试和 mock workflow 不依赖 API key 或网络。
- 第三方模型统一先走 OpenAI-compatible 接口，避免在节点里绑定具体厂商 SDK。
- API key 使用 `MEDICAL_RESEARCH_LLM_API_KEY`，避免与其他项目的全局环境变量混淆。

后续事项：
- 后续可把 `parse_intent`、`plan_research`、`extract_evidence`、`write_report`、`verify_claims` 分批改为通过 `LLMClient` 注入调用。
- 接入真实 LLM 前，需要为结构化输出失败、JSON 修复和调用日志持久化补充更细的测试。
- 如需支持非 OpenAI-compatible 厂商协议，可新增独立 client 类，但继续实现 `LLMClient` 接口。

## 2026-06-22 / 资料检索 connector 与文档解析最小版本

修改文件：
- `pyproject.toml`
- `.env.example`
- `README.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/config.py`
- `src/medical_research_agent/io.py`
- `src/medical_research_agent/connectors/__init__.py`
- `src/medical_research_agent/connectors/base.py`
- `src/medical_research_agent/connectors/pubmed.py`
- `src/medical_research_agent/connectors/crossref.py`
- `src/medical_research_agent/connectors/semantic_scholar.py`
- `src/medical_research_agent/connectors/url.py`
- `src/medical_research_agent/parsers/__init__.py`
- `src/medical_research_agent/parsers/web.py`
- `src/medical_research_agent/parsers/pdf.py`
- `examples/search_sources.py`
- `tests/test_connectors_sources.py`
- `tests/test_parsers_documents.py`

改动摘要：
- 新增统一 `SourceConnector` / `SearchRequest` 接口和 `ConnectorError`，connector 统一返回现有 `SourceRecord` schema。
- 实现 PubMed / NCBI E-utilities、Crossref、Semantic Scholar 最小论文检索 connector；Semantic Scholar 支持无 key 使用，也预留 `MEDICAL_RESEARCH_SEMANTIC_SCHOLAR_API_KEY` 配置。
- 新增公开 URL source 归一化能力，用于普通网页和 PDF URL 的后续解析入口。
- 新增网页解析器和 PDF 解析器，分别输出现有 `ParsedDocument` schema，并用 `DocumentParseError` 包装抓取和解析错误。
- 新增 `write_model_json` 小工具和 `examples/search_sources.py` 示例，可保存 `sources.json` / `documents.json` 中间产物。
- 新增 connector/parser 单元测试，覆盖字段映射、错误包装、HTML 正文抽取、PDF 页数解析和 JSON 落盘。

关键决定：
- 不改动现有核心 schema，优先将外部来源元数据放入 `SourceRecord.metadata`，解析信息放入 `ParsedDocument.metadata`。
- 只引入轻量依赖 `beautifulsoup4` 与 `pypdf`，避免为最小解析能力引入较重框架。
- 当前 connector/parser 只负责资料发现、抓取和解析，不写报告生成逻辑、不做 PDF 输出、不接前端。
- 参考 `paper-qa` 的文献元数据与可追溯来源分层思路，以及 `gpt-researcher` 的多源检索统一 source 记录思路；不引入两者为依赖。

后续事项：
- 将真实 connector/parser 接入 workflow 的 `search_sources` 和 `fetch_and_parse_sources` 节点，并补充重试、限速和缓存策略。
- 为 PubMed / Crossref / Semantic Scholar 增加可选邮件、API key、速率控制和分页支持。
- 网页正文抽取后续可评估引入 `trafilatura` 或更强的 readability 策略；PDF 后续需补充扫描件 OCR、表格抽取和页码定位。
- 网络集成测试可作为单独标记测试加入，默认单元测试继续使用 mock transport 保持稳定。

## 2026-06-22 / 真实 connector 与 parser 接入 workflow 前两步

修改文件：
- `README.md`
- `LOG.md`
- `src/medical_research_agent/workflow/__init__.py`
- `src/medical_research_agent/workflow/graph.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/workflow/state.py`
- `examples/run_source_workflow.py`
- `tests/test_workflow_sources.py`

改动摘要：
- 在 workflow state 中新增 `use_real_connectors` 开关，默认 `run_mock_workflow` 仍保持离线 mock 行为。
- 新增 `run_source_workflow`，启用真实 connector/parser 节点，并继续沿用后续 mock 证据与报告节点。
- `search_sources` 在真实模式下调用 PubMed、Crossref、Semantic Scholar 文献 connector；非论文来源暂以 placeholder source 保持计划可追踪。
- `fetch_and_parse_sources` 在真实模式下根据 URL / PDF hint 选择网页或 PDF parser，单个来源失败时记录错误并继续处理其他来源。
- 新增 source workflow 示例脚本和单元测试，覆盖 connector 失败、解析失败、artifact 落盘和 mock 默认行为。

关键决定：
- 真实 connector/parser 接入采用显式开关，避免破坏已有 mock workflow 的稳定离线测试。
- 当前只替换资料检索与文档解析两步；证据抽取、报告写作、PDF 输出仍保持现有 mock/未实现边界。
- 对未实现的厂商/监管 connector 先生成 placeholder source，而不是假装完成真实检索。

后续事项：
- 下一步可把 `extract_evidence` 从 mock 改为基于 `ParsedDocument` 的结构化证据抽取。
- 为真实网络模式增加限速、重试、缓存和更细粒度 source-level status。
- 后续实现厂商公开资料、监管资料 connector 后替换 placeholder source。

## 2026-06-22 / 厂商公开资料与监管资料 connector 接入

修改文件：
- `README.md`
- `LOG.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/connectors/__init__.py`
- `src/medical_research_agent/connectors/web_search.py`
- `src/medical_research_agent/connectors/openfda.py`
- `src/medical_research_agent/connectors/clinical_trials.py`
- `src/medical_research_agent/workflow/nodes.py`
- `tests/test_connectors_sources.py`
- `tests/test_workflow_sources.py`

改动摘要：
- 新增 DuckDuckGo HTML 公开网页搜索 connector，用于厂商公开手册、规格页和 PDF 线索检索，输出 `vendor_public_doc` 或指定公开来源类型。
- 新增 openFDA device 510(k) connector，输出 FDA 510(k) 监管来源元数据。
- 新增 ClinicalTrials.gov v2 studies connector，输出临床试验注册来源元数据。
- `run_source_workflow` 的真实检索模式不再为厂商/监管来源生成 placeholder，而是调用对应 connector；解析节点继续按 URL/PDF hint 抽取网页或 PDF 文本。
- 补充 connector 和 workflow 测试，覆盖厂商网页搜索、openFDA、ClinicalTrials.gov、真实 workflow 多类来源接入。

关键决定：
- 厂商资料暂采用无 key 的公开网页搜索作为最小实现，metadata 中保留 connector、rank 和文档格式 hint；后续可替换为指定厂商站点 connector 或正式搜索 API。
- 监管资料先接入 FDA 510(k) 与 ClinicalTrials.gov 两类公开 API，暂不处理 NMPA/NICE 等需要更多字段设计的数据源。
- 各 connector 仍只返回 `SourceRecord`，不做证据判断；厂商宣传资料与监管/临床资料的解释边界留给后续证据抽取和核查模块。

后续事项：
- 为厂商搜索增加域名白名单/黑名单、PDF 优先、去重和搜索结果可信度标注。
- openFDA 查询语法需要在真实样例上继续调优，特别是产品名、申请人和 product code 的组合检索。
- 后续可新增 FDA PMA、FDA device recall、NMPA、NICE、EUDAMED 等监管 connector。

## 2026-06-23 / 本地上传私有资料 ingestion 最小版本

修改文件：
- `README.md`
- `LOG.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/parsers/__init__.py`
- `src/medical_research_agent/parsers/local_files.py`
- `examples/ingest_local_files.py`
- `tests/test_local_file_ingestion.py`

改动摘要：
- 新增 `LocalFileIngestor`，支持将本地 PDF、Markdown、TXT、DOCX 文件转换为 `SourceRecord` 与 `ParsedDocument`。
- 本地文件统一标记为 `user_uploaded_private`，metadata 中记录 `privacy=local_only`、文件名、后缀、大小、SHA-256 和格式 hint。
- PDF 复用现有 `PDFParser.parse_bytes`；Markdown/TXT 直接按 UTF-8 读取；DOCX 使用标准库 zip/XML 提取段落文本。
- 新增 `examples/ingest_local_files.py`，可把本地文件解析结果保存为 `sources.json` / `documents.json`。
- 新增测试覆盖 Markdown、TXT、PDF、DOCX、未知格式和缺失文件。

关键决定：
- 当前最小版本不解析旧二进制 `.doc`，只支持 `.docx`，避免引入重依赖或桌面 Office 自动化。
- 用户上传资料默认只做本地处理，不调用外部 LLM 或搜索 API；隐私边界由 `SourceType.USER_UPLOADED_PRIVATE` 和 metadata 明确标记。
- 不修改核心 schema，继续复用 `SourceRecord.local_path`、`SourceRecord.metadata` 和 `ParsedDocument.metadata` 承载本地文件信息。

后续事项：
- 将本地 ingestor 接入 workflow 的任务输入，让一个任务同时包含公开来源与本地私有资料。
- 为 DOCX 增加表格、页眉页脚、批注等更完整抽取；如需读取旧 `.doc`，再评估轻量转换或 OfficeCLI/LibreOffice 流程。
- 后续证据抽取阶段必须继续尊重 `user_uploaded_private` 的外发限制。

## 2026-07-06 / 线程 019eee47 迁移交接

修改文件：
- `LOG.md`

本线程已完成工作：
- 搭建并验证 LangGraph mock workflow 骨架，包含 `parse_intent`、`plan_research`、`search_sources`、`fetch_and_parse_sources`、`extract_evidence`、`deduplicate_evidence`、`plan_report`、`write_report`、`verify_claims`、`render_outputs` 等节点。
- 新增 workflow 状态结构、节点日志和中间状态落盘机制，mock 运行可生成 `sources.json`、`documents.json`、`evidence.json`、`claims.json`、`report.md`、`workflow_state.json`、`run.log`。
- 新增可替换 LLM 调用层，包含默认 `MockLLMClient`、OpenAI-compatible HTTP client、LLM 请求/响应模型，以及公开/私有来源外发隐私门禁。
- 新增资料检索 connector 基础接口和最小公开数据源 connector，包括 PubMed、Crossref、Semantic Scholar、公开 URL、DuckDuckGo HTML 厂商资料搜索、openFDA 510(k)、ClinicalTrials.gov。
- 新增网页/PDF parser，以及本地上传私有资料 ingestion 最小版本，支持 PDF、Markdown、TXT、DOCX，并统一标记 `user_uploaded_private`。
- 将真实 connector/parser 接入 workflow 前两步，保留 `run_mock_workflow` 离线 mock 路径，并新增真实来源 workflow 入口。
- 补充 README、示例脚本和测试，覆盖 schema、报告模板、workflow、LLM client、connector、parser、本地文件 ingestion 等关键模块。

主要改动文件/目录：
- `pyproject.toml`
- `.env.example`
- `README.md`
- `src/medical_research_agent/config.py`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/workflow/`
- `src/medical_research_agent/llm/`
- `src/medical_research_agent/connectors/`
- `src/medical_research_agent/parsers/`
- `src/medical_research_agent/io.py`
- `examples/`
- `tests/`
- `LOG.md`

当前状态：
- 项目已经从纯 schema/模板骨架推进到可运行的 workflow 骨架，并具备 mock 离线闭环、可替换 LLM 层、部分真实公开来源检索、网页/PDF 解析、本地私有文件 ingestion。
- 默认路径仍应优先使用 mock/offline 测试，真实网络 connector 作为显式开启能力，不应让基础测试依赖外部网络。
- 用户私有资料默认本地处理，禁止默认发送外部 LLM；外发私有内容必须显式配置并确认。
- 本线程未提交、未 push；迁移前应在新电脑上重新检查工作树和测试状态。

未完成事项/阻塞点：
- 证据抽取仍主要是 mock，需要接入基于 `ParsedDocument` 的真实结构化抽取逻辑。
- 报告写作、claim verifier、引用核查仍未接入真实 LLM/证据链，后续应分节点替换 mock 实现。
- PDF 渲染、FastAPI、前端工作台尚未实现。
- 真实 connector 还需要补充限速、重试、缓存、分页、去重、网络集成测试和更稳健的错误恢复。
- PDF parser 尚未支持扫描件 OCR、表格抽取、精确页码定位；DOCX ingestion 仍是最小段落提取。
- 厂商与监管 connector 仍需更多真实样例调优，如 FDA PMA、recall、NMPA、NICE、EUDAMED 等来源尚未接入。

迁移到另一台电脑继续接手注意事项：
- 新线程开始仍需先读 `AGENTS.md`、开发周期计划表和 `LOG.md` 最新记录。
- 涉及 git 操作必须继续使用完整路径 `D:\Users\gongjx\AppData\Local\Programs\Git\mingw64\bin\git.exe`，不要直接调用普通 `git`。
- 按 README / `.codex/setup.ps1` 重建 `.venv`，并确认 `.env`、`data/`、`outputs/`、`cache/`、`uploads/` 等本地文件不提交。
- 不要改动两份既有调研草稿：`DBS脑电采集电极要求调研_加强版.md` 和 `SCS刺激参数调研.md`。
- API key 不应写入 git；如需真实 LLM，使用 `.env` 中的 `MEDICAL_RESEARCH_LLM_*` 配置，并优先保持 `MEDICAL_RESEARCH_ALLOW_EXTERNAL_LLM_FOR_PRIVATE_SOURCES=false`。
- 下一步建议优先做真实证据抽取节点，保持 `EvidenceItem` / `ProductSpec` / `Claim` schema 对齐，并继续保留 mock 测试路径。

## 2026-07-06 / 线程 019eee50 迁移交接

修改文件：
- `LOG.md`

本线程已完成的主要工作：
- 搭建并扩展资料检索 connector 与文档解析模块，形成统一 `SourceRecord` / `ParsedDocument` 输出链路。
- 新增公开论文检索 connector：PubMed / NCBI E-utilities、Crossref、Semantic Scholar（预留可选 API key）。
- 新增公开网页与 URL 来源处理：普通 URL source 归一化、网页正文解析、PDF URL 下载与文本抽取。
- 新增厂商公开资料和监管资料最小 connector：DuckDuckGo HTML 搜索作为厂商公开手册/规格/PDF 线索的临时无 key 入口；openFDA device 510(k)；ClinicalTrials.gov v2 studies。
- 将真实 connector/parser 接入 LangGraph workflow 的 `search_sources` 与 `fetch_and_parse_sources` 两步，保留 `run_mock_workflow` 离线 mock 行为，并新增 `run_source_workflow` 真实检索/解析入口。
- 新增本地上传私有资料 ingestion 能力：支持 PDF、Markdown、TXT、DOCX，统一标记 `user_uploaded_private` 与 `privacy=local_only`，生成 `SourceRecord` 和 `ParsedDocument`。
- 用两份用户样例验证本地解析：`RTScale产品规格书-简洁版.docx` 可抽取 DOCX 段落/表格文本；`DSY202509面向电动汽车充电桩接入的配电网承载力分析与提升技术研究（任务书下达稿）.pdf` 可抽取 58 页、约 40469 字文本。

本线程涉及的主要代码/文档文件：
- `pyproject.toml`
- `.env.example`
- `README.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/config.py`
- `src/medical_research_agent/io.py`
- `src/medical_research_agent/connectors/__init__.py`
- `src/medical_research_agent/connectors/base.py`
- `src/medical_research_agent/connectors/pubmed.py`
- `src/medical_research_agent/connectors/crossref.py`
- `src/medical_research_agent/connectors/semantic_scholar.py`
- `src/medical_research_agent/connectors/url.py`
- `src/medical_research_agent/connectors/web_search.py`
- `src/medical_research_agent/connectors/openfda.py`
- `src/medical_research_agent/connectors/clinical_trials.py`
- `src/medical_research_agent/parsers/__init__.py`
- `src/medical_research_agent/parsers/web.py`
- `src/medical_research_agent/parsers/pdf.py`
- `src/medical_research_agent/parsers/local_files.py`
- `src/medical_research_agent/workflow/__init__.py`
- `src/medical_research_agent/workflow/graph.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/workflow/state.py`
- `examples/search_sources.py`
- `examples/run_source_workflow.py`
- `examples/ingest_local_files.py`
- `tests/test_connectors_sources.py`
- `tests/test_parsers_documents.py`
- `tests/test_workflow_sources.py`
- `tests/test_local_file_ingestion.py`

当前状态：
- 最后一次完整测试命令：`cmd /c ".venv\Scripts\python.exe -m pytest tests"`。
- 最后一次测试结果：`31 passed, 1 warning`。warning 来自 `langgraph` 的 pending deprecation，与本线程改动无直接失败关系。
- 现有能力已覆盖：公开论文检索、厂商网页线索检索、FDA/ClinicalTrials 监管检索、网页/PDF 解析、本地 PDF/MD/TXT/DOCX 私有资料解析、workflow 前两步真实接入。
- 两份既有调研草稿 `DBS脑电采集电极要求调研_加强版.md` 与 `SCS刺激参数调研.md` 未被本线程修改。
- 未提交、未 push；当前仅按迁移要求追加本条 `LOG.md` 记录。

未完成事项 / 阻塞点：
- 尚未实现真实证据抽取，`extract_evidence` 仍为 mock 逻辑；下一阶段应从 `ParsedDocument` 抽取 `EvidenceItem` / `ProductSpec`。
- 本地私有资料 ingestion 尚未正式接入 workflow 任务输入；目前可通过 `examples/ingest_local_files.py` 单独解析。
- DuckDuckGo HTML 搜索只是厂商公开资料检索的无 key MVP 入口，长期建议替换或增强为 Tavily/Bing/SerpAPI、指定厂商站点 connector、域名白名单和去重策略。
- openFDA 查询语法仍需用真实医疗/器械样例继续调优；NMPA、NICE、FDA PMA、FDA recall、EUDAMED 等监管 connector 尚未接入。
- PDF 解析目前主要依赖 `pypdf` 文本层；扫描件 OCR、表格结构化、页码定位、图资产抽取仍未实现。
- DOCX 解析当前使用标准库 zip/XML 抽正文，未完整保留表格结构、页眉页脚、批注等；旧 `.doc` 暂不支持。
- 尚未实现真实报告写作、引用核查、PDF 输出、FastAPI 后端和前端。

另一台电脑接手注意事项：
- 新线程开始前继续按项目规则先读 `AGENTS.md`、`医疗产品调研Agent开发周期计划表.md`、`LOG.md` 最新记录和相关代码。
- 迁移时不要提交 `.env`、`.venv/`、`data/`、`outputs/`、`cache/`、`uploads/` 或用户上传私有文档；这些目录和文件按本地优先/隐私规则处理。
- 新机器需重新创建 Python 虚拟环境并按 `pyproject.toml` 安装依赖；可参考 `.codex/setup.ps1`、`.codex/actions.ps1` 和 README 中的命令。
- 如果继续在原机器做 git 操作，必须使用 `D:\Users\gongjx\AppData\Local\Programs\Git\mingw64\bin\git.exe`；迁移到新机器后应确认 Git 可执行路径是否变化，并同步更新协作约定或本机说明。
- 私有资料进入 LLM 前必须继续走隐私门禁，默认不得外发 `user_uploaded_private` / `internal_private` 内容。
- 本线程产生的本地解析样例输出位于 `outputs/local_ingest_rtscale/` 与 `outputs/local_ingest_dsy202509/`，属于运行产物，不应作为代码提交。

## 2026-07-06 / 迁移交接文档汇总

修改文件：
- `HANDOFF.md`
- `LOG.md`

改动摘要：
- 协调线程 `019eca3e`、`019eee47`、`019eee50` 追加迁移交接日志。
- 新增 `HANDOFF.md`，用于另一台电脑的 Codex 接手项目。
- `HANDOFF.md` 汇总了当前完成能力、未完成事项、测试与环境恢复命令、迁移前提交步骤、新电脑接手步骤和下一步开发建议。

关键决定：
- 新电脑接手时优先阅读 `AGENTS.md`、`HANDOFF.md`、`LOG.md`，不要依赖旧电脑的 Codex 对话历史。
- 迁移前必须先把本机未提交代码提交并推送到 GitHub。
- `.env`、`.venv/`、`data/`、`outputs/`、`cache/`、`uploads/` 和用户私有资料仍不得提交。

后续事项：
- 本机执行测试后，将当前开发进度提交并推送到 `https://github.com/anklecrusher/medical-product-research-agent`。

## 2026-07-06 / 线程 019eca3e 迁移交接

修改文件：
- `LOG.md`

本线程已完成的工作：
- 完成项目基础骨架与核心 schema 初始化：新增 `pyproject.toml`、`.env.example`、`README.md`、`src/medical_research_agent/`、`tests/` 等基础文件。
- 配置本机 Python 3.12.9、项目 `.venv`、本地 `.env`、`.vscode/settings.json` 以及 `data/`、`outputs/`、`cache/`、`uploads/` 运行目录；这些本地文件/目录按 `.gitignore` 不提交。
- 新增 Codex worktree 环境脚本：`.codex/setup.ps1`、`.codex/actions.ps1`、`.codex/README.md`，并为未来前端 `package.json` 预留 `npm install` 分支。
- 完成图文增强弹性报告模板：新增 `FigureAsset`、`ReportTemplate`、`ReportTemplateBlock` 等 schema，增加 Jinja2 Markdown 模板和渲染 helper，支持来源图嵌入、图注、来源链接和缺图占位。
- 完成 LangGraph mock workflow 骨架，按主流程跑通 mock 节点并输出 `sources.json`、`documents.json`、`evidence.json`、`claims.json`、`report.md`、`workflow_state.json`、`run.log` 等中间产物。
- 完成可替换 LLM 调用层，默认 `mock` provider，预留 OpenAI-compatible `/chat/completions` HTTP client，并加入私有资料外发门禁。
- 完成资料检索 connector 与文档解析最小版本：PubMed、Crossref、Semantic Scholar、公开 URL、网页解析、PDF 解析，以及 JSON 落盘工具和示例。
- 完成真实 connector/parser 接入 workflow 前两步：`run_source_workflow` 可用真实 connector/parser 替换检索与解析节点，后续证据与报告仍保持 mock。
- 完成厂商公开资料与监管资料 connector 接入：DuckDuckGo HTML 搜索、openFDA 510(k)、ClinicalTrials.gov v2 studies，并替换真实 workflow 中的厂商/监管 placeholder。
- 完成本地上传私有资料 ingestion 最小版本：支持 PDF、Markdown、TXT、DOCX，统一标记为 `user_uploaded_private` 与 `privacy=local_only`。

当前状态：
- 当前仓库有大量未提交变更，`git status --short` 显示 `LOG.md` 已修改，`.codex/`、`.env.example`、`README.md`、`examples/`、`pyproject.toml`、`scripts/`、`src/`、`templates/`、`tests/` 等为未跟踪文件。
- 已多次使用 `.venv\Scripts\python.exe -m pytest` 验证阶段性功能；最近日志记录中测试已覆盖 schema、报告模板、mock workflow、LLM client、connectors/parsers、本地文件 ingestion 等模块。
- 没有执行提交、push 或破坏性 git 操作。

未完成事项 / 阻塞点：
- 真实证据抽取、产品参数抽取、去重与冲突检查、报告大纲生成、章节写作、引用核查和 PDF 渲染仍未完成。
- 真实 connector/parser 已接入 workflow 的检索与解析阶段，但后续证据和报告节点仍是 mock。
- 厂商搜索仍是公开网页搜索最小实现，需后续增加域名白/黑名单、PDF 优先、去重和可信度标注。
- PDF 解析仍是文本级最小实现，尚未支持 OCR、表格抽取、页码级图资产裁取。
- 本地 DOCX ingestion 只做正文段落抽取，尚未处理表格、页眉页脚、批注等复杂结构。
- Node 当前可用来源记录为 CodexTools `node v24.14.0` / `npm 11.9.0`；官方 Node 24.16.0 LTS MSI 曾尝试安装，但当前 shell 仍优先解析到 CodexTools Node。

另一台电脑接手注意事项：
- 新机器开始前必须先读 `AGENTS.md`、`医疗产品调研Agent开发周期计划表.md` 和本 `LOG.md` 最新记录。
- 涉及 git 操作继续使用完整路径：`D:\Users\gongjx\AppData\Local\Programs\Git\mingw64\bin\git.exe`；如果新机器路径不同，应先更新项目约定或在交接中明确替代路径。
- 迁移时需要带走未提交的工作区文件；仅 `git clone` 远程仓库可能拿不到当前所有新增文件，除非先在本机提交并推送。
- `.env`、`.venv/`、`.vscode/`、`data/`、`outputs/`、`cache/`、`uploads/` 是本地运行环境/产物，不应提交；新机器应重新运行 `.codex/setup.ps1` 或手动创建虚拟环境并安装依赖。
- 推荐在新机器执行：`powershell -ExecutionPolicy Bypass -File .codex/setup.ps1`，再执行：`powershell -ExecutionPolicy Bypass -File .codex/actions.ps1 test` 验证环境。
- 私有上传资料仍必须默认本地处理，不得发送外部 LLM；后续接入真实 LLM 时必须继续使用现有隐私门禁。

## 2026-07-06 / 线程 019eee50 迁移交接

修改文件：
- `LOG.md`

本线程已完成的主要工作：
- 负责资料检索 connector 与文档解析模块收尾，形成从检索/抓取/解析到统一 `SourceRecord` 与 `ParsedDocument` 的最小链路。
- 新增并验证公开论文 connector：PubMed / NCBI E-utilities、Crossref、Semantic Scholar（预留可选 API key）。
- 新增并验证普通 URL、网页正文解析、PDF URL 下载与文本抽取能力。
- 新增厂商公开资料和监管资料最小 connector：DuckDuckGo HTML 搜索作为厂商公开手册/规格/PDF 线索的临时无 key 入口；openFDA device 510(k)；ClinicalTrials.gov v2 studies。
- 将真实 connector/parser 接入 LangGraph workflow 的 `search_sources` 与 `fetch_and_parse_sources` 两步，保留 `run_mock_workflow` 离线 mock 行为，并新增 `run_source_workflow` 真实检索/解析入口。
- 新增本地上传私有资料 ingestion：支持 PDF、Markdown、TXT、DOCX，统一标记 `user_uploaded_private` 与 `privacy=local_only`，输出 `SourceRecord` 和 `ParsedDocument`。
- 用两份用户样例做过本地解析验证：`RTScale产品规格书-简洁版.docx` 可抽取 DOCX 文本；`DSY202509面向电动汽车充电桩接入的配电网承载力分析与提升技术研究（任务书下达稿）.pdf` 可抽取 58 页、约 40469 字文本。

本线程涉及的主要代码/文档文件：
- `pyproject.toml`
- `.env.example`
- `README.md`
- `src/medical_research_agent/__init__.py`
- `src/medical_research_agent/config.py`
- `src/medical_research_agent/io.py`
- `src/medical_research_agent/connectors/__init__.py`
- `src/medical_research_agent/connectors/base.py`
- `src/medical_research_agent/connectors/pubmed.py`
- `src/medical_research_agent/connectors/crossref.py`
- `src/medical_research_agent/connectors/semantic_scholar.py`
- `src/medical_research_agent/connectors/url.py`
- `src/medical_research_agent/connectors/web_search.py`
- `src/medical_research_agent/connectors/openfda.py`
- `src/medical_research_agent/connectors/clinical_trials.py`
- `src/medical_research_agent/parsers/__init__.py`
- `src/medical_research_agent/parsers/web.py`
- `src/medical_research_agent/parsers/pdf.py`
- `src/medical_research_agent/parsers/local_files.py`
- `src/medical_research_agent/workflow/__init__.py`
- `src/medical_research_agent/workflow/graph.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/workflow/state.py`
- `examples/search_sources.py`
- `examples/run_source_workflow.py`
- `examples/ingest_local_files.py`
- `tests/test_connectors_sources.py`
- `tests/test_parsers_documents.py`
- `tests/test_workflow_sources.py`
- `tests/test_local_file_ingestion.py`

当前状态：
- 最后一次完整测试命令：`cmd /c ".venv\Scripts\python.exe -m pytest tests"`。
- 最后一次测试结果：`31 passed, 1 warning`；warning 来自 `langgraph` pending deprecation。
- 现有能力已覆盖：公开论文检索、厂商网页线索检索、FDA/ClinicalTrials 监管检索、网页/PDF 解析、本地 PDF/MD/TXT/DOCX 私有资料解析、workflow 前两步真实接入。
- 两份既有调研草稿 `DBS脑电采集电极要求调研_加强版.md` 与 `SCS刺激参数调研.md` 未被本线程修改。
- 未提交、未 push；本次迁移收尾只追加 `LOG.md`。

未完成事项 / 阻塞点：
- 尚未实现真实证据抽取，`extract_evidence` 仍为 mock；下一阶段应从 `ParsedDocument` 抽取 `EvidenceItem` / `ProductSpec`。
- 本地私有资料 ingestion 尚未正式接入 workflow 任务输入；目前通过 `examples/ingest_local_files.py` 单独解析。
- DuckDuckGo HTML 搜索只是厂商公开资料检索的无 key MVP，后续建议替换或增强为 Tavily/Bing/SerpAPI、指定厂商站点 connector、域名白名单和去重策略。
- openFDA 查询语法仍需真实样例调优；NMPA、NICE、FDA PMA、FDA recall、EUDAMED 等监管 connector 尚未接入。
- PDF 解析目前主要依赖 `pypdf` 文本层；扫描件 OCR、表格结构化、页码定位、图资产抽取仍未实现。
- DOCX 解析当前使用标准库 zip/XML 抽正文，未完整保留表格结构、页眉页脚、批注等；旧 `.doc` 暂不支持。
- 真实报告写作、引用核查、PDF 输出、FastAPI 后端和前端均未实现。

另一台电脑继续接手时需要注意：
- 新线程开始前继续按项目规则先读 `AGENTS.md`、`医疗产品调研Agent开发周期计划表.md`、`LOG.md` 最新记录和相关代码。
- 迁移时不要提交 `.env`、`.venv/`、`data/`、`outputs/`、`cache/`、`uploads/` 或用户上传私有文档；这些是本地运行环境/产物或私有数据。
- 新机器需重新创建 Python 虚拟环境并按 `pyproject.toml` 安装依赖；可参考 `.codex/setup.ps1`、`.codex/actions.ps1` 和 README。
- 如果继续在原机器做 git 操作，必须使用 `D:\Users\gongjx\AppData\Local\Programs\Git\mingw64\bin\git.exe`；迁移到新机器后应确认 Git 路径是否变化，并更新交接说明或本机约定。
- 私有资料进入 LLM 前必须继续走隐私门禁，默认不得外发 `user_uploaded_private` / `internal_private` 内容。
- 本线程产生的本地解析样例输出位于 `outputs/local_ingest_rtscale/` 与 `outputs/local_ingest_dsy202509/`，属于运行产物，不应作为代码提交。
