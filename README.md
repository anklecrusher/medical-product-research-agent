# Medical Research Agent

面向医疗产品经理的本地优先调研系统骨架。

当前仓库先提供项目基础结构、配置入口和核心 Pydantic schema。后续 workflow、connector、报告生成、PDF 渲染和前端应基于这些 schema 继续扩展。

## Local Runtime Directories

以下目录用于本地运行时数据，默认不提交到 git：

- `data/`: 本地数据库和持久化中间数据
- `outputs/`: 每次调研任务的报告、证据和日志产物
- `cache/`: 下载、解析和检索缓存
- `uploads/`: 用户上传的私有资料

可通过 `.env` 中的 `MEDICAL_RESEARCH_*_DIR` 环境变量调整这些目录。

## Development

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
```

If you just want to use the environment without activation, run `.venv\Scripts\python.exe` directly.

## Codex

Codex worktrees should use the setup helper in `.codex/setup.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File .codex/setup.ps1
```

Common project actions are available through `.codex/actions.ps1`:

```powershell
powershell -ExecutionPolicy Bypass -File .codex/actions.ps1 test
powershell -ExecutionPolicy Bypass -File .codex/actions.ps1 doctor
```

The setup helper installs Python dependencies and creates local runtime directories. It also runs `npm install` automatically once a future frontend adds `package.json`.

## Report Templates

The first flexible report template lives in `templates/reports/medical_product_research_template.md`.
The renderable Jinja2 Markdown template lives in `src/medical_research_agent/templates/report_markdown.j2`.

The template uses a small fixed report skeleton plus optional blocks and figure assets. Source figures must include title, caption, source link, and location or usage notes when available.

## Mock Workflow

The first LangGraph workflow skeleton is intentionally mock-only. It does not call external search, parsing, LLM, PDF, or frontend services.

Run a one-sentence request through the workflow:

```powershell
.\.venv\Scripts\python.exe examples\run_mock_workflow.py "调研 SCS 刺激参数的产品范围、论文证据和监管资料"
```

The run writes mock intermediate artifacts under `outputs/{task_id}/` by default:

- `sources.json`
- `documents.json`
- `evidence.json`
- `claims.json`
- `report.md`
- `workflow_state.json`
- `run.log`

## Source Connectors And Parsers

The first real source layer provides normalized `SourceRecord` output for:

- PubMed / NCBI E-utilities
- Crossref
- Semantic Scholar, with optional `MEDICAL_RESEARCH_SEMANTIC_SCHOLAR_API_KEY`
- Vendor/public document web search via DuckDuckGo HTML results
- FDA 510(k) metadata via openFDA
- ClinicalTrials.gov study registry metadata
- User supplied public URLs

The parser layer provides normalized `ParsedDocument` output for public HTML pages and PDF URLs/files. Network failures are wrapped in `ConnectorError` or `DocumentParseError` so callers can show clear source-specific errors without crashing silently.

Run a lightweight search and optional URL parse:

```powershell
.\.venv\Scripts\python.exe examples\search_sources.py "deep brain stimulation electrode impedance" --limit 2 --url "https://example.com" --output-dir outputs\source_demo
```

When `--output-dir` is set, the example writes:

- `sources.json`
- `documents.json`

The LangGraph workflow can also run the real source retrieval and parsing nodes while keeping later evidence/report nodes as mock placeholders:

```powershell
.\.venv\Scripts\python.exe examples\run_source_workflow.py "调研 DBS 电极阻抗的论文证据" --output-dir outputs\source_workflow_demo
```

## Local Private File Ingestion

Local uploads are treated as private by default. The local ingestor converts PDF, Markdown, TXT, and DOCX files into `user_uploaded_private` `SourceRecord` objects and `ParsedDocument` text without calling external APIs.

```powershell
.\.venv\Scripts\python.exe examples\ingest_local_files.py uploads\sample.pdf uploads\notes.md --output-dir outputs\local_ingest_demo
```

The example writes:

- `sources.json`
- `documents.json`

Legacy binary `.doc` files are intentionally not parsed yet; use `.docx` for the current minimum version.

## LLM Configuration

The LLM layer is replaceable and defaults to a local mock client. Tests and mock workflow runs do not require an API key or network access.

To use an OpenAI-compatible third-party API, copy `.env.example` to `.env` and fill:

```powershell
MEDICAL_RESEARCH_LLM_PROVIDER=openai_compatible
MEDICAL_RESEARCH_LLM_BASE_URL=https://api.example.com/v1
MEDICAL_RESEARCH_LLM_MODEL=your-model-name
MEDICAL_RESEARCH_LLM_API_KEY=your-api-key
```

Privacy gates are explicit:

```powershell
MEDICAL_RESEARCH_ALLOW_EXTERNAL_LLM_FOR_PUBLIC_SOURCES=true
MEDICAL_RESEARCH_ALLOW_EXTERNAL_LLM_FOR_PRIVATE_SOURCES=false
```

Keep private-source external calls disabled unless the user has explicitly approved that behavior.
