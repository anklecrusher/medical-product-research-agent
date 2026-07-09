"""Public source connectors."""

from medical_research_agent.connectors.base import ConnectorError, ConnectorErrorKind, SearchRequest, SourceConnector
from medical_research_agent.connectors.clinical_trials import ClinicalTrialsConnector
from medical_research_agent.connectors.crossref import CrossrefConnector
from medical_research_agent.connectors.openfda import OpenFDA510kConnector
from medical_research_agent.connectors.pubmed import PubMedConnector
from medical_research_agent.connectors.semantic_scholar import SemanticScholarConnector
from medical_research_agent.connectors.url import URLSourceConnector
from medical_research_agent.connectors.web_search import DuckDuckGoHTMLSearchConnector

__all__ = [
    "ClinicalTrialsConnector",
    "ConnectorError",
    "ConnectorErrorKind",
    "CrossrefConnector",
    "DuckDuckGoHTMLSearchConnector",
    "OpenFDA510kConnector",
    "PubMedConnector",
    "SearchRequest",
    "SemanticScholarConnector",
    "SourceConnector",
    "URLSourceConnector",
]
