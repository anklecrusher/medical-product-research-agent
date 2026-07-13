from __future__ import annotations

from medical_research_agent.evidence_gaps import detect_evidence_gaps, plan_follow_up_searches
from medical_research_agent.connectors.literature_access import attach_access_metadata
from medical_research_agent.parsers import DocumentParseError
from medical_research_agent.research_planning import ResearchFacetKind, build_query_expansion_plan
from medical_research_agent.schemas import (
    EvidenceItem,
    EvidenceKind,
    ParsedDocument,
    ResearchTask,
    SourceRecord,
    SourceType,
)
from medical_research_agent.source_contracts import AccessCheck, FreeAccessStatus
from medical_research_agent.workflow import follow_up
from medical_research_agent.workflow.query_expansion import build_search_items_from_expansion
from medical_research_agent.workflow.state import ResearchPlan


class PaywalledFollowUpVendorConnector:
    name = "duckduckgo_html"

    def search(self, request):
        return [
            SourceRecord(
                source_id="src_paywalled_follow_up",
                task_id=request.task_id,
                source_type=SourceType.VENDOR_PUBLIC_DOC,
                title="DBS clinician programmer manual paywalled portal",
                url="https://example.com/paywalled-dbs-programmer-manual",
                search_query=request.query,
                metadata={
                    "connector": self.name,
                    "snippet": "DBS clinician programmer interface manual with programming workflow details.",
                    "access_check": {
                        "source_id": "src_paywalled_follow_up",
                        "url": "https://example.com/paywalled-dbs-programmer-manual",
                        "status": FreeAccessStatus.PAYWALLED.value,
                        "checked_by": "test",
                    },
                },
            )
        ]


class FakeWebPageParser:
    name = "fake_web"

    def parse_url(self, source):
        raise DocumentParseError(self.name, f"should not parse rejected source {source.source_id}")


class FakePDFParser:
    name = "fake_pdf"

    def parse_url(self, source):
        raise DocumentParseError(self.name, f"should not parse rejected source {source.source_id}")


class PaywalledAccessVerifier:
    checked_source_ids: list[str] = []

    def verify(self, source: SourceRecord) -> AccessCheck:
        self.checked_source_ids.append(source.source_id)
        return AccessCheck(
            source_id=source.source_id,
            url=str(source.url),
            status=FreeAccessStatus.PAYWALLED,
            checked_by="test",
        )


class DeclaredMetadataOnlyFollowUpConnector:
    name = "duckduckgo_html"

    def search(self, request):
        source = SourceRecord(
            source_id="src_metadata_only_follow_up",
            task_id=request.task_id,
            source_type=SourceType.VENDOR_PUBLIC_DOC,
            title="DBS programmer specification metadata record",
            url="https://doi.org/10.1000/dbs-follow-up-metadata",
            search_query=request.query,
            metadata={"connector": self.name, "snippet": "DBS programmer specification evidence"},
        )
        return [
            attach_access_metadata(
                source,
                status=FreeAccessStatus.METADATA_ONLY,
                evidence_note="Metadata-only follow-up fixture.",
            )
        ]


class GenericFreeFollowUpAccessVerifier:
    def verify(self, source: SourceRecord) -> AccessCheck:
        return AccessCheck(
            source_id=source.source_id,
            url=str(source.url),
            status=FreeAccessStatus.FREE_LANDING_PAGE,
            checked_by="test-generic-verifier",
        )


