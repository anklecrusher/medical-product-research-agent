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

## 2026-07-07 / Todo 8 CLI 文档与日志更新

修改文件：

- `examples/run_source_workflow.py`
- `README.md`
- `LOG.md`
- `.omo/evidence/task-8-mvp-flow-reroute.md`

改动摘要：

- 更新 `run_source_workflow.py` 的说明与终端输出，去掉源工作流仍使用 mock evidence/report 节点的旧表述。
- CLI 运行结束后现在打印 sources、documents、evidence、claims、artifacts、errors 计数，并逐项列出 `sources.json`、`documents.json`、`evidence.json`、`claims.json`、`report.md`、`report.pdf`、`workflow_state.json`、`run.log` 的路径。
- 更新 README 源工作流章节，明确当前 CLI-first 路径会写出 Markdown 报告与 `report.pdf`，并列出完整产物清单。
- 新增 Todo 8 证据文件，记录 help、CLI smoke、stale-language scan、dirty worktree 与运行产物清理结果。

关键决定：

- 本次只更新 CLI/docs/log/evidence 表面，不修改核心 workflow、evidence、report 或 PDF 生成逻辑。
- README 只记录产物名称和运行命令，不记录 `.env`、API key、运行时文件正文或私有资料内容。
- 现场 CLI smoke 产生的 `outputs/task8_source_workflow_check/` 仅用于验证 stdout 路径展示，检查后已删除，保持运行产物不进入提交范围。

测试与检查：

- `.\.venv\Scripts\python.exe examples\run_source_workflow.py --help` 成功。
- `.\.venv\Scripts\python.exe -m py_compile examples\run_source_workflow.py` 成功。
- `.\.venv\Scripts\python.exe examples\run_source_workflow.py '调研 DBS 电极阻抗的论文证据' --output-dir outputs\task8_source_workflow_check` 成功，stdout 打印完整产物路径；该 live smoke 出现 5 条 connector/parser 错误但 workflow 仍生成可定位产物路径，后续 Todo 9 继续做完整 artifact audit。
- stale-language scan 在 `README.md`、`examples/run_source_workflow.py`、`LOG.md` 中未发现源工作流旧占位说明。
- 使用 `C:\Users\ankle crusher\scoop\apps\git\current\cmd\git.exe status --short` 检查工作区；当前仍包含其他 Todo 已产生的 AGENTS、pyproject、workflow、测试和新模块变更，本次未回退他人改动。

后续事项：

- Todo 9 继续执行 deterministic end-to-end CLI smoke 和 artifact audit，验证 JSON 可解析、PDF 头、workflow_state 与报告内容。
- 后续如要提交，继续排除 `.env`、`.venv/`、`data/`、`outputs/`、`cache/`、`uploads/` 和私有资料。

## 2026-07-07 / MVP flow reroute 完整实现与最终合规修正

修改文件：

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `examples/run_source_workflow.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/evidence.py`
- `src/medical_research_agent/evidence_dedup.py`
- `src/medical_research_agent/claim_verifier.py`
- `src/medical_research_agent/report_models.py`
- `src/medical_research_agent/report_content.py`
- `src/medical_research_agent/report_sections.py`
- `src/medical_research_agent/report_writer.py`
- `src/medical_research_agent/renderers/__init__.py`
- `src/medical_research_agent/renderers/pdf.py`
- `tests/test_evidence.py`
- `tests/test_evidence_dedup.py`
- `tests/test_claim_verifier.py`
- `tests/test_report_writer.py`
- `tests/test_pdf_renderer.py`
- `tests/test_mvp_flow_expectations.py`
- `.omo/plans/mvp-flow-reroute.md`
- `.omo/evidence/task-1-mvp-flow-reroute.md` through `.omo/evidence/task-10-mvp-flow-reroute.md`
- `.omo/evidence/mvp-flow-reroute-gate-review.md`
- `.omo/evidence/f1-fix-mvp-flow-reroute.md`
- `LOG.md`

改动摘要：

- 本条记录补全 2026-07-07 `mvp-flow-reroute` 的完整实现事实，并取代上一条 “Todo 8 CLI 文档与日志更新” 可能造成的误解：Todo 8 只记录 CLI/docs 表面更新，不代表整个实现范围。
- 将源工作流从早期 mock evidence/report 终点重路由为 CLI-first MVP 闭环：检索与解析后进入确定性证据抽取、证据去重、报告章节生成、claim 核查和 PDF 渲染。
- 新增结构化证据抽取与产品参数抽取逻辑，保持来源链接、来源类型、隐私标记、单位/参数字段和 `needs_review` 状态可追溯。
- 新增证据去重与冲突标记，用于合并重复证据、保留来源边界，并在冲突或缺证据时显式要求人工复核。
- 新增报告数据模型、章节规划/正文生成和 Markdown 写作模块，使输出更贴近医疗产品经理调研报告：关键结论、参数表、证据表、风险/未确认项和参考来源。
- 新增 claim verifier，将报告中的关键结论与证据支撑状态关联，避免把厂商宣传、单篇论文或未确认信息写成确定性结论。
- 新增 ReportLab PDF renderer，并把 `report.pdf` 纳入 CLI 产物清单；`report.md` 和 `report.pdf` 都作为最终可分享/归档产物。
- 更新 CLI 示例和 README，使 `examples/run_source_workflow.py` 输出 sources、documents、evidence、claims、artifacts、errors 计数，并列出 `sources.json`、`documents.json`、`evidence.json`、`claims.json`、`report.md`、`report.pdf`、`workflow_state.json`、`run.log` 路径。
- 新增针对 evidence、dedup、claim verifier、report writer、PDF renderer 和完整 MVP flow 预期的测试。
- 清理最终合规阻塞：`outputs/f3_mvp_flow_smoke/` 运行目录已不存在；旧 Task 9 gate review 的 `REJECT` 已在证据中标注为被后续 exit-code receipt 和确认性审查 supersede。

关键决定：

- 继续保持 CLI-first MVP，不引入 FastAPI、React/Vite、数据库任务存储、auth 或 dashboard。
- 本轮不引入自由自治 agent；工作流仍按 `AGENTS.md` 的 workflow-first 原则通过明确节点和中间产物传递状态。
- 源工作流的证据/报告/PDF生成采用确定性本地逻辑，不调用 LLM；私有来源仍默认本地处理，外部 LLM 门禁保持不放松。
- 新增 PDF 能力选择轻量稳定的 `reportlab>=4.2,<5`，不为 MVP 引入更重的浏览器渲染链路。
- 运行产物、私有资料和缓存继续通过 `.gitignore` 排除；`.omo/evidence/` 只保存审查证据，不保存私有正文或运行输出目录。
- 旧日志中 “真实证据抽取、报告写作、引用核查、PDF 输出尚未实现” 的状态已被本条记录 supersede；当前剩余问题应按下方后续事项理解。

测试与检查：

- `.\.venv\Scripts\python.exe -m pytest -q` 通过：`47 passed, 1 warning`；warning 来自已安装 `langgraph` 包的 pending deprecation。
- Task 9 CLI smoke 后续补充了直接 exit-code receipt：`LASTEXITCODE: 0`，并确认生成 `report.pdf` 后清理 smoke 输出目录。
- Task 9 artifact audit 可解析 JSON，并记录 `workflow_state.json` 结束在 `render_outputs`、task status 为 `completed`、`report.pdf` 以 `%PDF` 开头、`report.md` 无 stale Mock wording、recoverable connector/parser errors 被记录。
- Todo 10 检查确认 `outputs/`、`data/`、`cache/`、`uploads/` 被 `.gitignore` 忽略，运行根目录为空，已知 smoke 输出目录不存在。
- F1 修正检查确认 `outputs/f3_mvp_flow_smoke/` 不存在，`LOG.md` 已补全完整实现记录，旧 Task 9 `REJECT` 已有 supersession note。

后续事项：

- 提交前仍需决定是否纳入 `.omo` 下的计划/证据文件；`.omo/boulder.json`、`.omo/drafts/`、`.omo/start-work/ledger.jsonl` 属于执行元数据，默认不建议进入普通 feature commit。
- `src/medical_research_agent/workflow/nodes.py` 仍偏大，后续可在不改变行为的前提下拆分节点实现；本次 F1 修正按要求未编辑产品代码。
- 后续可继续增强真实网页/PDF 表格抽取、页码定位、厂商/监管 connector 精度、NMPA/NICE/FDA PMA/recall/EUDAMED 等数据源。
- 如未来接入真实 LLM 章节写作，必须继续保留私有资料默认本地处理和可审计外发门禁。

## 2026-07-08 / Todo 10 research-quality regression fixtures

修改文件：

- `tests/test_research_quality_regressions.py`
- `src/medical_research_agent/workflow/report_nodes.py`
- `.omo/plans/mature-research-agent-architecture.md`
- `.omo/evidence/task-10-mature-research-agent-architecture.md`
- `LOG.md`

