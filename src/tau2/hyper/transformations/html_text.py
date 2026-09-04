"""Visible-text extraction shared by HTML-backed evidence transformations."""

from html.parser import HTMLParser
from pathlib import Path

_BLOCK_TAGS = {
    "article",
    "aside",
    "br",
    "div",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "main",
    "nav",
    "p",
    "section",
    "table",
    "td",
    "th",
    "tr",
}
_IGNORED_TAGS = {"noscript", "script", "style", "template"}


class _VisibleTextParser(HTMLParser):
    """Small, dependency-free visible-text extractor for authored HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in _IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif not self._ignored_depth and tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._chunks.append(f" {data} ")

    def text(self) -> str:
        """Return normalized visible text with block boundaries preserved."""
        lines = (" ".join(line.split()) for line in "".join(self._chunks).splitlines())
        return "\n".join(line for line in lines if line).rstrip() + "\n"


def visible_text_from_html(path: str | Path) -> str:
    """Extract visible text from an authored HTML document."""
    parser = _VisibleTextParser()
    parser.feed(Path(path).read_text())
    parser.close()
    return parser.text()
