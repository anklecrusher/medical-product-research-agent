# HANDOFF.md

## 1. 文件定位

本文件用于把当前电脑上的开发进度迁移到另一台电脑继续开发。

新电脑上的 Codex / 开发线程开始前，应按顺序阅读：

1. `AGENTS.md`
2. `HANDOFF.md`
3. `LOG.md`
4. `医疗产品调研Agent开发周期计划表.md`
5. 当前任务涉及的代码和测试文件

`AGENTS.md` 是全局总领文件，`LOG.md` 是历史工作记录，`HANDOFF.md` 是本次迁移交接摘要。

## 2. 远端仓库

GitHub 仓库：

```text
https://github.com/anklecrusher/medical-product-research-agent
```

迁移前，本机需要先把当前未提交进度提交并推送到该仓库。新电脑只应在确认远端包含最新提交后再 clone。

## 3. 当前本机状态摘要

截至 2026-07-06，本机 `main` 分支相对远端有大量未提交开发成果。

当前本机新增/修改的主要内容包括：

- Python 项目骨架：`pyproject.toml`、`src/medical_research_agent/`
- 配置与环境示例：`.env.example`、`.codex/`
- 文档：`README.md`、`LOG.md`
- 示例脚本：`examples/`
- 开发脚本：`scripts/`
- 报告模板：`templates/`
- 测试：`tests/`

不要只在新电脑 clone 当前远端旧版本后继续开发；必须先在本机提交并推送最新进度。

## 4. 已完成能力

当前项目已经不只是计划文档，已经具备一批最小实现。

### 项目骨架与 Schema

已完成：

- Python `src` 包结构。
- `pyproject.toml`。
- `.env.example`。
- 基础配置模块。
- 核心 Pydantic schema。
- 本地目录约定：`data/`、`outputs/`、`cache/`、`uploads/`。
- Codex 本地环境脚本：`.codex/setup.ps1`、`.codex/actions.ps1`。

核心结构已覆盖：

- `ResearchTask`
- `SourceRecord`
- `ParsedDocument`
- `EvidenceItem`
- `ProductSpec`
- `Claim`
- `ReportSection`
- `ReportArtifact`
- 图文增强相关 schema，如 `FigureAsset`、`ReportTemplate`、`ReportTemplateBlock`

### Workflow 与 LLM 封装

已完成：

- LangGraph mock workflow 骨架。
- workflow 状态结构、节点日志和中间状态落盘。
- mock 流程可生成：
  - `sources.json`
  - `documents.json`
  - `evidence.json`
  - `claims.json`
  - `report.md`
  - `workflow_state.json`
  - `run.log`
- 可替换 LLM 调用层。
- 默认 `MockLLMClient`。
- OpenAI-compatible HTTP client 预留。
- LLM 请求/响应模型。
- 公开/私有来源外发隐私门禁。

### Connector 与 Parser

已完成最小版本：

- PubMed / NCBI E-utilities connector。
- Crossref connector。
- Semantic Scholar connector。
- 普通 URL source 归一化。
- DuckDuckGo HTML 厂商公开资料搜索 connector。
- openFDA device 510(k) connector。
- ClinicalTrials.gov v2 studies connector。
- 网页正文解析。
- PDF 文本解析。
- 本地私有资料 ingestion：
  - PDF
  - Markdown
  - TXT
  - DOCX

本地私有资料统一标记为：

```text
source_type = user_uploaded_private
privacy = local_only
```

### 报告模板

已完成：

- 图文增强弹性报告模板。
- Markdown/Jinja2 模板。
- 来源原图资产位设计。
- 图题、图注、来源链接、使用说明字段。
- 缺图时不崩溃，显示占位提示。

### 示例与测试

当前已有示例：

- `examples/run_mock_workflow.py`
- `examples/run_source_workflow.py`
- `examples/search_sources.py`
- `examples/ingest_local_files.py`

当前已有测试覆盖：

- schema 导入
- mock workflow
- LLM client
- connectors
- parsers
- workflow sources
- report templates
- local file ingestion

最近日志中记录过完整测试结果：

```text
31 passed, 1 warning
```

warning 来自 `langgraph` pending deprecation，不是当前业务失败。

## 5. 尚未完成事项

下一阶段重点不是继续搭骨架，而是把 mock 链路逐步替换为真实能力。

尚未完成：

- 真实证据抽取：从 `ParsedDocument` 抽取 `EvidenceItem` / `ProductSpec` / `Claim`。
- 产品参数抽取：频率、脉宽、电流、电压、通道数、触点、适应证、闭环能力等。
- 证据去重与冲突检查。
- 真实报告大纲生成。
- 真实章节写作。
- claim verifier 与引用核查。
- PDF 渲染输出。
- CLI 完整入口。
- FastAPI 后端。
- React/Vite 前端工作台。

技术债和限制：

