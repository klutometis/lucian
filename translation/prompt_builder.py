"""
Builds LangChain prompts from STYLE.md, CONVENTIONS.md, GLOSSARY.md.
"""

from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path


class TranslationPromptBuilder:
    def __init__(self, config_dir: Path = Path("translation")):
        self.config_dir = config_dir
        self.style = self._load("STYLE.md")
        self.conventions = self._load("CONVENTIONS.md")
        self.glossary = self._load("GLOSSARY.md")

    def _load(self, filename: str) -> str:
        p = self.config_dir / filename
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def build_translation_prompt(self, format_instructions: str = "") -> ChatPromptTemplate:
        system = f"""You are translating Lucian of Samosata's *Dialogues of the Dead*
from Ancient Greek into English.

# Translation Style
{self.style}

# Conventions
{self.conventions}

# Glossary
{self.glossary}

# Output Format
Respond with valid JSON matching this schema exactly:
{{format_instructions}}
"""
        human = """## Dialogue {dialogue_id}: {dialogue_title}
Speakers: {speakers}

### Previous dialogue's last lines (for continuity):
{prev_lines}

### This dialogue (translate this):
{source_lines}

### Next dialogue's first lines (for resolution awareness):
{next_lines}
"""
        return ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", human),
        ])
