"""Fully configurable OpenAI-compatible provider adapter."""

import json
import os
import re
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI, BadRequestError
from paper_pipeline.config import ExtractionConfig, ProviderConfig
from paper_pipeline.errors import ErrorCode, PipelineError
from paper_pipeline.extract.provider import AIResult
from paper_pipeline.extract.schema import parse_json_object, validate

SYSTEM = """Extract only facts supported by the supplied paper. Do not guess.
Use null for missing scalars and [] for missing lists. Preserve original numbers,
units, experimental conditions and physical page numbers. Distinguish body text,
tables, figures, and supplements. Never invent quotations or attribute cited
experiments to review authors."""


class OpenAICompatibleProvider:
    def __init__(self, config: ProviderConfig, extraction: ExtractionConfig) -> None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", config.api_key_env):
            raise PipelineError(
                ErrorCode.CONFIG_INVALID,
                "api_key_env must be an environment variable name, not an API key value",
            )
        key = os.getenv(config.api_key_env, "")
        if not key and not config.allow_empty_api_key:
            raise PipelineError(
                ErrorCode.CONFIG_INVALID, f"environment variable {config.api_key_env} is not set"
            )
        self.config, self.extraction = config, extraction
        self.client = AsyncOpenAI(
            api_key=key or "unused",
            base_url=config.base_url,
            default_headers=config.extra_headers,
            timeout=extraction.timeout_seconds,
            max_retries=extraction.retries,
        )

    async def extract_text(
        self, text: str, schema: dict[str, Any], merge: bool = False
    ) -> AIResult:
        instruction = (
            "Merge partial objects without combining distinct experimental conditions. "
            if merge
            else "Extract structured data from this paper section. "
        )
        for mode in self._modes():
            kwargs: dict[str, Any] = dict(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": instruction + "\n\n" + text},
                ],
                **self.config.request_options,
            )
            kwargs[self.config.output_token_param] = self.extraction.max_output_tokens
            if mode == "strict":
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "extraction", "strict": True, "schema": schema},
                }
            elif mode == "json":
                kwargs["response_format"] = {"type": "json_object"}
            else:
                kwargs["messages"][1]["content"] += "\nReturn only JSON matching:\n" + json.dumps(
                    schema
                )
            try:
                response = await self.client.chat.completions.create(**kwargs)
            except BadRequestError:
                if mode != self._modes()[-1]:
                    continue
                raise PipelineError(
                    ErrorCode.AI_UNSUPPORTED_FEATURE, f"structured mode {mode} unsupported"
                ) from None
            data = parse_json_object(response.choices[0].message.content or "")
            validate(data, schema)
            usage = response.usage
            return AIResult(
                data,
                response.id,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            )
        raise PipelineError(ErrorCode.AI_UNSUPPORTED_FEATURE, "no structured output mode succeeded")

    async def extract_file(self, path: Path, schema: dict[str, Any]) -> AIResult:
        uploaded = await self.client.files.create(file=path, purpose="user_data")
        try:
            response = await self.client.responses.create(  # type: ignore[call-overload]
                model=self.config.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_file", "file_id": uploaded.id},
                            {
                                "type": "input_text",
                                "text": SYSTEM + "\nSchema:\n" + json.dumps(schema),
                            },
                        ],
                    }
                ],
                **{self.config.output_token_param: self.extraction.max_output_tokens},
                **self.config.request_options,
            )
            data = parse_json_object(response.output_text)
            validate(data, schema)
            usage = response.usage
            return AIResult(
                data,
                response.id,
                getattr(usage, "input_tokens", 0),
                getattr(usage, "output_tokens", 0),
            )
        finally:
            if not self.config.keep_remote_file:
                await self.client.files.delete(uploaded.id)

    def _modes(self) -> list[str]:
        return (
            ["strict", "json", "prompt"]
            if self.config.structured_output == "auto"
            else [self.config.structured_output]
        )