改动摘要：

- 新增 Todo 10 no-network research-quality 回归测试，覆盖 UI/manual happy path、UI/manual missing gap、regulatory weak/no-result、vendor competitor/spec，以及 `run_source_workflow(..., output_dir=tmp_path)` integration-style artifact flow。
- 回归断言不只检查 JSON/PDF 存在，还检查 accepted/rejected sources、facet coverage、supported/needs_review claims、status semantics 和 report wording。
- noisy Crossref 数学/laser-plasma 来源必须进入 `rejected_sources`，不得进入 accepted evidence 或报告正文。
- 修正 `render_outputs()`：写入 `workflow_state.json` 的 final state 现在保留 render 节点返回的 artifact path metadata，包括 `rejected_sources_path`。

测试与检查：

- Red receipt：新增回归初跑出现 `KeyError: 'rejected_sources_path'`，确认 serialized workflow state 缺少 render artifact path metadata。
- `.\.venv\Scripts\python.exe -m pytest tests/test_research_quality_regressions.py -q` 通过：`5 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest tests/test_research_quality_regressions.py tests/test_source_relevance.py tests/test_report_outline_planner.py -q` 通过：`9 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest -q` 通过：`88 passed, 1 warning`；warning 仍为已知 LangGraph pending deprecation。
- Manual QA 使用 `.omo\tmp\task10_manual_pytest` 临时目录检查 no-network integration artifacts：accepted=5、rejected=8、evidence=10、status=completed、supported_claims=2；报告包含 `程控 UI / 界面资料` 和 `论文证据不在本节充当产品界面证据`，不包含 noisy Crossref 关键词。检查后已删除临时目录。

后续事项：

- `tests/test_research_quality_regressions.py` 当前正好 250 pure LOC；后续若继续增加场景，应先拆出 fixture/helper 模块。
- Todo 11 可继续执行 live smoke、README/LOG 架构说明补充和运行产物清理。

## 2026-07-08 / Todo 11 mature research architecture live smoke and docs

修改文件：

- `README.md`
- `LOG.md`
- `.omo/evidence/task-11-mature-research-agent-architecture.md`

改动摘要：

- 运行完整测试和原始 UI/程控题目的 live CLI smoke，确认 source workflow 会落盘 `sources.json`、`rejected_sources.json`、`evidence.json`、`claims.json`、`report.md`、`report.pdf`、`workflow_state.json` 和 `run.log`。
- README 补充 mature research workflow 语义：query planning、facet-based source routing、relevance gate、bounded evidence gap loop、以及 `completed` / `needs_more_sources` / `needs_review` 的完成状态边界。
- 记录 live smoke 当前真实结果：pipeline 产物生成成功，但研究状态为 `needs_review`，原因是 live source coverage 仍偏向公开论文，Semantic Scholar 429 与 ClinicalTrials 403 被作为 recoverable/classified errors 记录。
- 使用既有 all-rejected regression 测试覆盖 no-useful-sources failure scenario，确认无有效来源时会写出 rejection evidence 并使用 `needs_more_sources`，而不是伪装成普通成功。
- live smoke 运行目录仅用于审计，证据摘要写入 `.omo/evidence/` 后已删除 `outputs/task11_live_smoke/`。

测试与检查：

- `.\.venv\Scripts\python.exe -m pytest -q` 通过：`88 passed, 1 warning`；warning 仍为已知 LangGraph pending deprecation。
- `.\.venv\Scripts\python.exe examples\run_source_workflow.py "调研交叉刺激与8触点刺激的相关程控逻辑和ui界面" --output-dir outputs\task11_live_smoke` 通过，exit code 0；artifact audit 显示 accepted sources=6、rejected sources=2、documents=6、evidence=6、claims=2、errors=4、task status=`needs_review`、PDF header=`%PDF-`。
- `.\.venv\Scripts\python.exe -m pytest tests\test_source_relevance.py::test_all_rejected_sources_record_needs_more_sources_and_render_json -q` 通过：`1 passed, 1 warning`。
- 使用完整 git 路径检查 runtime 输出：live smoke 目录在清理前只出现在 ignored `outputs/` 下，清理后 `outputs\task11_live_smoke` 不存在。

后续事项：

- Live public-web/vendor/manual evidence coverage 仍不稳定，后续应继续增强 vendor manual、IFU、programmer manual、patent 和监管 connector，而不是把公开论文结果当作 UI/程控产品证据。
- Semantic Scholar 429 和 ClinicalTrials 403 已被分类记录，但后续可增加 API key 配置、限速/backoff 或替代源，提高 live smoke 的可重复性。

## 2026-07-08 / F2 source quality low-relevance blocker fix

修改文件：

- `src/medical_research_agent/source_quality.py`
- `tests/test_source_relevance.py`
- `tests/test_workflow_sources.py`
- `.omo/evidence/f2-source-quality-fix-mature-research-agent-architecture.md`
- `LOG.md`

改动摘要：

- 修复 source quality gate：非 generic、非 mock 来源只要低于既有 `REJECTION_THRESHOLD` 就会被拒绝，不再要求同时命中 hard-coded noise bucket。
- 新增 failing-first regression，覆盖 `vendor_public_doc` / `programmer_ui` 形态但内容完全无医疗/程控相关性的来源，要求 rejected、`relevance=0.0`、reason 为 `low_relevance`。
- 更新旧 workflow source fake connector 的标题/snippet，使其包含真实 DBS/electrode/manual/regulatory 相关文本，避免旧 fixture 依赖零相关占位标题通过 relevance gate。

关键决定：

- 最小修复放在共享 seam `_decision_for_source()`，不新增黑名单词，也不硬编码 reviewer 的 banana-bread 示例。
- 保留 generic plan 和 mock source 的既有兼容行为，避免破坏离线 mock workflow。

测试与检查：

- Red test：`.\.venv\Scripts\python.exe -m pytest tests\test_source_relevance.py::test_zero_relevance_vendor_programmer_ui_source_is_rejected -q` 先失败，失败点为 unrelated source 被 accepted。
- Targeted：`.\.venv\Scripts\python.exe -m pytest tests\test_source_relevance.py -q` 通过：`3 passed, 1 warning`。
- Broader subset：`.\.venv\Scripts\python.exe -m pytest tests\test_research_quality_regressions.py tests\test_source_relevance.py tests\test_report_outline_planner.py -q` 通过：`10 passed, 1 warning`。
- Full suite：`.\.venv\Scripts\python.exe -m pytest -q` 通过：`89 passed, 1 warning`。
- Manual QA：generic unrelated `vendor_public_doc` + `programmer_ui` probe 返回 `accepted=0`、`rejected=1`、`status=needs_more_sources`、`decision=rejected`、`relevance=0.0`。

后续事项：

- `src/medical_research_agent/source_quality.py` 当前 230 pure LOC，处于 warning band；后续若继续扩展 source quality 规则，应先拆分职责。
- 相关证据记录在 `.omo/evidence/f2-source-quality-fix-mature-research-agent-architecture.md`。

## 2026-07-08 / F2 source quality short-token collision fix

修改文件：

- `src/medical_research_agent/source_quality.py`
- `tests/test_source_relevance.py`
- `.omo/evidence/f2-source-quality-short-token-fix-mature-research-agent-architecture.md`
- `LOG.md`

改动摘要：

- 修复 source relevance 的短英文 token 子串误命中：`UI` 不再能命中 `guide` 这类无关英文长词内部。
- 最小改动放在共享 `_matched_terms()` seam：ASCII term 使用词/token 边界匹配；中文等非 ASCII term 保留原有 substring 匹配语义。
- 新增 regression 同时覆盖无关 `guide` collision 被拒绝，以及真实 standalone DBS / programmer UI / interleaving stimulation / 8-contact 来源继续被接受。

测试与检查：

- Red test：`.\.venv\Scripts\python.exe -m pytest tests\test_source_relevance.py::test_short_ui_token_does_not_match_inside_unrelated_words -q` 先失败，失败点为 `Warehouse shelving permit guide` 被纳入 `review.accepted`。
- Targeted regression：同一测试通过，`1 passed, 1 warning`。
- Targeted relevance：`.\.venv\Scripts\python.exe -m pytest tests\test_source_relevance.py -q` 通过，`4 passed, 1 warning`。
- Broader source workflow：`.\.venv\Scripts\python.exe -m pytest tests\test_workflow_sources.py::test_source_workflow_uses_real_connectors_and_parsers -q` 通过，`1 passed, 1 warning`。
- Full suite：`.\.venv\Scripts\python.exe -m pytest -q` 通过，`90 passed, 1 warning`。
- No-excuse：touched Python files 通过，`no violations in 2 file(s)`。
- Adversarial probe：结构化断言确认 unrelated guide source rejected，legitimate DBS programmer UI source accepted。

后续事项：