def test_bounded_follow_up_uses_triage_access_metadata_before_parsing(monkeypatch) -> None:
    PaywalledAccessVerifier.checked_source_ids = []
    plan = _plan("调研 DBS 程控界面和论文证据")
    literature_source = SourceRecord(
        task_id="task_follow_up_triage",
        source_type=SourceType.PUBLIC_LITERATURE,
        title="DBS clinical literature evidence",
        url="https://example.com/literature",
        search_query="DBS literature",
        metadata={"facet": ResearchFacetKind.CLINICAL_STUDY.value},
    )
    literature_evidence = EvidenceItem(
        task_id="task_follow_up_triage",
        source_id=literature_source.source_id,
        kind=EvidenceKind.CLINICAL_FINDING,
        statement="Literature evidence exists for DBS programming.",
        metadata={"facet": ResearchFacetKind.CLINICAL_STUDY.value},
    )
    state = {
        "task": ResearchTask(task_id="task_follow_up_triage", query="调研 DBS 程控界面和论文证据"),
        "research_plan": plan,
        "sources": [literature_source],
        "rejected_sources": [],
        "documents": [],
        "evidence": [literature_evidence],
        "product_specs": [],
        "use_real_connectors": True,
    }

    monkeypatch.setattr(follow_up, "SourceAccessVerifier", PaywalledAccessVerifier)
    result = follow_up.run_bounded_follow_up(
        state,
        follow_up.FollowUpAdapters(
            vendor_connector=PaywalledFollowUpVendorConnector(),
            web_parser=FakeWebPageParser(),
            pdf_parser=FakePDFParser(),
        ),
    )

    follow_up_sources = [
        source for source in result.sources if source.metadata.get("follow_up_round") == 1
    ]
    rejected_follow_up = [
        source for source in result.rejected_sources if source.metadata.get("follow_up_round") == 1
    ]

    assert follow_up_sources == []
    assert [source.source_id for source in rejected_follow_up] == ["src_paywalled_follow_up"]
    assert rejected_follow_up[0].metadata["gap_facet"] in {"programmer_ui", "vendor_manual"}
    assert rejected_follow_up[0].metadata["bounded"] is True
    assert rejected_follow_up[0].metadata["llm_triage"]["decision"] == "rejected"
    assert "access_status_not_final_citable:paywalled" in rejected_follow_up[0].metadata["llm_triage"]["reasons"]
    assert PaywalledAccessVerifier.checked_source_ids == []
    assert result.follow_up_added_source_count == 0


def test_bounded_follow_up_preserves_declared_metadata_only_contract(monkeypatch) -> None:
    # Given: a follow-up candidate declares restrictive metadata-only access but a generic verifier sees a free page.
    plan = _plan("调研 DBS 程控界面和论文证据")
    state = {
        "task": ResearchTask(task_id="task_follow_up_metadata", query="调研 DBS 程控界面和论文证据"),
        "research_plan": plan,
        "sources": [],
        "rejected_sources": [],
        "documents": [],
        "evidence": [],
        "product_specs": [],
        "use_real_connectors": True,
    }
    monkeypatch.setattr(follow_up, "SourceAccessVerifier", GenericFreeFollowUpAccessVerifier)

    # When: bounded follow-up verifies and triages the declared source contract.
    result = follow_up.run_bounded_follow_up(
        state,
        follow_up.FollowUpAdapters(
            vendor_connector=DeclaredMetadataOnlyFollowUpConnector(),
            web_parser=FakeWebPageParser(),
            pdf_parser=FakePDFParser(),
        ),
    )

    # Then: the source stays rejected and never enters the parser-facing accepted source list.
    assert result.follow_up_added_source_count == 0
    rejected = [source for source in result.rejected_sources if source.source_id == "src_metadata_only_follow_up"]
    assert len(rejected) == 1
    assert rejected[0].metadata["access_check"]["status"] == FreeAccessStatus.METADATA_ONLY.value
    assert rejected[0].metadata["citation_eligibility"]["eligible"] is False


def _plan(query: str) -> ResearchPlan:
    expansion = build_query_expansion_plan(query)
    plan = ResearchPlan(
        objective="test plan",
        query_expansion=expansion,
        search_items=build_search_items_from_expansion(expansion),
        expected_evidence=[],
    )
    gaps = detect_evidence_gaps(plan, [], [])
    assert plan_follow_up_searches(plan, gaps, follow_up_round=1)
    return plan
