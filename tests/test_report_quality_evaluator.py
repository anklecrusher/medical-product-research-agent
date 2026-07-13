from __future__ import annotations

from pathlib import Path

from medical_research_agent.report_quality import ReportQualityArtifacts, evaluate_report_quality
from medical_research_agent.schemas import Claim, ClaimStatus, SourceType
from medical_research_agent.source_contracts import AccessCheck, FreeAccessStatus


def _pdf(tmp_path: Path) -> Path:
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF-1.4\nfixture readable pdf\n%%EOF\n")
    return path


def _access(source_id: str, source_type: SourceType, url: str) -> AccessCheck:
    return AccessCheck(
        source_id=source_id,
        url=url,
        status=FreeAccessStatus.PDF_ACCESSIBLE,
        evidence_note=source_type.value,
    )


def _claim(claim_id: str, source_ids: list[str]) -> Claim:
    return Claim(
        claim_id=claim_id,
        text="该结论有当前来源和证据链支撑。",
        source_ids=source_ids,
        evidence_ids=[f"ev_{claim_id}"],
        status=ClaimStatus.SUPPORTED,
    )


def test_evaluator_fails_weak_template_only_report_with_actionable_reasons(tmp_path: Path) -> None:
    # Given: a short template-style report with one source and no readable PDF.
    report = """
# 调研报告

## 1. 核心结论
- 暂无足够证据形成核心结论，标记为 needs_review。

## 风险、边界与未确认项
- 未确认项待补充。

## 参考文献与来源链接
- Example: https://example.test/one
"""
    artifacts = ReportQualityArtifacts(
        report_markdown=report,
        access_checks=(_access("src_lit", SourceType.PUBLIC_LITERATURE, "https://example.test/one"),),
        claims=(),
        pdf_path=tmp_path / "missing.pdf",
    )

    # When: the deterministic evaluator checks the artifact.
    result = evaluate_report_quality(artifacts)

    # Then: it fails with explicit depth and source-diversity reasons.
    assert not result.passed
    assert any("source diversity" in reason for reason in result.reasons)
    assert any("topic-appropriate sections" in reason for reason in result.reasons)
    assert any("PDF" in reason for reason in result.reasons)


def test_evaluator_passes_device_parameter_report_with_free_citations(tmp_path: Path) -> None:
    # Given: a product-parameter research shape with tables, free links, gaps, and supported claims.
    report = """
# 神经调控设备刺激参数调研

## 1. 核心结论
- 参数窗口需要同时看频率、脉宽、电流和触点面积。[1](https://example.test/vendor-manual.pdf)
- 厂商资料不能直接等同临床结论。[2](https://example.test/literature)
- 监管资料用于确认公开注册边界。[3](https://example.test/regulatory)

## 背景与术语
本节解释适应证、刺激参数、程控场景和工程边界，避免把单篇论文写成行业共识。

## 技术/产品参数分析
| 参数 | 典型范围 | 来源 |
|---|---:|---|
| 频率 | 2-130 Hz | [1](https://example.test/vendor-manual.pdf) |
| 脉宽 | 60-450 us | [1](https://example.test/vendor-manual.pdf) |

## 竞品/厂商资料对照
| 来源类型 | 可用信息 | 使用边界 |
|---|---|---|
| 厂商手册 | 参数和产品说明 | 不能替代临床证据 |
| 论文 | 随访和安全讨论 | 不能代表全部产品 |

## 论文证据与监管资料
| 证据 | 来源 | 结论状态 |
|---|---|---|
| 参数与安全解释 | [2](https://example.test/literature) | supported |
| 注册路径 | [3](https://example.test/regulatory) | supported |

## 风险、边界与未确认项
- 未确认项：缺少完整临床随访和长期故障率，需要补充注册文件与真实世界资料。

## 参考文献与来源链接
- [1] Vendor manual: https://example.test/vendor-manual.pdf
- [2] Literature review: https://example.test/literature
- [3] Regulatory record: https://example.test/regulatory
"""
    artifacts = ReportQualityArtifacts(
        report_markdown=report,
        access_checks=(
            _access("src_vendor", SourceType.VENDOR_PUBLIC_DOC, "https://example.test/vendor-manual.pdf"),
            _access("src_lit", SourceType.PUBLIC_LITERATURE, "https://example.test/literature"),
            _access("src_reg", SourceType.PUBLIC_REGULATORY, "https://example.test/regulatory"),
        ),
        claims=(_claim("device", ["src_vendor", "src_lit", "src_reg"]),),
        pdf_path=_pdf(tmp_path),
    )

    # When: the deterministic evaluator checks the artifact.
    result = evaluate_report_quality(artifacts)

    # Then: it passes without depending on one disease, device class, or company.
    assert result.passed
    assert result.score >= 0.8