- `src/medical_research_agent/source_quality.py` 当前 238 pure LOC，仍在 warning band；后续继续扩展 source quality 规则前应优先拆分职责。
- 相关证据记录在 `.omo/evidence/f2-source-quality-short-token-fix-mature-research-agent-architecture.md`。

## 2026-07-09 / Pre-commit review cleanup for mature research architecture

修改文件：

- `src/medical_research_agent/workflow/source_nodes.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/connectors/base.py`
- `tests/test_connector_error_handling.py`
- `tests/test_workflow_sources.py`
- `tests/test_evidence_gap_followup.py`
- `tests/test_research_quality_regressions.py`
- `tests/test_source_relevance.py`
- `LOG.md`

改动摘要：

- 将真实 source connector routing 和 URL/PDF parser 调用从 `workflow/nodes.py` 拆到 `workflow/source_nodes.py`，保留 `nodes.py` 作为 workflow 入口与 mock/evidence 节点聚合，避免单文件继续超过 OMO no-excuse 体积线。
- `SearchRequest` 改为 frozen+slots dataclass，并新增 `SearchRequestError` 表达 query/limit 结构错误；HTTP status classifier 保留开放整数集合的显式 `MATCH_OK` 例外。
- 更新测试 monkeypatch seam 到 `workflow.source_nodes`，避免测试继续依赖旧的大型 `workflow.nodes` 内部实现位置。
- 修复 pre-commit code review 发现的两个阻塞点：`parse failed` 等可恢复 parser 错误不再因宽泛 `failed` marker 被归类为 `TaskStatus.FAILED`；query planning 的短 ASCII trigger（如 `UI`）改为词/token 边界匹配，避免 `guide/guideline` 误触发 `programmer_ui`。
- 本机清理：`.omo/` 作为 OMO 过程/证据目录加入 `.git/info/exclude`，不进入 feature commit；已删除旧的 ignored runtime smoke 目录 `outputs/cross_8contact_stim_ui_visible`。

测试与检查：

- `.\.venv\Scripts\python.exe -m pytest tests\test_workflow_status.py tests\test_research_planning.py tests\test_query_expansion.py -q` 通过：`22 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest tests\test_connector_error_handling.py tests\test_workflow_sources.py tests\test_workflow_mock.py -q` 通过：`10 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest tests\test_evidence_gap_followup.py tests\test_research_quality_regressions.py tests\test_source_relevance.py -q` 通过：`13 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest tests\test_source_relevance.py tests\test_evidence_gap_followup.py tests\test_research_quality_regressions.py tests\test_workflow_sources.py tests\test_connector_error_handling.py -q` 通过：`21 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest -q` 通过：`92 passed, 1 warning`；warning 仍为已知 LangGraph pending deprecation。
- OMO no-excuse 对当前 changed Python files 通过：`no violations in 37 file(s)`。

后续事项：

- `.omo/` 仍保留本地审查与计划证据，但默认不提交；若需要公开过程证据，应单独做 process-artifact commit。
- `outputs/` 保持 ignored runtime 根目录；旧可视 smoke 已删除，后续如需给用户保留运行产物，应明确说明只作本地检查用途。

## 2026-07-09 / Todo 1 deep-free-source LLM configuration doctor

修改文件：

- `examples/check_llm_config.py`
- `src/medical_research_agent/llm/client.py`
- `src/medical_research_agent/llm/doctor.py`
- `tests/test_check_llm_config_cli.py`
- `tests/test_llm_config_doctor.py`
- `README.md`
- `LOG.md`

改动摘要：

- 新增 `examples/check_llm_config.py`，输出 provider/model/base URL/key-present 状态，并保持 API key 只显示为 `api_key_set=true/false`。
- 新增 LLM doctor 模块，支持默认 mock 配置检查、`openai_compatible` 缺 key 非零退出、以及 `--mock-provider-smoke` 的 in-memory OpenAI-compatible `/chat/completions` 测试。
- smoke 通过 fake HTTP transport 走真实 OpenAI-compatible client payload、retry/error、privacy gate 和 provider switching 路径，不需要真实 API key 或外部网络。
- `OpenAICompatibleLLMClient` 增加可注入 HTTP transport 和 sleep hook，用于无网络测试；同时将既有通用异常收敛为 typed exception dataclass，保留原有用户可读错误文本。
- README 补充 LLM doctor 用法、mock smoke 语义、缺 key 行为和 secret redaction 边界。

测试与检查：

- Red receipt：`.\.venv\Scripts\python.exe -m pytest tests\test_llm_config_doctor.py -q` 先失败，原因是 `medical_research_agent.llm.doctor` 尚不存在。
- Focused：`.\.venv\Scripts\python.exe -m pytest tests\test_llm_client.py tests\test_llm_config_doctor.py tests\test_check_llm_config_cli.py -q` 通过：`14 passed`。
- Manual QA：`.\.venv\Scripts\python.exe examples\check_llm_config.py --mock-provider-smoke` 通过，exit code 0，输出 `provider=mock`、`api_key_set=false`、`mock_provider_smoke=ok`、`retry_attempts=1`。
- Manual failure QA：设置 `MEDICAL_RESEARCH_LLM_PROVIDER=openai_compatible` 且不设置 key 后运行 doctor，exit code 1，输出 `api_key_set=false`，stderr 为 `Missing LLM API key...`，未打印 secret。
- OMO no-excuse 对本次 touched Python files 通过：`no violations in 5 file(s)`。

后续事项：

- 本轮仅实现配置 doctor 和 mocked provider smoke；真实 provider smoke 仍应在 `.env` 配置真实 key 后由后续 Todo 13 明确标记并执行。
- LLM 规划、筛源、证据抽取和报告写作仍未接入真实 LLM，本条只完成可执行配置验证入口。

## 2026-07-09 / Todo 3 deep-free-source item-level access verifier

修改文件：

- `src/medical_research_agent/source_access.py`
- `src/medical_research_agent/source_contracts.py`
- `tests/test_free_access_verifier.py`
- `.omo/evidence/task-3-deep-free-source-llm-reporting.md`
- `LOG.md`

改动摘要：

- 新增 item-level `SourceAccessVerifier`，通过 HTTP `HEAD` 和 `GET` fallback 检查具体 URL 的状态码、content type、redirect final URL、PDF/HTML parseability 和 failure reason。
- 覆盖 PubMed abstract、PMC/Europe PMC full text、公开厂商 PDF/manual page、302 redirect、403、404、login marker、paywall marker、DOI metadata-only、parser failure、missing URL/unsupported scheme 和 prompt-injection marker 场景。
- 适配 Todo 2 新增的 `source_contracts.py`：`source_access.py` 不再定义私有 `FreeAccessStatus`/`AccessCheck`，而是返回共享 `AccessCheck`，并通过 `CitationEligibility.from_access_check(...)` 判定最终引用资格。
- 只为共享 `AccessCheck` 补充 verifier 必需的 `status_code`、`redirected`、`failure_reason` 字段，未改动来源 schema 或报告模板。

测试与检查：

- Red test：`.\.venv\Scripts\python.exe -m pytest tests\test_free_access_verifier.py -q` 先失败，原因是 `medical_research_agent.source_access` 尚不存在。
- Focused：`.\.venv\Scripts\python.exe -m pytest tests\test_free_access_contracts.py tests\test_free_access_verifier.py -q` 通过：`19 passed in 14.50s`。
- Broader parser/source subset：`.\.venv\Scripts\python.exe -m pytest tests\test_parsers_documents.py tests\test_connectors_sources.py tests\test_free_access_verifier.py -q` 通过：`28 passed in 32.36s`。
- Full suite：`.\.venv\Scripts\python.exe -m pytest -q` 通过：`121 passed, 1 warning in 58.19s`；warning 仍为既有 LangGraph pending deprecation。
- Manual QA：使用 `httpx.MockTransport` 的 fake PDF 和 fake login page，输出 `Manual: status=pdf_accessible; eligible=True` 与 `Login: status=login_required; eligible=False`。
- OMO no-excuse 对本次 touched Python files 通过：`no violations in 3 file(s)`。
- Duplicate contract check 确认只有 `src/medical_research_agent/source_contracts.py` 定义 `FreeAccessStatus` 和 `AccessCheck`。

后续事项：

- DOI/Crossref 仍保持 metadata-only，后续 Todo 6/8 应只在发现并验证具体免费全文 URL 后再提升为可最终引用。
- 当前 verifier 对未知 content type 保守返回 `needs_review`；后续新增 connector 时可按具体公开来源类型扩展分类规则。

## 2026-07-09 / Todo 2 deep-free-source source strategy and free-access contracts

修改文件：

- `src/medical_research_agent/source_contracts.py`
- `tests/test_free_access_contracts.py`
- `LOG.md`

改动摘要：

