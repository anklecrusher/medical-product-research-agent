from medical_research_agent import ResearchTask, SourceRecord
from medical_research_agent.config import AppSettings
from medical_research_agent.schemas import SourceType


def test_core_schema_import_and_dump() -> None:
    task = ResearchTask(query="调研 DBS 脑电采集电极的关键参数")
    source = SourceRecord(
        task_id=task.task_id,
        source_type=SourceType.PUBLIC_LITERATURE,
        title="Example literature source",
        url="https://example.com/paper",
    )

    dumped = source.model_dump(mode="json")

    assert task.task_id.startswith("task_")
    assert dumped["source_type"] == "public_literature"
    assert dumped["url"] == "https://example.com/paper"


def test_runtime_directory_convention() -> None:
    settings = AppSettings()

    assert set(settings.runtime_dirs()) == {"data", "outputs", "cache", "uploads"}

