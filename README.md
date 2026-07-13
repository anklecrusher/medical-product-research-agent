# Medical Research Agent

面向医疗产品经理的本地优先调研系统骨架。

当前仓库已提供项目基础结构、配置入口、核心 Pydantic schema、LangGraph workflow 骨架、公开来源 connector/parser、结构化证据抽取、claim 核查、Markdown/PDF 报告渲染和 CLI 示例。后续前端工作台和更完整的内容审计会基于这些已落地的流程继续扩展。

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

- PubMed / NCBI E-utilities for literature discovery and abstract-level access, not full text
- PubMed Central (`PMCFullTextConnector`) for item-level open full text
- Europe PMC for open full-text items when available; records without a usable free item URL remain metadata-only
- OpenAlex for literature discovery and item-level open-access URLs when available; otherwise metadata-only
- Crossref for DOI discovery and metadata only
- Semantic Scholar discovery, with optional `MEDICAL_RESEARCH_SEMANTIC_SCHOLAR_API_KEY`
- Vendor/public document web search via DuckDuckGo HTML results
- FDA 510(k) metadata via openFDA
- FDA/NLM AccessGUDID public device-identifier metadata
- ClinicalTrials.gov study registry metadata
- PatentsView public patent metadata
- User supplied public URLs

The parser layer provides normalized `ParsedDocument` output for public HTML pages and PDF URLs/files. Network failures are wrapped in `ConnectorError` or `DocumentParseError` so callers can show clear source-specific errors without crashing silently.

User-supplied public URLs are subject to an outbound safety policy. The initial host and every redirect target must resolve exclusively to public IP addresses; loopback, private, link-local, reserved, unspecified, and multicast addresses are rejected. Production requests pin a validated public IP at the actual connection boundary to close DNS-rebinding gaps. Explicit or environment-configured HTTP proxies are unsupported for these fetches and fail closed because the application cannot verify a proxy's remote DNS result.

Run a lightweight search and optional URL parse:

```powershell
.\.venv\Scripts\python.exe examples\search_sources.py "deep brain stimulation electrode impedance" --limit 2 --url "https://example.com" --output-dir outputs\source_demo
```

When `--output-dir` is set, the example writes:

- `sources.json`
- `documents.json`

The LangGraph workflow can also run the CLI-first source workflow: real source retrieval/parsing feeds deterministic evidence extraction, claim checks, Markdown report generation, and PDF rendering.

```powershell
.\.venv\Scripts\python.exe examples\run_source_workflow.py "调研 DBS 电极阻抗的论文证据" --output-dir outputs\source_workflow_demo
```

The command prints task counts, status, report-quality pass/score/reasons, and direct artifact paths. The run writes:

- `sources.json`
- `documents.json`
- `rejected_sources.json`
- `evidence.json`
- `claims.json`
- `report.md`
- `report.pdf`
- `workflow_state.json`
- `run.log`

### Mature Research Workflow Semantics

The source workflow now adds a research-quality control layer before report rendering:

- Query planning extracts research facets from the user request, keeps the original Chinese query, and expands medical-product terms into bounded Chinese/English search variants for literature, vendor/manual, UI/programming, regulatory, and local/private-document routes.
- Source routing chooses connectors by facet instead of relying on one generic search path. For UI, programmer, manual, and engineering-logic topics, public web/vendor-manual style searches are prioritized before literature-only fallback.
- The relevance gate scores candidate sources before parsing. Accepted sources are written to `sources.json`; rejected or pending-review records are written to `rejected_sources.json` with audit reasons instead of being silently discarded.
- The evidence gap loop detects missing required facets after the first pass and can run bounded follow-up searches tied to specific gaps. It does not run an unbounded crawler.
- Completion status separates pipeline execution from research success. Artifact generation can finish while the task status is `needs_more_sources` or `needs_review` when source coverage, supported claims, or connector results are insufficient. `completed` is reserved for runs that satisfy the configured research-quality thresholds.

Known current limitations:

- Live public search quality depends on external services and rate limits; recoverable 403/429 connector errors are logged in `workflow_state.json` and `run.log`.
- Deterministic extraction is intentionally conservative and may mark claims as `needs_review` when accepted sources do not directly support product/UI conclusions.
- Regulatory and vendor/manual coverage is useful for diagnostics but still needs broader source-specific connectors before it should be treated as exhaustive.

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

Check the active configuration without printing secrets:

```powershell
.\.venv\Scripts\python.exe examples\check_llm_config.py
```

Run the no-key CI smoke for the OpenAI-compatible client path:

```powershell
.\.venv\Scripts\python.exe examples\check_llm_config.py --mock-provider-smoke
```

The doctor reports provider, model, base URL, and whether a key is present as `api_key_set=true/false`. It never prints the key value. In `openai_compatible` mode, a missing key exits nonzero with the setup hint for `MEDICAL_RESEARCH_LLM_API_KEY`. The mock-provider smoke uses an in-memory fake `/chat/completions` provider, so it validates the payload, retry/error path, privacy gate, and provider switching without requiring a real key.

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

### Provider, Citation, And Runtime Boundaries

- The mock-provider smoke proves the local OpenAI-compatible client path only. It does not call or validate a real provider. A real-provider smoke remains conditional on an explicitly configured `.env` key, and diagnostics must continue to redact it.
- `completed` requires a passing report-quality snapshot. `needs_more_sources` and `needs_review` can still generate a Markdown report and PDF, but their quality reasons, `workflow_state.json`, and `rejected_sources.json` must be reviewed before treating the result as research-ready.
- Final report references require an item-level `CitationEligibility` record with a free-accessible URL. Crossref/DOI metadata-only records remain in the source audit and cannot become final citations without a separately verified accessible item.
- `outputs/` is local runtime state. Use a dedicated `--output-dir` for inspection, then remove it unless the user explicitly requests the artifacts be retained. Do not commit `.env`, runtime outputs, caches, uploads, or private documents.