- 新增冻结 Pydantic 契约模型：`SourceStrategy`、`SourceRoute`、`AccessCheck`、`CitationEligibility`、`LLMResearchDecision`、`ReportQualityMetric`、`ReportQualityMetrics`。
- 新增 `FreeAccessStatus` 枚举和 `FINAL_CITABLE_ACCESS_STATUSES`，把 final citation eligibility 固化为 URL + 枚举状态的布尔契约，不依赖 prose 约定。
- 新增 unit tests 覆盖 strategy/access/citation/quality metrics 序列化、free PDF/HTML 可最终引用、paywalled/metadata-only/missing URL 不可最终引用、非法 access status 在 Pydantic 边界被拒绝。

关键决定：

- 契约放在新的 `source_contracts.py`，避免继续扩大 `schemas.py` 或已处于 warning band 附近的 `source_quality.py`。
- 本轮只定义 workflow 边界契约，不实现 HTTP 级 item access verifier；实际验证器留给 Todo 3。

测试与检查：

- Red receipt：`.\.venv\Scripts\python.exe -m pytest tests\test_free_access_contracts.py -q` 先失败，原因是 `medical_research_agent.source_contracts` 尚不存在。
- Targeted：`.\.venv\Scripts\python.exe -m pytest tests\test_free_access_contracts.py -q` 通过：`4 passed`。
- Broader subset：`.\.venv\Scripts\python.exe -m pytest tests\test_schemas_import.py tests\test_research_planning.py tests\test_source_relevance.py -q` 通过：`13 passed, 1 warning`。
- Full suite：`.\.venv\Scripts\python.exe -m pytest -q` 通过：`121 passed, 1 warning`；warning 仍为已知 LangGraph pending deprecation。
- Manual QA：Python one-liner 构造 `pdf_accessible` 与 `metadata_only` access checks，输出 PDF `eligible=true`、metadata-only `eligible=false`。
- OMO no-excuse 对本轮 touched Python files 通过：`no violations in 2 file(s)`；pure LOC 为 `source_contracts.py=97`、`test_free_access_contracts.py=100`。

后续事项：

- Todo 3 应复用或对齐本轮 `FreeAccessStatus` / `AccessCheck` / `CitationEligibility`，避免另建平行 free-access 语义。

## 2026-07-09 / Todo 4 deep-free-source report quality evaluator

修改文件：

- `src/medical_research_agent/report_quality.py`
- `tests/test_report_quality_evaluator.py`
- `.omo/evidence/task-4-deep-free-source-llm-reporting.md`
- `LOG.md`

改动摘要：

- 新增 deterministic `evaluate_report_quality(...)`，按核心结论、Markdown 表格、来源类型多样性、supported claim、免费可引用链接、主题章节、未确认项表达、引用密度和 PDF 可读性评估报告质量。
- 评估输入使用 typed `ReportQualityArtifacts`、`AccessCheck`、`Claim` 和可选 `SourceRecord`，复用 `CitationEligibility.from_access_check(...)`，没有新增平行 free-access 语义。
- 新增 fixture tests 覆盖 weak/template-only 报告失败、长但无支持报告失败，以及设备参数调研和公司/监管动态两种不同研究形态通过，避免硬编码 DBS、疾病、公司或单一 benchmark。

测试与检查：

- Red receipt：`.\.venv\Scripts\python.exe -m pytest tests\test_report_quality_evaluator.py -q` 先失败，原因是 `medical_research_agent.report_quality` 尚不存在。
- Focused：`.\.venv\Scripts\python.exe -m pytest tests\test_report_quality_evaluator.py -q` 通过：`4 passed`。
- Broader subset：`.\.venv\Scripts\python.exe -m pytest tests\test_report_quality_evaluator.py tests\test_report_writer.py tests\test_report_templates.py tests\test_research_quality_regressions.py -q` 通过：`14 passed, 1 warning`。
- Full suite：`.\.venv\Scripts\python.exe -m pytest -q` 通过：`125 passed, 1 warning`；warning 仍为既有 LangGraph pending deprecation。
- Manual QA：Python stdin command 构造 weak/good fixture，输出 `weak: passed=False; score=0.00; ...` 与 `good: passed=True; score=1.00; reasons=[]`。
- OMO no-excuse 对本次 touched Python files 通过：`no violations in 2 file(s)`；pure LOC 为 `report_quality.py=134`、`test_report_quality_evaluator.py=127`。

后续事项：

- Todo 12 可将该 evaluator 接入 workflow completion/status policy；本轮未改 workflow、source access/contracts 或报告渲染路径。

## 2026-07-09 / Todo 1 LLM doctor sentinel cleanup

修改文件：

- `src/medical_research_agent/llm/doctor.py`
- `tests/test_llm_config_doctor.py`
- `tests/test_check_llm_config_cli.py`
- `.omo/evidence/task-1-deep-free-source-llm-reporting.md`
- `LOG.md`

改动摘要：

- 将 LLM doctor 内部 smoke key 与 redaction 测试里的假 token 改为 `doctor-fake-*` 形态，避免测试/证据中的非真实值被 secret scanner 误判。
- 保留 stdout/stderr redaction 断言，继续验证 sentinel 不会出现在诊断输出中。
- 更新 Todo 1 evidence，移除旧的 secret-shaped fake-token 示例描述。

测试与检查：

- secret-shaped token 与 literal authorization-token 扫描仅剩安全误报：`LOG.md` 中历史 `.omo/evidence/task-*` 路径、`examples/ingest_local_files.py` 的 `--task-id` 帮助文本、LLM client 动态 authorization header 构造、LLM doctor authorization prefix 校验；没有剩余 fake API key literal。
- `.\.venv\Scripts\python.exe -m pytest tests\test_llm_config_doctor.py tests\test_check_llm_config_cli.py tests\test_llm_client.py -q` 通过：`14 passed in 2.66s`。
- OMO no-excuse 对本次 touched Python files 通过：`no violations in 3 file(s)`。

## 2026-07-09 / Todo 8 deep-free-source LLM source triage and bounded gap loop

修改文件：

- `src/medical_research_agent/source_triage.py`
- `src/medical_research_agent/source_triage_models.py`
- `src/medical_research_agent/workflow/source_nodes.py`
- `src/medical_research_agent/workflow/follow_up.py`
- `tests/test_llm_source_triage.py`
- `tests/test_follow_up_source_triage.py`
- `tests/test_evidence_gap_followup.py`
- `.omo/evidence/task-8-deep-free-source-llm-reporting.md`
- `.omo/plans/deep-free-source-llm-reporting.md`
- `.omo/start-work/ledger.jsonl`
- `LOG.md`

改动摘要：

- 新增 LLM-assisted source triage 组合层：先复用 deterministic `source_quality` gate，再读取 connector/access verifier 已写入的 `access_check` / `citation_eligibility`，最后用结构化 LLM JSON 对候选来源做 topic fit、facet fit、source type fit 和 citation usability 判定。
- LLM triage 输出使用 Pydantic schema 校验；malformed JSON、缺 key、provider unsupported、LLM request failure、privacy block 都会退回 deterministic + access gate 并写入 audit reason，不让自由文本直接通过。
- 明确防护 source text prompt injection：来源 title/snippet/abstract 被视为不可信文本，不能覆盖 privacy、free-link、citation 或 bounded-search 规则。
- real connector search 现在通过 `review_sources_with_configured_llm_triage(...)` 输出 accepted/rejected/pending_review，并把 pending 作为 rejected audit 保留在 workflow state。
- bounded follow-up 搜索现在也经过 triage；follow-up metadata 保留 `gap_facet`、`gap_description`、`follow_up_round` 和 `bounded`，并在解析前拒绝 paywalled/login/metadata-only 等不可最终引用来源。
- 为新增 follow-up triage 回归拆出 `tests/test_follow_up_source_triage.py`，避免 `tests/test_evidence_gap_followup.py` 超过 OMO 250 LOC 规则。

测试与检查：

- `.\.venv\Scripts\python.exe -m pytest tests\test_llm_source_triage.py tests\test_evidence_gap_followup.py tests\test_follow_up_source_triage.py -q` 通过：`10 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest tests\test_source_relevance.py tests\test_source_routing.py tests\test_workflow_sources.py tests\test_research_quality_regressions.py -q` 通过：`13 passed, 1 warning`。
- `.\.venv\Scripts\python.exe -m pytest -q` 通过：`147 passed, 1 warning`。
- OMO no-excuse 对 Todo 8 touched Python files 通过：`no violations in 7 file(s)`。
- 体积检查：`source_triage.py=225`、`source_triage_models.py=213`、`workflow/source_nodes.py=218`、`workflow/follow_up.py=220`、`tests/test_evidence_gap_followup.py=231`、`tests/test_follow_up_source_triage.py=107`、`tests/test_llm_source_triage.py=168` pure LOC。

关键决定：

- `source_quality.py` 继续保持 deterministic relevance/credibility 职责，未继续扩展该 warning-band 文件；LLM JSON、access gate 和 prompt-injection 防护放入新的 `source_triage*` 模块。
- workflow 默认仍能在 mock/no key 环境下运行；真实 provider triage 只有配置可用时参与，失败不会让检索节点崩溃。
- Todo 8 不做证据抽取或深度报告写作；这些仍留给 Todo 9 和 Todo 11。

