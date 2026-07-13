"""Bounded source-strategy planning from user intent and optional LLM JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, assert_never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from medical_research_agent.llm.client import (
    LLMClient,
    LLMRequestFailedError,
    MissingLLMAPIKeyError,
    UnsupportedLLMProviderError,
)
from medical_research_agent.llm.models import LLMMessage, LLMRequest
from medical_research_agent.schemas import SourceType
from medical_research_agent.source_contracts import SourceRoute, SourceStrategy
from medical_research_agent.source_strategy_catalog import (
    DEFAULT_FOLLOW_UP_ROUNDS,
    MAX_ROUTE_BUDGET,
    ROUTE_TEMPLATES,
    TEMPLATES_BY_ID,
    RouteTemplate,
    template_for,
)
from medical_research_agent.source_strategy_heuristics import (
    all_expansion_terms,
    fallback_follow_up_intents,
    fallback_route_ids,
    requires_private_local_only,
)

if TYPE_CHECKING:
    from medical_research_agent.workflow.state import ResearchIntent, SearchPlanItem


@dataclass(frozen=True, slots=True)
class SourceStrategyPlan:
    strategy: SourceStrategy
    follow_up_intents: tuple[str, ...]
    audit_reasons: tuple[str, ...]
    external_llm_used: bool


@dataclass(frozen=True, slots=True)
class StrategyBuildRequest:
    intent: ResearchIntent
    route_ids: tuple[str, ...]
    budgets: dict[str, int]
    follow_up_intents: tuple[str, ...]
    external_llm_used: bool


class LLMRouteBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    route_id: str = Field(min_length=1)
    budget: int = Field(ge=1)


class LLMSourceStrategyProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    objective: str = Field(min_length=1)
    selected_routes: tuple[str, ...] = Field(min_length=1)
    route_budgets: tuple[LLMRouteBudget, ...] = Field(default=())
    follow_up_intents: tuple[str, ...] = Field(default=())
    rationale: str = Field(min_length=1)


def plan_source_strategy(intent: "ResearchIntent", llm_client: LLMClient | None = None) -> SourceStrategyPlan:
    """Plan bounded source routes without allowing arbitrary LLM tools or URLs."""

    audit_reasons: list[str] = []

    if requires_private_local_only(intent):
        audit_reasons.append("private_local_only:external_llm_disabled_by_default")
        return _build_plan(
            StrategyBuildRequest(
                intent=intent,
                route_ids=("local_docs",),
                budgets={},
                follow_up_intents=(),
                external_llm_used=False,
            ),
            audit_reasons,
        )

    proposal = _llm_proposal(intent, llm_client, audit_reasons)
    route_ids, budgets = _routes_and_budgets(intent, proposal, llm_client, audit_reasons)
    follow_up_intents = proposal.follow_up_intents if proposal is not None else fallback_follow_up_intents(intent)
    return _build_plan(
        StrategyBuildRequest(
            intent=intent,
            route_ids=route_ids,
            budgets=budgets,
            follow_up_intents=follow_up_intents,
            external_llm_used=proposal is not None,
        ),
        audit_reasons,
    )


def search_items_from_source_strategy(strategy: SourceStrategy) -> list["SearchPlanItem"]:
    """Convert bounded strategy routes into existing connector search items."""

    from medical_research_agent.workflow.state import SearchPlanItem

    return [
        SearchPlanItem(
            query=query,
            source_type=source_type,
            rationale=route.rationale,
            facet=route.facet,
            expanded_terms=list(template_for(route.route_id).query_terms),
            preferred_connectors=list(route.connectors),
            route_priority=index * 10,
            limit=route.budget,
            metadata={"source_strategy_route_id": route.route_id},
        )
        for index, route in enumerate(strategy.routes, start=1)
        for query in route.queries
        for source_type in route.source_types
    ]


def _routes_and_budgets(
    intent: "ResearchIntent",
    proposal: LLMSourceStrategyProposal | None,
    llm_client: LLMClient | None,
    audit_reasons: list[str],
) -> tuple[tuple[str, ...], dict[str, int]]:
    if proposal is None:
        if llm_client is not None and not any(reason.startswith("llm_error:") for reason in audit_reasons):
            audit_reasons.append("llm_output_invalid:fallback_strategy_used")
        return fallback_route_ids(intent), {}

    if not _recognized_route_ids(proposal.selected_routes):
        audit_reasons.append("llm_selected_no_known_routes:fallback_strategy_used")
        return fallback_route_ids(intent), {}

    return proposal.selected_routes, {item.route_id: item.budget for item in proposal.route_budgets}


def _llm_proposal(
    intent: "ResearchIntent",
    llm_client: LLMClient | None,
    audit_reasons: list[str],
) -> LLMSourceStrategyProposal | None:
    if llm_client is None:
        return None

    request = LLMRequest(
        messages=[
            LLMMessage(
                role="system",
                content=(
                    "Return JSON only. Select source route IDs from the fixed catalog. "
                    "Do not include URLs, browser tools, shell tools, or connector names outside the catalog."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    f"Query: {intent.original_query}\n"
                    f"Allowed route IDs: {', '.join(template.route_id for template in ROUTE_TEMPLATES)}"
                ),
            ),
        ],
        temperature=0.0,
        max_tokens=800,
        response_format={"type": "json_object"},
        source_types=[SourceType.PUBLIC_WEB],
    )
    try:
        return LLMSourceStrategyProposal.model_validate_json(llm_client.complete(request).content)
    except (MissingLLMAPIKeyError, UnsupportedLLMProviderError, LLMRequestFailedError) as exc:
        audit_reasons.append(llm_strategy_failure_reason(exc))
        return None
    except (ValidationError, json.JSONDecodeError):
        return None


def llm_strategy_failure_reason(
    error: MissingLLMAPIKeyError | UnsupportedLLMProviderError | LLMRequestFailedError,
) -> str:
    """Return a stable provider diagnostic without exposing response content or secrets."""

    match error:
        case MissingLLMAPIKeyError(env_var=env_var):
            return f"llm_error:MissingLLMAPIKeyError:env_var={env_var}:fallback_strategy_used"
        case UnsupportedLLMProviderError(provider=provider):
            return f"llm_error:UnsupportedLLMProviderError:provider={provider}:fallback_strategy_used"
        case LLMRequestFailedError(attempts=attempts):
            return f"llm_error:LLMRequestFailedError:attempts={attempts}:fallback_strategy_used"
        case unreachable:
            assert_never(unreachable)


def _build_plan(request: StrategyBuildRequest, audit_reasons: list[str]) -> SourceStrategyPlan:
    routes: list[SourceRoute] = []
    for route_id in request.route_ids:
        template = TEMPLATES_BY_ID.get(route_id)
        if template is None:
            audit_reasons.append(f"unknown_route:{route_id}")
            continue
        routes.append(_route_from_template(request.intent, template, _bounded_budget(route_id, template, request.budgets, audit_reasons)))

    selected_routes = tuple(_unique(routes))
    if not selected_routes:
        selected_routes = (_route_from_template(request.intent, template_for("vendor_company"), 2),)
        audit_reasons.append("empty_strategy:vendor_company_fallback")

    strategy = SourceStrategy(
        objective=f"围绕“{request.intent.original_query}”规划公开且有边界的资料检索策略。",
        routes=selected_routes,
        max_follow_up_rounds=DEFAULT_FOLLOW_UP_ROUNDS,
        privacy_note="Private/local sources stay local unless explicitly enabled.",
    )
    return SourceStrategyPlan(
        strategy=strategy,
        follow_up_intents=request.follow_up_intents,
        audit_reasons=tuple(audit_reasons),
        external_llm_used=request.external_llm_used,
    )


def _route_from_template(intent: "ResearchIntent", template: RouteTemplate, budget: int) -> SourceRoute:
    query = " ".join((intent.original_query, *template.query_terms, *all_expansion_terms(intent))).strip()
    return SourceRoute(
        route_id=template.route_id,
        facet=template.facet,
        source_types=template.source_types,
        connectors=template.connectors,
        queries=(query,),
        budget=budget,
        rationale=template.rationale,
    )


def _bounded_budget(
    route_id: str,
    template: RouteTemplate,
    budgets: dict[str, int],
    audit_reasons: list[str],
) -> int:
    budget = budgets.get(route_id, template.default_budget)
    clamped_budget = min(budget, MAX_ROUTE_BUDGET)
    if clamped_budget != budget:
        audit_reasons.append(f"budget_clamped:{route_id}:{budget}->{clamped_budget}")
    return clamped_budget


def _recognized_route_ids(route_ids: Iterable[str]) -> tuple[str, ...]:
    return tuple(route_id for route_id in route_ids if route_id in TEMPLATES_BY_ID)


def _unique[T](values: Iterable[T]) -> tuple[T, ...]:
    result: list[T] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
