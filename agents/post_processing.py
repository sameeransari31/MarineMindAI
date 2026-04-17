"""
Post-processing — Cleans LLM output to remove markdown artifacts.
"""
import re


def strip_markdown_artifacts(text: str) -> str:
    """
    Remove markdown formatting symbols while preserving content structure.
    Keeps numbered lists, dash bullet points, and plain text formatting.
    """
    # Remove markdown bold/italic: **text** → text, __text__ → text, *text* → text
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'(?<!\[)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)

    # Remove markdown headings: ## Heading → Heading
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove code fences: ```...``` → content
    text = re.sub(r'```[\w]*\n?', '', text)

    # Remove inline code backticks: `code` → code
    text = re.sub(r'`(.+?)`', r'\1', text)

    # Remove horizontal rules: --- or *** or ___
    text = re.sub(r'^[\-\*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Clean up excessive blank lines (more than 2 consecutive)
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    return text.strip()
