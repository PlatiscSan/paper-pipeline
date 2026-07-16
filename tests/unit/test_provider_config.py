
import pytest
from paper_pipeline.config import ExtractionConfig, ProviderConfig
from paper_pipeline.errors import PipelineError
from paper_pipeline.extract.openai_compatible import OpenAICompatibleProvider


def test_api_key_value_is_rejected_without_echo(monkeypatch: pytest.MonkeyPatch) -> None:
    leaked_value = "sk-example-secret-value"
    config = ProviderConfig(api_key_env=leaked_value)

    with pytest.raises(PipelineError) as caught:
        OpenAICompatibleProvider(config, ExtractionConfig())

    assert "environment variable name" in str(caught.value)
    assert leaked_value not in str(caught.value)