后续事项：

- `source_triage.py`、`source_triage_models.py`、`workflow/source_nodes.py`、`workflow/follow_up.py` 都处于 200-250 LOC warning band；后续继续扩展前应优先拆分。
- 一名 OMO 子执行器曾误写 `outputs/evidence/todo8_llm_source_triage_pytest_20260709.txt`，已删除该文件和空目录；`outputs/` 仍不提交。

## 2026-07-10 / Todos 9-11 source-bound LLM evidence, citation filtering, and deep report writing

修改文件：

- `src/medical_research_agent/llm_evidence.py`
- `src/medical_research_agent/llm_evidence_models.py`
- `src/medical_research_agent/llm_evidence_output.py`
- `src/medical_research_agent/workflow/evidence_nodes.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/report_models.py`
- `src/medical_research_agent/report_templates.py`
- `src/medical_research_agent/templates/report_markdown.j2`
- `src/medical_research_agent/llm_report_models.py`
- `src/medical_research_agent/llm_report_grounding.py`
- `src/medical_research_agent/llm_report_writer.py`
- `src/medical_research_agent/workflow/report_writer_nodes.py`
- `src/medical_research_agent/workflow/report_nodes.py`
- `tests/test_llm_evidence_extraction.py`
- `tests/test_workflow_llm_evidence.py`
- `tests/test_report_citation_eligibility.py`
- `tests/test_llm_report_writer.py`

改动摘要：

- 新增 schema-bound LLM evidence extractor，只处理具有 item-level final-citable URL 的公开来源；输出 evidence/spec/claim 均校验 `source_id`、`document_id`、URL、quote/location 和 evidence index。
- workflow 的 evidence 节点保持 deterministic extractor 为永久 fallback；仅在真实 `openai_compatible` provider 配置时叠加 LLM evidence，mock/private-only/malformed/缺 key/请求失败不会清空原证据。
- 私有与内部资料继续 local-only：不会进入外部 LLM prompt，并在 intermediate/errors 中记录 skipped private source IDs。
- final reference rendering 新增 citation projection：只有一致的 `AccessCheck` + `CitationEligibility` 才进入最终参考文献；不可引用来源保留在 JSON 和“来源审计与证据缺口”附录。
- PubMed `abstract_accessible` 引用明确标注“仅摘要证据，非全文”。
- 新增 deep LLM report writer：按 planned semantic sections 生成长文、表格和 source-linked claims；未知/不可引用 source、未知 evidence、link mismatch、缺失章节、malformed JSON 均降级为 deterministic/explicit-gap `needs_review`。
- final references 仍由 deterministic citation projection 生成，LLM 无权新增任意引用；strong claims 仍需经过现有 claim verifier 后才能标记 supported。

测试与检查：

- Todo 9 extractor：`6 passed`；evidence/privacy subset：`18 passed`；workflow integration subset：`22 passed, 1 warning`。
- Todo 10 citation tests：`2 passed, 1 warning`；独立 report regression subset：`12 passed, 1 warning`。
- Todo 11 writer tests：`5 passed, 1 warning`；report/claim/citation/outline regression gate：`24 passed, 1 warning`。
- Full suite：`164 passed, 1 warning in 50.52s`。
- OMO no-excuse 对 Todo 9-11 touched Python surface：`no violations in 16 file(s)`。
- secret-shaped literal scan 无匹配；`.env`、`outputs/`、`data/`、`cache/`、`uploads/` 仍未作为提交内容引入。

关键决定：

- `evidence.py` 和既有 deterministic `report_writer.py` 不扩写；LLM 功能放入独立模块并通过小型 workflow adapter 接入。
- LLM writer 初版达到 292 pure LOC，被 no-excuse 阻止后拆出 `llm_report_grounding.py`；最终 writer 为 191 pure LOC。
- 本轮创建子智能体时按用户要求使用 `gpt-5.6-terra` + `high`。Todo 9 核心与 Todo 10 子智能体成功交付；后续 integration/writer 子智能体空结束，主线程在同一 OMO 测试/证据约束下完成剩余小切片。

后续事项：

- Todo 12 仍需把 report-quality evaluator 接入 workflow completion/status 与 CLI 输出。
- `llm_evidence.py` 当前 236 pure LOC，进入 warning band；后续扩展前应先拆分。

## 2026-07-12 / Todo 13 deep-free-source LLM smoke, docs, and cleanup

修改文件：

- `src/medical_research_agent/connectors/crossref.py`
- `tests/test_connectors_sources.py`
- `README.md`
- `LOG.md`
- `.omo/evidence/task-13-deep-free-source-llm-reporting.md`

改动摘要：

- 完成 redacted LLM doctor 和 mock OpenAI-compatible smoke：本机未发现 `.env`，因此保持 `provider=mock`、`api_key_set=false`；mock smoke 验证了 client payload/retry/privacy/provider-switching 路径。真实 provider 仍仅在用户配置真实 key 后执行，且不记录 key。
- Todo 13 的实际文献/监管/产品 CLI smoke 首次暴露 Crossref 日期解析缺陷：嵌套 `date-parts=[[null]]` 触发 `int(None)` 并中断 workflow。新增参数化回归后，Crossref 逐一尝试 `published-print`、`published-online`、`published`、`issued`，跳过不可解析候选；没有可解析日期时保留 `published_at=None`，且不改变 Crossref metadata-only 最终引用资格。
- 重新运行原始文献/监管/产品 topic 后，workflow 在 180 秒内正常返回 `needs_more_sources`，而不是崩溃；报告/PDF/状态/rejected-source 审计均落盘。公司/国内公开信息 topic 的保留 smoke 同样诚实返回 `needs_more_sources`，未伪造最终引用。
- README 现在明确 mock-vs-real provider 边界、quality status/CLI 诊断、item-level free citation 条件、private-source egress 默认和 runtime output 清理规则。

测试与检查：

- Doctor：`examples\check_llm_config.py` 输出 `provider=mock`、`api_key_set=false`；`--mock-provider-smoke` 输出 `mock_provider_smoke=ok` 和 `retry_attempts=1`，无 secret。
- Red：新的 Crossref 日期参数化测试在修复前 `2 failed, 1 passed`，两项失败均为 `TypeError: int() ... NoneType`。
- Green：同一测试 `3 passed in 0.25s`；受影响 connector tests `16 passed in 2.75s`；full suite `177 passed, 1 warning in 55.99s`，低于 180 秒；OMO no-excuse 对本轮两个 Python 文件 `no violations in 2 file(s)`。
- 实际 workflow smokes：公司/国内公开信息 run 为 `needs_more_sources`、quality `0.2`、`0 accepted / 3 rejected`、regulatory source gap；文献/监管/产品 run 为 `needs_more_sources`、quality `0.2`、`0 accepted / 7 rejected`、stimulation/electrode_contacts/regulatory source gaps。两者均生成 Markdown/PDF，PDF header 为 `%PDF-`，报告引用数为 0，因此没有不合格的最终引用；文献 run 还保留两条 Semantic Scholar 429 retryable 诊断。
- 清理：未请求保留输出，已删除 `outputs/todo13-company-smoke/`、`outputs/todo13-literature-smoke/` 及五份临时 Todo 13 transcript；精确 `Test-Path` 回执均为 `False`。

关键决定：

- 对 live public source 的无来源结果，`needs_more_sources` 加上 facet-scoped gaps、rejected-source audit 和零最终引用是预期的安全行为，不将 report/PDF 文件存在误报为 completed。

## 2026-07-12 / Todo 13 Crossref scalar date-envelope follow-up

修改文件：

- `src/medical_research_agent/connectors/crossref.py`
- `tests/test_connectors_sources.py`
- `LOG.md`
- `.omo/evidence/task-13-deep-free-source-llm-reporting.md`

改动摘要：

- 独立 verifier 发现第二个 Crossref raw-date 边界：`issued='not-a-date-object'` 会在日期 helper 的首个 `.get` 抛出 `AttributeError`。helper 现在仅在候选为 `Mapping` 时读取 `date-parts`；scalar/malformed candidate 归一化为 `None`，既有候选循环会继续尝试低优先级有效日期。
- 新增回归覆盖 scalar `published-print` + 有效 `issued` 回退，以及 scalar-only `issued` 仍生成 metadata-only source 并保持 `published_at=None`。没有扩大 Crossref item schema 校验或 workflow exception handling。

测试与检查：