def test_evaluator_passes_company_regulatory_research_shape(tmp_path: Path) -> None:
    # Given: a different research shape centered on company signals and public regulatory evidence.
    report = """
# 影像辅助软件公司动态与注册线索调研

## 1. 核心结论
- 公司公告、监管记录和行业新闻需要分开使用。[1](https://example.test/news)
- 公开注册信息只能支持产品准入状态，不能证明临床优效。[2](https://example.test/device-record)
- 论文摘要适合补充算法评价口径。[3](https://example.test/abstract)

## 背景与术语
本节说明软件医疗器械、注册证、公开新闻和论文摘要之间的证据等级差异。

## 公司与市场动态
| 信号 | 内容 | 来源 |
|---|---|---|
| 公告 | 新版本发布 | [1](https://example.test/news) |
| 招采 | 医院采购线索 | [4](https://example.test/tender) |

## 监管/注册与产品边界
| 记录 | 适用范围 | 来源 |
|---|---|---|
| 注册记录 | 辅助检测软件 | [2](https://example.test/device-record) |

## 论文证据表
| 研究 | 可用结论 | 来源 |
|---|---|---|
| 算法评价 | 仅支持数据集表现 | [3](https://example.test/abstract) |

## 风险、边界与未确认项
- needs_review：缺少完整说明书和真实部署数据，下一步应补充公开产品手册与不良事件线索。

## 参考文献与来源链接
- [1] Company news: https://example.test/news
- [2] Device record: https://example.test/device-record
- [3] Abstract: https://example.test/abstract
- [4] Tender: https://example.test/tender
"""
    artifacts = ReportQualityArtifacts(
        report_markdown=report,
        access_checks=(
            _access("src_news", SourceType.PUBLIC_WEB, "https://example.test/news"),
            _access("src_reg", SourceType.PUBLIC_REGULATORY, "https://example.test/device-record"),
            _access("src_lit", SourceType.PUBLIC_LITERATURE, "https://example.test/abstract"),
            _access("src_tender", SourceType.PUBLIC_WEB, "https://example.test/tender"),
        ),
        claims=(_claim("company", ["src_news", "src_reg", "src_lit"]),),
        pdf_path=_pdf(tmp_path),
    )

    # When: the deterministic evaluator checks the artifact.
    result = evaluate_report_quality(artifacts)

    # Then: a non-DBS, non-electrode research shape can also pass.
    assert result.passed


def test_evaluator_rejects_long_report_without_supported_claims_or_references(tmp_path: Path) -> None:
    # Given: a long report that looks substantial but has no citable source support.
    report = "# 长报告\n\n" + "\n\n".join(
        f"## 章节 {index}\n这是一段很长的无来源分析，包含大量产品判断但没有引用或证据链。"
        for index in range(1, 18)
    )
    artifacts = ReportQualityArtifacts(
        report_markdown=report,
        access_checks=(),
        claims=(),
        pdf_path=_pdf(tmp_path),
    )

    # When: the evaluator checks the artifact.
    result = evaluate_report_quality(artifacts)

    # Then: length alone is not enough to pass.
    assert not result.passed
    assert any("supported claims" in reason for reason in result.reasons)
    assert any("free citations" in reason for reason in result.reasons)


def test_evaluator_rejects_free_cited_report_when_supported_claims_cover_only_one_source(tmp_path: Path) -> None:
    # Given: a deep report has three eligible references, but its supported claim only links one source.
    report = """
# 神经调控设备刺激参数调研

## 1. 核心结论
- 参数窗口需要同时看频率、脉宽和触点面积。[1](https://example.test/vendor-manual.pdf)
- 厂商资料和临床结论需要分开解释。[2](https://example.test/literature)

## 背景与方法
本节说明公开来源的证据边界和调研方法。

## 技术与产品参数分析
| 参数 | 典型范围 | 来源 |
|---|---:|---|
| 频率 | 2-130 Hz | [1](https://example.test/vendor-manual.pdf) |

## 论文与监管证据
| 证据 | 结论边界 | 来源 |
|---|---|---|
| 注册路径 | 非临床优效结论 | [3](https://example.test/regulatory) |

## 风险、边界与未确认项
- 未确认长期随访，仍存在证据缺口和产品边界。

## 参考文献与来源链接
- [1] Vendor manual: https://example.test/vendor-manual.pdf
- [2] Literature review: https://example.test/literature
- [3] Regulatory record: https://example.test/regulatory
"""
    artifacts = ReportQualityArtifacts(
        report_markdown=report,
        access_checks=(
            _access("src_vendor", SourceType.VENDOR_PUBLIC_DOC, "https://example.test/vendor-manual.pdf"),
            _access("src_lit", SourceType.PUBLIC_LITERATURE, "https://example.test/literature"),
            _access("src_reg", SourceType.PUBLIC_REGULATORY, "https://example.test/regulatory"),
        ),
        claims=(_claim("narrow", ["src_vendor"]),),
        pdf_path=_pdf(tmp_path),
    )

    # When: the evaluator checks the rendered artifact.
    result = evaluate_report_quality(artifacts)

    # Then: three references alone cannot substitute for broad source-linked evidence.
    assert not result.passed
    assert any("evidence breadth" in reason for reason in result.reasons)
