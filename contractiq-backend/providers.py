"""Bounded provider fallback; never mix a partial stream with a second provider."""
import time
from collections.abc import Callable, Iterator
from threading import Event
from typing import TypeVar

from pydantic import BaseModel

from config import Settings
from errors import ServiceError
from llm import GroqLLM
from telemetry import provider_span

T = TypeVar("T", bound=BaseModel)


class ProviderChain:
    def __init__(self, providers: list[GroqLLM]):
        if not providers:
            raise ValueError("At least one provider is required")
        self.providers = providers

    def close(self) -> None:
        for provider in self.providers:
            provider.close()

    def generate(self, schema: type[T], prompt: str, *, deadline: float,
                 validate: Callable[[T], None] | None = None) -> T:
        for index, provider in enumerate(self.providers):
            budget = deadline if index == len(self.providers) - 1 else time.monotonic() + max(0, deadline - time.monotonic()) / 2
            model_name = getattr(provider, "model", getattr(getattr(provider, "settings", None), "groq_model", "unknown"))
            try:
                with provider_span(provider.name, model_name) as usage:
                    try:
                        return provider.generate(schema, prompt, deadline=budget, validate=validate)
                    finally:
                        usage.update(provider.usage)
            except ServiceError as exc:
                if exc.status not in {502, 503, 504} or index == len(self.providers) - 1 or time.monotonic() >= deadline:
                    raise
        raise ServiceError(503, "The analysis providers are unavailable.")

    def stream_json(self, schema: type[BaseModel], prompt: str, *, deadline: float, cancelled: Event) -> Iterator[str]:
        for index, provider in enumerate(self.providers):
            emitted = False
            budget = deadline if index == len(self.providers) - 1 else time.monotonic() + max(0, deadline - time.monotonic()) / 2
            model_name = getattr(provider, "model", getattr(getattr(provider, "settings", None), "groq_model", "unknown"))
            try:
                with provider_span(provider.name, model_name) as usage:
                    try:
                        for delta in provider.stream_json(schema, prompt, deadline=budget, cancelled=cancelled):
                            if cancelled.is_set():
                                return
                            emitted = emitted or bool(delta)
                            yield delta
                    finally:
                        usage.update(provider.usage)
                return
            except ServiceError as exc:
                if emitted or cancelled.is_set() or exc.status not in {502, 503, 504} or index == len(self.providers) - 1:
                    raise


def create_provider(settings: Settings) -> ProviderChain:
    providers: list[GroqLLM] = []

    if settings.groq_api_key:
        providers.append(GroqLLM(
            settings,
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            base_url="https://api.groq.com/openai/v1",
            name="groq",
        ))

    if settings.openai_api_key:
        providers.append(GroqLLM(
            settings,
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            name="openai",
        ))

    if settings.ollama_base_url:
        providers.append(GroqLLM(
            settings,
            api_key="",
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            name="ollama",
        ))

    if settings.fallback_api_key and settings.fallback_base_url and settings.fallback_model:
        fallback = settings.model_copy(update={
            "groq_api_key": settings.fallback_api_key,
            "groq_model": settings.fallback_model,
            "structured_mode": settings.fallback_structured_mode,
        })
        providers.append(GroqLLM(fallback, api_key=settings.fallback_api_key, model=settings.fallback_model, base_url=settings.fallback_base_url, name="fallback"))

    if not providers:
        providers.append(GroqLLM(settings, name="unconfigured"))

    return ProviderChain(providers)