- Red：Crossref 日期参数化测试在修复前 `2 failed, 3 passed in 0.64s`，两项均为 `AttributeError: 'str' object has no attribute 'get'`。
- Green：同一测试 `5 passed in 0.26s`；受影响 connector suite `18 passed in 4.20s`；full suite `179 passed, 1 warning in 59.18s`，低于 180 秒；OMO no-excuse `no violations in 2 file(s)`。
- 再次运行原始文献/监管/产品 CLI topic 后，workflow 在 180 秒内 exit 0 且不再崩溃；由于 live public-network 返回变化，结果为 `needs_review`、quality `0.4`、`1 accepted / 9 rejected`、1 条 Semantic Scholar 429 retryable error。报告仍为零最终链接，PDF header `%PDF-`，stimulation/regulatory gaps 保留而 electrode_contacts 标记 covered。该网络快照替代此前同题目的 `0 accepted / 7 rejected` 统计，不表示质量完成。
- 未请求保留运行产物；新建的 scalar-boundary smoke directory 和 full/CLI transcript 已在 evidence capture 后删除。
- 本轮没有向外部 LLM 发送私有内容；`.env` 缺失且配置保持 mock。远程公开 source text 未进入真实 provider，prompt-injection egress 通过既有 source-triage policy/test 约束，而非用 smoke 假装验证了真实 provider。

## 2026-07-12 / Todo 15 source-contract, Crossref envelope, strategy LLM, and follow-up route integrity

修改文件：

- `src/medical_research_agent/workflow/source_access_contracts.py`
- `src/medical_research_agent/workflow/source_nodes.py`
- `src/medical_research_agent/workflow/follow_up.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/evidence_gaps.py`
- `src/medical_research_agent/connectors/crossref.py`
- `tests/test_workflow_source_routes.py`
- `tests/test_follow_up_source_triage.py`
- `tests/test_follow_up_preferred_routes.py`
- `tests/test_llm_source_strategy.py`
- `tests/test_crossref_resilience.py`
- `.omo/evidence/task-15-deep-free-source-llm-reporting.md`

改动摘要：

- 初始检索和 bounded follow-up 共享 restrictive access-contract gate；Crossref 等已声明 `metadata_only` 的来源不会再被通用 verifier 提升为最终可引用来源，也不会进入解析。
- Crossref 对非 mapping 根/信封返回 parser-classified connector error，跳过标量 item/author，保留既有标量日期回退行为。
- `plan_research` 现在将配置 LLM client 传入 source strategy；私有本地请求仍在 strategy 层阻断外部 completion。
- follow-up 从已有 search plan 继承 `preferred_connectors` 并复用 route builder；无公开 route 的项目不执行 public connector，保持每项的 bounded limit。

测试与检查：

- 红测分别覆盖合同覆盖、Crossref 根/author、workflow LLM 注入和 preferred follow-up route；修复后 Todo 15 聚焦批次 `37 passed, 1 warning in 11.45s`。
- 完整测试：`189 passed, 1 warning in 76.94s`；OMO no-excuse：`no violations in 11 file(s)`。
- 内存 manual harness 验证配置 LLM 调用一次、metadata-only Crossref 拒绝、畸形 Crossref 安全处理、`pmc`/`accessgudid` 路由且零 DuckDuckGo fallback。

后续事项：

- 本机无 `.env` 和真实 API key，因此 real OpenAI-compatible provider 未执行；公开网络 connector 的接受率仍应视为运行时快照，不能替代确定性合同测试。

## 2026-07-12 / Todo 16 final review boundary hardening

修改文件：

- `src/medical_research_agent/connectors/crossref.py`
- `src/medical_research_agent/llm_report_grounding.py`
- `src/medical_research_agent/report_models.py`
- `src/medical_research_agent/workflow/follow_up.py`
- `src/medical_research_agent/workflow/follow_up_search.py`
- `tests/test_crossref_resilience.py`
- `tests/test_report_boundary_hardening.py`
- `tests/test_follow_up_preferred_routes.py`
- `.omo/evidence/task-16-deep-free-source-llm-reporting.md`

改动摘要：

- Crossref 对 DOI、URL 或 publisher 为非标量的 mapping row 安全跳过，避免 Pydantic `ValidationError` 击穿 workflow。
- LLM 报告 section 现在必须有 evidence link；section claim 的 evidence 必须与 section evidence 相交。非字符串 `llm_triage.decision` 在来源审计中降级为保守的 `rejected_or_pending_source`。
- bounded follow-up 在选择 connector 前跳过私有 source type，并对每个 item 的 connector 返回总量执行 limit 截断。connector 执行切片提取到 `follow_up_search.py`，保留 `follow_up._search_follow_up_sources` 兼容测试 seam。

测试与检查：

- Todo 16 聚焦 adversarial tests：`10 passed, 1 warning in 1.04s`。
- 受影响回归批次：`45 passed, 1 warning in 8.76s`。
- 完整测试：`195 passed, 1 warning in 122.45s`；唯一 warning 是既有的 LangGraph deprecation。
- OMO no-excuse 对五个生产模块和三份回归测试：`no violations in 8 file(s)`。
- 离线 `httpx.MockTransport` manual harness 确认 invalid Crossref mapping 返回零记录、source-only section 有 grounding errors、malformed triage 使用保守 audit reason、private follow-up 零 public connector calls、overproducing connector 截断至 item limit。

清理与边界：

- 本机仍无 `.env` 或 real provider key；所有 Todo 16 QA 为 offline/mock，不接触私有资料或真实 provider。
- 首次 full-suite terminal handle 只显示 partial progress，按 inconclusive 处理并确认没有遗留 Python 进程；新鲜 TTY rerun 获得 exit-0 回执。
- 已在 evidence capture 后删除临时 `.debug-journal.md` 及其唯一 local exclude entry；没有保留 Todo 16 runtime output 或临时 test receipt。

## 2026-07-12 / Todo 17 SSRF and report-boundary security gate

修改文件：

- `src/medical_research_agent/url_security.py`
- `src/medical_research_agent/connectors/url.py`
- `src/medical_research_agent/parsers/web.py`
- `src/medical_research_agent/parsers/pdf.py`
- `src/medical_research_agent/source_access.py`
- `src/medical_research_agent/report_models.py`
- `tests/test_url_security_policy.py`
- `tests/test_report_security_projection.py`
- `tests/test_llm_evidence_extraction.py`
- `tests/test_llm_evidence_private_boundary.py`
- `LOG.md`

改动摘要：

- 新增共享 URL 安全策略：拒绝 `localhost`、loopback、private、link-local、reserved、unspecified 和 multicast 的字面 IP host；只允许 HTTP(S)，并在每个 redirect target 发起请求前重新校验。
- URL metadata connector、HTML/PDF parser 与 source access verifier 全部改为手动逐跳请求。访问校验遇到策略拒绝时保守返回 `needs_review` 和明确原因，不会将该错误伪装为可访问来源。
- 最终引用 projection 现在自行拒绝 `user_uploaded_private`/`internal_private`，并要求 `access_check.url` 与 `SourceRecord.url` 完全一致。因此直接调用 LLM report writer 也不会将这两类来源或其证据送入外部请求。
- PDF parser 将既有 broad `Exception` 收窄为 `pypdf.errors.PdfReadError`，保留损坏 PDF 的 `DocumentParseError` 契约。
- 将 267 行的 `test_llm_evidence_extraction.py` 中私有来源回归拆到独立 `test_llm_evidence_private_boundary.py`；原文件降至 244 行，测试语义不变。

测试与检查：

- Red：安全对抗测试在修复前 `11 failed in 10.56s`，覆盖危险字面 IP、私网 redirect、私有 source 和 access URL mismatch 进入报告 LLM payload。
- Green：同一对抗测试 `11 passed in 11.86s`；受影响 parser/verifier/citation/LLM 回归均通过。
- Full suite：`206 passed, 1 warning in 115.29s`；唯一 warning 是既有 LangGraph deprecation。
- OMO no-excuse：10 个触及 Python 文件 `no violations in 10 file(s)`。
- Manual QA：公共 `URLSourceConnector` API 对 `http://127.0.0.1/admin` 返回 `url: blocked host: loopback`，未发出网络请求。

关键决定：

- 禁止使用 HTTP client 的自动 redirect；安全策略必须在下一跳 request 之前执行，避免 verifier/parser 在获得最终 URL 后才发现私网地址。
- 隐私和 citation URL 一致性在 projection 层再次执行，即使上游 evidence extractor 已有类似检查，也避免直接 report-writer 调用绕过 LLM egress 边界。
## 2026-07-13 / Todo 12 report-quality workflow gate completion

修改文件：

- `src/medical_research_agent/report_quality.py`
- `src/medical_research_agent/workflow/status_policy.py`
- `src/medical_research_agent/workflow/quality_nodes.py`
- `examples/run_source_workflow.py`

改动摘要：

- 将报告质量评估接入 workflow 状态与 CLI 摘要；只有来源相关性、可免费访问引用、证据广度、章节深度、结论支撑和 PDF 产物均满足时才允许 `completed`。
- 缺失或不通过的质量结果保持 `needs_review` / `needs_more_sources`，异常与致命错误继续优先覆盖既有状态。

## 2026-07-13 / Todo 17 global security and code-quality gates

修改文件：