- DuckDuckGo HTML 搜索只是厂商公开资料检索的无 key MVP，后续应考虑更稳定搜索 API 或指定站点 connector。
- openFDA 查询语法还需要真实医疗器械样例继续调优。
- PDF parser 当前主要是文本层抽取，不支持 OCR、表格结构化、页码级图资产裁取。
- DOCX ingestion 当前主要抽正文段落，表格结构、页眉页脚、批注等还未完整保留。
- 本地私有资料 ingestion 尚未正式接入 workflow 任务输入，目前主要通过 `examples/ingest_local_files.py` 单独运行。

## 6. 三个线程的迁移日志

以下线程已经按要求把交接记录写入 `LOG.md`：

- `019eca3e-d051-77a1-9748-387cd57aaafd`：项目骨架与核心 schema。
- `019eee47-687a-7033-8dbd-c06bdd41ef61`：Workflow 编排与 LLM 外部封装。
- `019eee50-6765-7e52-a974-f5d9ec7d0a70`：检索 connector 与文档解析。

新电脑接手时，应重点阅读 `LOG.md` 中这些标题：

```text
## 2026-07-06 / 线程 019eca3e 迁移交接
## 2026-07-06 / 线程 019eee47 迁移交接
## 2026-07-06 / 线程 019eee50 迁移交接
```

## 7. 迁移前本机必须执行

在旧电脑上，确认 `.env`、本地数据和运行产物不会被提交。

不要提交：

- `.env`
- `.venv/`
- `.vscode/`
- `data/`
- `outputs/`
- `cache/`
- `uploads/`
- 用户上传的私有资料

提交前检查：

```powershell
$git = "D:\Users\gongjx\AppData\Local\Programs\Git\mingw64\bin\git.exe"
& $git status --short
```

建议提交命令：

```powershell
$git = "D:\Users\gongjx\AppData\Local\Programs\Git\mingw64\bin\git.exe"

& $git add .gitignore AGENTS.md HANDOFF.md LOG.md README.md pyproject.toml .env.example .codex examples scripts src templates tests
& $git commit -m "Sync development progress for migration"
& $git push
```

如果 `git status --short` 还显示其他应提交代码文件，先确认不是私有数据或运行产物，再决定是否加入。

## 8. 新电脑接手步骤

### 8.1 克隆仓库

```powershell
git clone https://github.com/anklecrusher/medical-product-research-agent.git
cd medical-product-research-agent
```

如果新电脑上的 Git 路径不是普通 `git`，先确认可执行路径，再在本机更新协作说明。

### 8.2 创建环境

推荐使用仓库内 Codex setup：

```powershell
powershell -ExecutionPolicy Bypass -File .codex/setup.ps1
```

或者手动：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
New-Item -ItemType Directory -Force -Path data, outputs, cache, uploads
```

### 8.3 配置环境变量

复制 `.env.example` 为 `.env`：

```powershell
Copy-Item .env.example .env
```

默认建议仍使用 mock：

```text
MEDICAL_RESEARCH_LLM_PROVIDER=mock
```

如果需要真实 LLM，再填写 OpenAI-compatible 配置。不要把 `.env` 提交到 git。

### 8.4 验证环境

```powershell
powershell -ExecutionPolicy Bypass -File .codex/actions.ps1 doctor
powershell -ExecutionPolicy Bypass -File .codex/actions.ps1 test
```

或直接：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 9. 新电脑推荐下一步

建议优先开一个新线程，任务是：

```text
阅读 AGENTS.md、HANDOFF.md、LOG.md 和现有代码，确认项目在新电脑能通过测试；
不要开发新功能，先完成迁移环境验收。
```

验收通过后，再开下一个功能线程：

```text
实现真实 evidence extraction 最小版本：
从 ParsedDocument 中抽取 EvidenceItem / ProductSpec / Claim，
保持 mock 路径可用，
新增测试，
更新 LOG.md。
```

不要一上来做前端或 PDF；当前最关键的缺口是真实证据抽取和引用/claim 质量闭环。

## 10. 私有资料与运行产物

本机曾解析过用户上传样例，运行产物位于：

- `outputs/local_ingest_rtscale/`
- `outputs/local_ingest_dsy202509/`

这些属于运行产物，不应提交到 GitHub。若需要在新电脑保留这些样例结果，应单独压缩拷贝，而不是加入仓库。

## 11. 重要注意事项

- 新电脑上的 Codex 不会自动继承旧电脑的对话线程历史。
- 项目上下文以 `AGENTS.md`、`HANDOFF.md`、`LOG.md` 为准。
- 所有新线程完成工作后必须追加 `LOG.md`。
- 涉及隐私资料时，默认本地处理，不外发 LLM。
- 真实网络 connector 不应成为基础测试的硬依赖；基础测试应继续保持 mock/offline 可跑。
- 不要修改两份既有调研草稿，除非用户明确要求。

