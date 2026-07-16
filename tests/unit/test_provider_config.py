import pytest
from paper_pipeline.config import ExtractionConfig, ProviderConfig
from paper_pipeline.errors import PipelineError
from paper_pipeline.extract.openai_compatible import OpenAICompatibleProvider


def test_missing_direct_api_key_is_rejected() -> None:
    with pytest.raises(PipelineError, match="not configured"):
        OpenAICompatibleProvider(ProviderConfig(), ExtractionConfig())


def test_direct_api_key_is_redacted() -> None:
    config = ProviderConfig(api_key="configured-secret")

    provider = OpenAICompatibleProvider(config, ExtractionConfig())

    assert provider.config.api_key.get_secret_value() == "configured-secret"
    assert "configured-secret" not in repr(provider.config)
