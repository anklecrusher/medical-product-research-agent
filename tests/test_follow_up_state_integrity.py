from __future__ import annotations

from medical_research_agent.research_planning import build_query_expansion_plan
from medical_research_agent.schemas import (
    DocumentFormat,
    EvidenceItem,
    EvidenceKind,
    ParsedDocument,
    ProductSpec,
    ResearchTask,
    SourceRecord,
    SourceType,
)
from medical_research_agent.source_contracts import AccessCheck, FreeAccessStatus
from medical_research_agent.workflow import follow_up
from medical_research_agent.workflow.query_expansion import build_search_items_from_expansion
from medical_research_agent.workflow.state import ResearchPlan, WorkflowState


class EmptyConnector:
    name = "empty"

    def search(self, request):
        return []


class UnusedParser:
    def parse_url(self, source):
        raise AssertionError(f"parser should not be called for {source.source_id}")


class AcceptedFollowUpConnector:
    name = "accepted_follow_up"

    def search(self, request):
        return [
            SourceRecord(
                source_id="src_follow_up",
                task_id=request.task_id,
                source_type=SourceType.VENDOR_PUBLIC_DOC,
                title="DBS clinician programmer manual",
                url="https://example.test/dbs-programmer-manual",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class AcceptedFollowUpParser:
    def parse_url(self, source: SourceRecord) -> ParsedDocument:
        return ParsedDocument(
            task_id=source.task_id,
            source_id=source.source_id,
            format=DocumentFormat.WEB_PAGE,
            title=source.title,
            text="DBS clinician programmer interface frequency 130 Hz and pulse width 60 us.",
            parser_name="accepted_follow_up",
        )


class FreeAccessVerifier:
    def verify(self, source: SourceRecord) -> AccessCheck:
        return AccessCheck(
            source_id=source.source_id,
            url=source.url,
            status=FreeAccessStatus.FREE_LANDING_PAGE,
            checked_by="test",
        )


def test_bounded_follow_up_preserves_llm_results_when_no_follow_up_runs(monkeypatch) -> None:
    # Given: LLM-derived evidence and specs already exist, with no actionable follow-up item.
    evidence, spec = _llm_results()
    state = _state(evidence=[evidence], product_specs=[spec])
    monkeypatch.setattr(follow_up, "plan_follow_up_searches", lambda plan, gaps, follow_up_round: [])

    # When: the bounded follow-up node has nothing to search.
    result = follow_up.run_bounded_follow_up(state, _adapters())

    # Then: the prior LLM state is returned unchanged rather than re-extracted away.
    assert [item.evidence_id for item in result.evidence] == [evidence.evidence_id]
    assert [item.spec_id for item in result.product_specs] == [spec.spec_id]


def test_follow_up_node_refreshes_source_quality_status_after_accepting_source(monkeypatch) -> None:
    # Given: the initial search was under-sourced and a bounded follow-up can supply a valid manual.
    evidence, spec = _llm_results()
    state = _state(evidence=[evidence], product_specs=[spec])
    state["intermediate"] = {"source_quality_status": "needs_more_sources"}
    state["task"] = state["task"].model_copy(update={"query": "调研 DBS 程控界面和说明书"})
    expansion = build_query_expansion_plan(state["task"].query)
    state["research_plan"] = ResearchPlan(
        objective="Fill programmer evidence gaps.",
        query_expansion=expansion,
        search_items=build_search_items_from_expansion(expansion),
    )
    monkeypatch.setattr(follow_up, "DuckDuckGoHTMLSearchConnector", lambda source_type: AcceptedFollowUpConnector())
    monkeypatch.setattr(follow_up, "WebPageParser", AcceptedFollowUpParser)
    monkeypatch.setattr(follow_up, "PDFParser", AcceptedFollowUpParser)
    monkeypatch.setattr(follow_up, "SourceAccessVerifier", FreeAccessVerifier)
    monkeypatch.setattr(
        follow_up,
        "route_connectors",
        lambda item, settings: (AcceptedFollowUpConnector(),),
    )

    # When: the workflow follow-up node accepts the new source.
    update = follow_up.follow_up_evidence_gaps(state)

    # Then: the stale initial quality status is explicitly refreshed.
    assert update["intermediate"]["follow_up_added_source_count"] > 0
    assert update["intermediate"]["source_quality_status"] == "has_accepted_sources"
    assert evidence.evidence_id in {item.evidence_id for item in update["evidence"]}
    assert spec.spec_id in {item.spec_id for item in update["product_specs"]}


def _state(*, evidence: list[EvidenceItem], product_specs: list[ProductSpec]) -> WorkflowState:
    query = "General public medical product research"
    expansion = build_query_expansion_plan(query)
    return {
        "task": ResearchTask(task_id="task_follow_up_integrity", query=query),
        "research_plan": ResearchPlan(
            objective="Preserve prior extraction state.",
            query_expansion=expansion,
            search_items=build_search_items_from_expansion(expansion),
        ),
        "sources": [],
        "rejected_sources": [],
        "documents": [],
        "evidence": evidence,
        "product_specs": product_specs,
        "use_real_connectors": True,
    }


def _llm_results() -> tuple[EvidenceItem, ProductSpec]:
    evidence = EvidenceItem(
        evidence_id="ev_llm",
        task_id="task_follow_up_integrity",
        source_id="src_llm",
        kind=EvidenceKind.ENGINEERING_NOTE,
        statement="Schema-bound LLM evidence.",
        metadata={"extraction_method": "llm"},
    )
    spec = ProductSpec(
        spec_id="spec_llm",
        product_name="DBS system",
        parameter_name="frequency",
        value="130",
        unit="Hz",
        source_ids=["src_llm"],
        evidence_ids=[evidence.evidence_id],
    )
    return evidence, spec


def _adapters() -> follow_up.FollowUpAdapters:
    parser = UnusedParser()
    return follow_up.FollowUpAdapters(
        vendor_connector=EmptyConnector(),
        web_parser=parser,
        pdf_parser=parser,
    )