- `src/medical_research_agent/url_security.py`
- `src/medical_research_agent/report_models.py`
- `src/medical_research_agent/llm_report_writer.py`
- `tests/test_url_security_policy.py`
- `tests/test_report_security_projection.py`
- `tests/test_research_quality_regressions.py`

改动摘要：

- 公共 URL 获取在初始请求和每个重定向目标上拒绝回环、私网、链路本地、保留、未指定及组播地址，并对生产传输解析主机名后检查全部地址；离线 `MockTransport` 测试不触发真实 DNS。
- 引用投影与外部报告 LLM 输入双重排除私有来源及 `access_check.url != source.url` 的伪造元数据。
- 将变更过的质量回归测试压缩到 250 纯代码行，并以 adversarial 安全测试和 no-excuse 检查锁定边界。

关键决定：

- DNS 失败按不可安全获取处理；解析结果中只要存在非公网地址即拒绝，避免 DNS rebinding/多地址主机绕过。

## 2026-07-13 / Todo 17 DNS rebinding TOCTOU closure

修改文件：
- `src/medical_research_agent/url_security.py`
- `tests/test_url_security_policy.py`

改动摘要：
- 将 DNS 校验移到 HTTP Core 的实际 TCP 连接边界，并把已校验的公网 IP 直接传给底层连接，消除“策略校验后由传输层再次解析域名”的 DNS rebinding 时间窗口。
- HTTP 请求仍保留原始域名，因此 HTTPS SNI 和证书主机名校验不变；每个重定向目标在连接前重新执行同一策略。
- 明确拒绝环境变量或显式配置产生的 HTTP proxy transport，因为代理端远程 DNS 无法证明最终连接地址；离线 `MockTransport` 行为保持不变。

测试与检查：
- Red：确定性重绑定回归测试显示校验阶段为 `93.184.216.34`、实际连接阶段变为 `169.254.169.254`，结果 `1 failed in 0.95s`。
- Green：URL 安全测试 `13 passed in 8.14s`；受影响 URL/access/parser/connector 测试 `45 passed in 31.14s`。
- OMO no-excuse：`url_security.py` 与 `test_url_security_policy.py` 为 `no violations in 2 file(s)`。

## 2026-07-13 / Todo 17 ProductSpec external-LLM privacy closure

修改文件：
- `src/medical_research_agent/llm_report_writer.py`
- `tests/test_report_security_projection.py`
- `.omo/evidence/task-17-deep-free-source-llm-reporting.md`

改动摘要：
- 外部报告 LLM 的 ProductSpec 投影现在要求 `source_ids` 与 `evidence_ids` 均非空，所有 source/evidence 均通过公开可引用过滤，并且每条 evidence 的真实来源必须属于该 spec 声明的 source。
- 新增 secret-marker 对抗回归，覆盖空 source、空 evidence、跨来源 evidence、私有 source 和私有 evidence；合法公开 spec 保留为正向控制。

测试与检查：
- Red：聚焦回归修复前 `1 failed in 0.72s`，捕获的外部请求包含未充分 grounding 的 secret-marked ProductSpec。
- Green：聚焦 `1 passed in 0.47s`；报告 writer/grounding/security/workflow 受影响批次 `16 passed, 1 warning in 2.07s`。
- Full suite：`211 passed, 1 warning in 110.55s`，退出码 0；唯一 warning 为既有 LangGraph deprecation。
- OMO no-excuse：两个触及 Python 文件 `no violations in 2 file(s)`。

隐私边界：
- 未调用真实外部 provider，未读取私有文档；测试中的 secret marker 均为合成字符串。

## 2026-07-13 / Outbound URL safety documentation closure

修改文件：
- `README.md`
- `LOG.md`

改动摘要：
- 明确用户提供的公网 URL 及每个重定向目标都会拒绝非公网地址，实际连接固定到已验证公网 IP；显式或环境 HTTP 代理按 fail-closed 处理。
- 连接固定由公开 `httpx.BaseTransport` 扩展点与标准库 socket/TLS 实现，不依赖 `httpx` / `httpcore` 私有接口。

## 2026-07-13 / F2 MVP flow test-size closure

修改文件：
- `tests/mvp_flow_fixtures.py`
- `tests/test_mvp_flow_expectations.py`
- `tests/test_mvp_flow_outputs.py`
- `.omo/evidence/f2-mvp-test-size-fix-deep-free-source-llm-reporting.md`

改动摘要：
- 将确定性 MVP workflow fixture、证据断言和报告/产物断言按职责拆分，保留原有 3 条测试行为与覆盖。
- 移除 `test_mvp_flow_expectations.py` 的 `SIZE_OK` 抑制；拆分后三个文件分别为 176、26、63 纯代码行。

测试与检查：
- 拆分前基线和拆分后聚焦测试均为 `3 passed, 1 warning`，退出码 0。
- OMO no-excuse 对三个 Python 文件报告 `no violations in 3 file(s)`；Python 编译检查退出码 0。

## 2026-07-13 / Todo 17 workflow integrity and quality-boundary closure

修改文件：

- `src/medical_research_agent/workflow/follow_up.py`
- `src/medical_research_agent/source_strategy.py`
- `src/medical_research_agent/workflow/nodes.py`
- `src/medical_research_agent/report_models.py`
- `src/medical_research_agent/workflow/quality_nodes.py`
- `tests/test_follow_up_state_integrity.py`
- `tests/test_llm_source_strategy.py`
- `tests/test_workflow_quality_security.py`

改动摘要：

- 有界跟进只对新增来源和文档做确定性抽取，再与已有证据和产品参数合并去重；无跟进与成功跟进都不会再覆盖前序 LLM 结果。
- 成功接受跟进来源时刷新 `source_quality_status`，避免初始 `needs_more_sources` 状态残留。
- 来源策略对缺少 API key、不支持的 provider 和请求重试耗尽做确定性目录回退，并记录不含响应内容或密钥的分类诊断；provider 失败不再误记为 LLM JSON 无效。
- 报告质量节点复用最终引用投影的私有来源、source ID、source/access URL 和 citation eligibility 边界，排除不可最终引用的来源对完成门禁计数的影响。

测试与检查：

- Red：首轮聚焦 `6 failed, 8 passed`，另有成功跟进状态探针 `1 failed`；精确诊断探针 `3 failed`。
- Green：聚焦 `15 passed, 1 warning`；受影响批次 `44 passed, 1 warning`。
- OMO no-excuse：8 个本轮 Python 文件 `no violations in 8 file(s)`；`git diff --check` 退出码 0。
- 并发 connector resource/URL transport 修改完成并合并后，最终全量为 `275 passed, 1 warning in 73.70s`、退出码 0；该结果取代编辑重叠期间的临时失败回执。

关键决定：

- 跟进节点采用“已有 LLM/确定性结果 + 新跟进确定性结果”的增量合并语义，而不是重新处理全部文档并替换状态。
- provider 错误诊断仅记录错误类型、环境变量名、provider 名或重试次数，不记录响应正文和密钥。

## 2026-07-13 / Public connector inventory documentation closure

修改文件：
- `README.md`
- `LOG.md`

改动摘要：
- README 补齐 PMC、Europe PMC、OpenAlex、AccessGUDID 与 PatentsView，并明确开放全文、检索/摘要和 metadata-only 的能力边界；Crossref 继续仅作元数据发现。

## 2026-07-13 / Todo 17 stable public transport and non-global IP closure

修改文件：

- `src/medical_research_agent/url_security.py`
- `src/medical_research_agent/public_http_transport.py`
- `src/medical_research_agent/connectors/url.py`
- `src/medical_research_agent/parsers/web.py`
- `src/medical_research_agent/parsers/pdf.py`
- `src/medical_research_agent/source_access.py`
- `tests/test_url_security_policy.py`
- `tests/test_public_url_transport.py`
- `.omo/evidence/task-17-deep-free-source-llm-reporting.md`

改动摘要：

- 公网 URL 策略改为要求 IP 全局可路由，并额外拒绝 IPv6 deprecated site-local 地址，补齐 CGNAT `100.64.0.0/10` 等 selected-flag denylist 漏洞。
- 用自有 `PublicURLFetcher`、公开 `httpx.BaseTransport` 扩展点及标准库 socket/TLS 替换对 HTTPX/HTTPCore 私有连接池字段的修改，不再关闭或改写调用方共享连接池。
- TCP 直接连接一次解析并校验后的 IP；Host、TLS SNI 和证书主机名仍使用原始域名。每跳重定向重新执行策略，代理路径 fail-closed，仅允许显式 `MockTransport` 作为离线测试 seam。
- parser、URL connector 与 access verifier 现在确定性拥有并关闭安全 fetcher；无共享池的每请求连接模型避免并发请求相互修改 transport 状态。

测试与检查：

