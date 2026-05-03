"""
Multi-model translator. Ported from heidegger/ and generalized for Greek→English.
"""

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_xai import ChatXAI
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Optional
import logging
import os


class DialogueTranslation(BaseModel):
    """Translation of one dialogue with reasoning."""
    translation: list[dict] = Field(
        description="List of {speaker, text} dicts — translated lines in order"
    )
    thinking: str = Field(
        description="Reasoning about translation choices, register, character voice"
    )
    key_terms: list[str] = Field(
        description="Greek terms worth flagging", default_factory=list
    )
    uncertainties: list[str] = Field(
        description="Judgment calls made", default_factory=list
    )


class Translator:
    """LangChain-based multi-model translator."""

    def __init__(self, model_name: str = "gpt-4o", **model_kwargs):
        self.model_name = model_name
        self.model = self._create_model(model_name, **model_kwargs)
        self.logger = logging.getLogger(__name__)

    def _create_model(self, model_name: str, **kwargs) -> BaseChatModel:
        defaults = {"temperature": 0.2, "max_tokens": 4000}
        defaults.update(kwargs)

        if model_name.startswith("gpt"):
            return ChatOpenAI(model=model_name, **defaults)
        elif model_name.startswith("claude"):
            return ChatAnthropic(model=model_name, **defaults)
        elif model_name.startswith("gemini"):
            gkw = {k: v for k, v in defaults.items() if k != "max_tokens"}
            gkw["max_output_tokens"] = kwargs.get("max_output_tokens", 8000)
            if "GOOGLE_API_KEY" in os.environ:
                gkw["google_api_key"] = os.environ["GOOGLE_API_KEY"]
            return ChatGoogleGenerativeAI(model=model_name, **gkw)
        elif model_name.startswith("grok"):
            gkw = dict(defaults)
            gkw["max_tokens"] = kwargs.get("max_tokens", 4000)
            return ChatXAI(model=model_name, **gkw)
        else:
            raise ValueError(f"Unsupported model: {model_name}")

    def translate(
        self,
        prompt: ChatPromptTemplate,
        dialogue: dict,
        prev_lines: Optional[list[dict]] = None,
        next_lines: Optional[list[dict]] = None,
    ) -> DialogueTranslation:
        """Translate a single dialogue."""
        parser = PydanticOutputParser(pydantic_object=DialogueTranslation)

        chain = prompt | self.model | parser

        return chain.invoke({
            "dialogue_title": dialogue["title"],
            "dialogue_id": dialogue["id"],
            "speakers": ", ".join(dialogue["speakers"]),
            "source_lines": self._format_lines(dialogue["lines"]),
            "prev_lines": self._format_lines(prev_lines) if prev_lines else "None",
            "next_lines": self._format_lines(next_lines) if next_lines else "None",
            "format_instructions": parser.get_format_instructions(),
        })

    def _format_lines(self, lines: list[dict]) -> str:
        return "\n".join(f"{l['speaker']}: {l['text']}" for l in lines)
