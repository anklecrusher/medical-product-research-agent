from medical_research_agent.research_planning import (
    EvidenceGap,
    EvidenceGapStatus,
    QueryExpansionPlan,
    ResearchFacetKind,
    SearchRoute,
    SourceQualitySignal,
    SourceReviewDecision,
    TerminologyCategory,
    build_query_expansion_plan,
)
from medical_research_agent.schemas import SourceType


def test_chinese_device_topic_expands_to_bilingual_planning_terms() -> None:
    # Given: a Chinese medical-device research topic with stimulation, contacts, and UI intent.
    topic = "调研交叉刺激与8触点刺激的相关程控逻辑和ui界面"

    # When: the topic is parsed into the planning schema.
    plan = build_query_expansion_plan(topic)
    dumped = plan.model_dump_json()

    # Then: the serialized plan preserves intent and includes reusable English terminology.
    assert isinstance(plan, QueryExpansionPlan)
    assert plan.original_query == topic
    assert "interleaving stimulation" in plan.english_terms
    assert "8-contact lead" in plan.english_terms
    assert "clinician programmer" in plan.english_terms
    assert "programming interface" in plan.english_terms
    assert "vendor manual" in plan.english_terms
    assert "interleaving stimulation" in dumped

    facet_kinds = {facet.kind for facet in plan.facets}
    assert ResearchFacetKind.STIMULATION in facet_kinds
    assert ResearchFacetKind.ELECTRODE_CONTACTS in facet_kinds
    assert ResearchFacetKind.PROGRAMMER_UI in facet_kinds
    assert ResearchFacetKind.VENDOR_MANUAL in facet_kinds
    assert any(SourceType.VENDOR_PUBLIC_DOC in route.source_types for route in plan.search_routes)


def test_generic_topic_creates_safe_needs_review_plan() -> None:
    # Given: a topic with no recognized medical-device terminology.
    topic = "证明黎曼猜想的直觉解释"

    # When: the topic is parsed into the planning schema.
    plan = build_query_expansion_plan(topic)

    # Then: the result remains usable but does not invent medical-device facets.
    assert plan.original_query == topic
    assert [facet.kind for facet in plan.facets] == [ResearchFacetKind.GENERIC_BACKGROUND]
    assert [route.source_types for route in plan.search_routes] == [(SourceType.PUBLIC_WEB,)]
    assert [gap.status for gap in plan.evidence_gaps] == [EvidenceGapStatus.NEEDS_REVIEW]
    assert "stimulation" not in plan.english_terms


def test_unrelated_chinese_research_topic_remains_generic() -> None:
    # Given: an unrelated math topic containing the generic Chinese word "research".
    topic = "研究黎曼猜想和素数分布的数学直觉"

    # When: the topic is parsed into the planning schema.
    plan = build_query_expansion_plan(topic)

    # Then: generic research wording alone does not invent a clinical-study facet.
    assert [facet.kind for facet in plan.facets] == [ResearchFacetKind.GENERIC_BACKGROUND]
    assert plan.recognized_categories == ()
    assert plan.english_terms == ()


def test_short_ascii_ui_trigger_does_not_match_inside_guide() -> None:
    # Given: an unrelated English query contains "ui" only inside longer words.
    topic = "warehouse shelving guide and guideline review"

    # When: the topic is parsed into the planning schema.
    plan = build_query_expansion_plan(topic)

    # Then: substring-only UI collisions do not invent programmer/UI planning facets.
    assert [facet.kind for facet in plan.facets] == [ResearchFacetKind.GENERIC_BACKGROUND]
    assert TerminologyCategory.PROGRAMMER_UI not in plan.recognized_categories
    assert "clinician programmer" not in plan.english_terms


def test_scs_only_topic_persists_domain_specific_english_terms() -> None:
    # Given: an SCS-specific stimulation topic.
    topic = "调研 SCS 刺激参数的产品范围和论文证据"

    # When: the topic is parsed into the planning schema.
    plan = build_query_expansion_plan(topic)

    # Then: persisted expansion terms stay in the SCS domain.
    assert "spinal cord stimulation" in plan.english_terms
    assert "deep brain stimulation" not in plan.english_terms
    assert "DBS programmer" not in plan.english_terms
    assert "interleaving stimulation" not in plan.english_terms


def test_dbs_only_topic_persists_domain_specific_english_terms() -> None:
    # Given: a DBS-specific stimulation topic.
    topic = "调研 DBS 电极阻抗的论文证据和程控资料"

    # When: the topic is parsed into the planning schema.
    plan = build_query_expansion_plan(topic)

    # Then: persisted expansion terms stay in the DBS domain.
    assert "deep brain stimulation" in plan.english_terms
    assert "spinal cord stimulation" not in plan.english_terms
    assert "SCS programmer" not in plan.english_terms
    assert "interleaving stimulation" not in plan.english_terms


def test_planning_models_serialize_quality_and_gap_contracts() -> None:
    # Given: route, quality, and gap records that later workflow nodes can persist.
    route = SearchRoute(
        facet=ResearchFacetKind.CLINICAL_STUDY,
        source_types=(SourceType.PUBLIC_LITERATURE,),
        queries=("spinal cord stimulation clinical study",),
        priority=20,
        rationale="clinical evidence should be checked against literature sources",
    )
    signal = SourceQualitySignal(
        facet=ResearchFacetKind.CLINICAL_STUDY,
        source_type=SourceType.PUBLIC_LITERATURE,
        relevance_score=0.75,
        credibility_score=0.8,
        source_fit_score=0.7,
        decision=SourceReviewDecision.PENDING_REVIEW,
        reasons=("abstract mentions target indication",),
    )
    gap = EvidenceGap(
        facet=ResearchFacetKind.PRIVATE_LOCAL_DOCS,
        status=EvidenceGapStatus.NEEDS_REVIEW,
        description="private uploaded manuals require local-only review",
        required_source_types=(SourceType.USER_UPLOADED_PRIVATE,),
        recommended_queries=("uploaded programmer manual",),
    )
    facet = build_query_expansion_plan("调研上传说明书中的程控限制").facets[0]

    # When: records are embedded in a plan and serialized.
    plan = QueryExpansionPlan(
        original_query="调研上传说明书中的程控限制",
        normalized_query="调研上传说明书中的程控限制",
        recognized_categories=("private_local_docs",),
        chinese_terms=("上传", "说明书", "程控"),
        english_terms=("uploaded private document", "programmer manual"),
        facets=(facet,),
        search_routes=(route,),
        evidence_gaps=(gap,),
        quality_signals=(signal,),
    )
    dumped = plan.model_dump(mode="json")

    # Then: enums and source types serialize into stable JSON-friendly values.
    assert dumped["search_routes"][0]["source_types"] == ["public_literature"]
    assert dumped["quality_signals"][0]["decision"] == "pending_review"
    assert dumped["evidence_gaps"][0]["required_source_types"] == ["user_uploaded_private"]