- Red：CGNAT 用例 `1 failed, 2 passed`；稳定 transport API 红测在旧实现上导入失败。
- Green：核心 URL/parser/access 聚焦 `38 passed`；typed-origin 重构后受影响批次 `83 passed, 1 warning in 22.87s`。
- Full suite：`275 passed, 1 warning in 73.82s`，退出码 0。
- `compileall`、`git diff --check` 通过；OMO no-excuse 为 `no violations in 8 file(s)`；URL 安全实现中不再存在 `httpcore` 导入或私有 transport/pool/network-backend 访问。

## 2026-07-13 / Todo 17 connector resilience and HTTP ownership closure

修改文件：

- `src/medical_research_agent/connectors/base.py`
- `src/medical_research_agent/connectors/accessgudid.py`
- `src/medical_research_agent/connectors/europe_pmc.py`
- `src/medical_research_agent/connectors/openalex.py`
- `src/medical_research_agent/connectors/patentsview.py`
- `src/medical_research_agent/connectors/pmc.py`
- `src/medical_research_agent/connectors/pubmed.py`
- `src/medical_research_agent/http_client.py`
- `src/medical_research_agent/resource_context.py`
- `src/medical_research_agent/workflow/source_nodes.py`
- `src/medical_research_agent/workflow/source_parsing.py`
- `src/medical_research_agent/workflow/follow_up.py`
- `src/medical_research_agent/workflow/follow_up_search.py`
- `tests/test_connector_json_resilience.py`
- `tests/test_http_client_ownership.py`

改动摘要：

- 六个 F2 点名连接器统一在 JSON 根边界要求 object；畸形嵌套 object/list 和标量 item 被安全归一化或跳过，非 object 根转为带分类的 `ConnectorError`，不再让 `AttributeError` 中断 workflow。
- NCBI 摘要字段、Europe PMC/OpenAlex 年份等可选元数据增加类型与范围归一化，保留可审计的 fallback 来源记录。
- 所有 `SourceConnector` 明确记录 HTTP client 所有权：自建 client 在上下文退出时关闭，注入 client 保持由调用方管理。
- 主搜索、follow-up 和批量解析使用 `managed_resource` 建立确定性关闭边界；不实现上下文协议的测试替身或扩展 adapter 继续通过 `nullcontext` 工作。

测试与检查：

- 首轮 Red：`44 failed`；嵌套字段第二轮 Red：`3 failed, 26 passed`。
- 聚焦 Green：`51 passed`；连接器与 workflow 受影响批次：`95 passed, 1 warning`。
- OMO no-excuse：`no violations in 20 file(s)`；`compileall` 与 `git diff --check` 退出码 0。
- 项目虚拟环境未安装 `ruff`，因此未声明 ruff 结果；所有新增/触及职责文件均低于 250 纯代码行。

## 2026-07-13 / Todo 17 NCBI optional-date range closure

修改文件：

- `src/medical_research_agent/connectors/pubmed.py`
- `src/medical_research_agent/connectors/pmc.py`
- `tests/test_connector_json_resilience.py`
- `.omo/evidence/task-17-deep-free-source-llm-reporting.md`

改动摘要：

- 独立复核发现 PubMed/PMC 对合法 JSON 中越界的可选日期仍可能抛出 `ValueError` 并丢弃整个来源；两个日期解析器现在将 `datetime` 范围错误保守归一化为 `None`，同时保留其余可审计来源元数据。

测试与检查：

- Red：PubMed 越界年份回归为 `1 failed`，错误为 `year 999999 is out of range`。
- Green：连接器 JSON 韧性测试 `30 passed`；三个触及 Python 文件的 OMO no-excuse 为 `no violations in 3 file(s)`，`compileall` 退出码 0。
- 独立受影响批次：连接器、client ownership、access verifier、parser、follow-up 与真实来源 workflow 共 `107 passed, 1 warning`；20 个相关文件的 OMO no-excuse 为 `no violations in 20 file(s)`，`git diff --check` 退出码 0。

## 2026-07-13 / Todo 17 公网响应体资源上限闭环

修改文件：

- `src/medical_research_agent/public_http_transport.py`
- `src/medical_research_agent/url_security.py`
- `tests/test_public_url_transport.py`
- `tests/test_free_access_verifier.py`
- `tests/test_parsers_documents.py`
- `.omo/evidence/task-17-deep-free-source-llm-reporting.md`

改动摘要：

- 公网抓取新增 typed 10 MiB 默认响应上限：GET 在有效 `Content-Length` 已超限时读前拒绝，无长度/分块响应按 HTTPX 解码后字节流累计计数，压缩响应的解码膨胀也受同一上限约束；HEAD 保留仅取元数据的语义和源站 `Content-Length`。
- 固定公网 IP 的 transport 改为把 HTTP response/socket 所有权交给 `SyncByteStream`，正常完成、声明长度拒绝和流式中途超限都会确定性关闭连接。
- 超限统一抛出 `PublicURLPolicyError`；access verifier 降级为不可引用的 `NEEDS_REVIEW`，网页/PDF parser 转为 `DocumentParseError`，不暴露部分内容也不伪装成功。

测试与检查：

- Red：三类攻击用例 `3 failed, 5 passed`；HEAD 元数据控制随后捕获源站长度被改写为 `0` 的兼容性回归。Green：transport/verifier/parser 专项 `30 passed`。
- 受影响批次：`92 passed, 1 warning`；全量：`283 passed, 1 warning in 68.55s`，退出码 0。
- OMO no-excuse：`no violations in 5 file(s)`；`compileall`、`git diff --check` 退出码 0。
- 生产 transport 真实公网 smoke：`https://example.com/` HEAD/GET 均返回 200，HEAD body 为 0 bytes，GET 为 559 HTML bytes，response 与 client 均确认关闭。

## 2026-07-13 / Todo 17 固定公网传输流式读取异常闭环

修改文件：

- `src/medical_research_agent/public_http_transport.py`
- `tests/pinned_transport_stream_fixtures.py`
- `tests/test_public_url_transport.py`
- `tests/test_parsers_documents.py`
- `tests/test_free_access_verifier.py`
- `.omo/evidence/task-17-deep-free-source-llm-reporting.md`

改动摘要：

- 固定公网 transport 在响应交给 HTTPX 后，流式 `HTTPResponse.read()` 产生的 stdlib 协议异常和 socket 读取异常分别转换为绑定原始 request 的 `httpx.RemoteProtocolError` 与 `httpx.ReadError`。
- 流式失败先关闭 response 和 connection；response 关闭路径使用 `finally`，保证仍会尝试关闭底层连接。
- 网页 parser 将该错误稳定映射为 `DocumentParseError`，access verifier 降级为不可引用的 `NEEDS_REVIEW`，不再由原始 stdlib 异常中断 workflow。

测试与检查：

- Red：生产 transport、parser 和 verifier 四个回归用例为 `4 failed in 1.29s`，捕获原始 `IncompleteRead` 与 `OSError` 穿透。
- Green：聚焦 `4 passed in 0.54s`；受影响批次 `50 passed, 1 warning in 1.69s`；全量 `287 passed, 1 warning in 68.10s`，退出码 0。
- OMO no-excuse：`no violations in 5 file(s)`；`compileall` 和 `git diff --check` 退出码 0。
- 生产公网 smoke：`https://example.com/` GET 为 200、559 bytes，response 与 owned client 均确认关闭。

## 2026-07-13 / Todo 17 声明长度静默截断闭环

修改文件：

- `src/medical_research_agent/public_http_transport.py`
- `tests/pinned_transport_stream_fixtures.py`
- `tests/test_public_url_transport.py`
- `tests/test_parsers_documents.py`
- `tests/test_free_access_verifier.py`
- `.omo/evidence/task-17-deep-free-source-llm-reporting.md`

改动摘要：

- 安全复核用真实 `http.client.HTTPResponse` 复现：响应声明 `Content-Length: 100`、只发送 19 bytes 时，分段 `read(amt)` 会在第二次读取直接返回空字节，不保证抛出 `IncompleteRead`。
- 固定公网 stream 现在保存非 chunked 响应的原始预期长度并累计实际 raw bytes；声明长度未满足却遇到空读时，关闭 response/connection 并抛出绑定原始 request、包含已收/应收字节数的 `httpx.RemoteProtocolError`。
- chunked 与无声明长度的 EOF-delimited 响应维持原有语义；parser 和 verifier 分别降级为 `DocumentParseError` 与不可引用的 `NEEDS_REVIEW`，残缺正文不会成为成功解析或可引用来源。

测试与检查：

- Red：transport/parser 未抛错，verifier 误记为 `PARSER_FAILED`，共 `3 failed in 0.82s`。
- Green：静默 EOF 聚焦 `3 passed in 0.44s`；全部 stream 错误回归 `7 passed in 0.44s`；受影响批次 `53 passed, 1 warning in 1.73s`。
- 全量：`290 passed, 1 warning in 71.08s`，退出码 0；OMO no-excuse `no violations in 5 file(s)`，`compileall` 与 `git diff --check` 退出码 0。
- 真实公网正常路径：example.com GET 为 200、559 bytes，response 与 owned client 均确认关闭。
