"""Self-contained raw HTML knowledge-base exports.

Unlike ``website_screenshot``, this representation delivers the authored HTML
itself. The archive remains directly inspectable, searchable, and renderable by
the Developer while fact ownership and article roles stay in an author-only
evaluation manifest.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from tau2.hyper.transformations.base import (
    KitFile,
    SectionTransformation,
    TransformationArtifact,
    register_transformation,
)
from tau2.utils.utils import DATA_DIR

_HTML_SUFFIXES = {".htm", ".html"}
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
_AUTHOR_ONLY_MARKERS = {
    "authoritative_fact_ids",
    "eval_manifest",
    "evidence_spans",
    "fact_id",
    "final_current",
}


class _ArchiveParser(HTMLParser):
    """Extract visible text, article identifiers, and resource references."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._ignored_depth = 0
        self.article_ids: list[str] = []
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in _IGNORED_TAGS:
            self._ignored_depth += 1
        elif not self._ignored_depth and tag in _BLOCK_TAGS:
            self._chunks.append("\n")
        if tag == "article" and attributes.get("data-article-id"):
            self.article_ids.append(str(attributes["data-article-id"]))
        for key in ("href", "src"):
            if attributes.get(key):
                self.references.append(str(attributes[key]))

    def handle_endtag(self, tag: str) -> None:
        if tag in _IGNORED_TAGS:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif not self._ignored_depth and tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self._chunks.append(f" {data} ")

    def visible_text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self._chunks).splitlines())
        return "\n".join(line for line in lines if line).rstrip() + "\n"


class KnowledgeBaseHTMLExportTransformation(SectionTransformation):
    """Deliver one or more self-contained raw HTML knowledge archives."""

    representation = "knowledge_base_html_export"
    aliases = ("html_knowledge_archive", "knowledge_base_html")
    placement = "named"
    carries_agent_utterances = False

    def discover_artifacts(
        self,
        schema: dict[str, Any],
        schema_path: Path,
        spec: dict[str, Any],
    ) -> list[TransformationArtifact]:
        del schema_path
        declared = spec.get("artifacts")
        if not declared:
            raise ValueError(
                "knowledge_base_html_export transformation for section schema "
                f"{schema.get('id', '<unknown>')!r} must declare artifacts"
            )

        shared_metadata = {
            key: spec[key]
            for key in (
                "minimum_articles",
                "minimum_context_articles",
            )
            if key in spec
        }
        artifacts = []
        for entry in declared:
            metadata = shared_metadata | {
                key: value
                for key, value in entry.items()
                if key not in {"included_fact_ids", "path"}
            }
            if metadata.get("eval_manifest_path"):
                metadata["eval_manifest_path"] = self._resolve(
                    metadata["eval_manifest_path"]
                )
            artifacts.append(
                TransformationArtifact(
                    source_path=self._resolve(entry["path"]),
                    included_fact_ids=list(entry.get("included_fact_ids", [])),
                    metadata=metadata,
                )
            )
        return artifacts

    def neutralize(self, artifact: TransformationArtifact, ordinal: int) -> KitFile:
        del ordinal
        return KitFile(
            relative_path=(f"{self.kit_dirname}/{artifact.metadata['kit_filename']}"),
            content=artifact.source_path.read_bytes(),
            artifact_kind=self.representation,
        )

    def to_text(self, artifact: TransformationArtifact) -> str:
        parser = self._parse(artifact.source_path)
        return parser.visible_text()

    def validate(
        self, schema: dict[str, Any], artifacts: list[TransformationArtifact]
    ) -> list[str]:
        issues = super().validate(schema, artifacts)
        seen_filenames: set[str] = set()
        for artifact in artifacts:
            path = artifact.source_path
            name = path.name
            suffix = path.suffix.lower()
            if suffix not in _HTML_SUFFIXES:
                issues.append(
                    f"{name}: knowledge-base export must be one of "
                    f"{sorted(_HTML_SUFFIXES)}"
                )
            if not path.is_file():
                issues.append(f"{name}: knowledge-base export not found")
                continue

            kit_filename = str(artifact.metadata.get("kit_filename") or "")
            if not kit_filename:
                issues.append(f"{name}: kit_filename is required")
            elif Path(kit_filename).name != kit_filename:
                issues.append(f"{name}: kit_filename must be a bare filename")
            elif Path(kit_filename).suffix.lower() != suffix:
                issues.append(f"{name}: kit_filename must preserve the source suffix")
            elif kit_filename in seen_filenames:
                issues.append(f"{name}: duplicate kit_filename {kit_filename!r}")
            if kit_filename:
                seen_filenames.add(kit_filename)

            try:
                raw_html = path.read_text()
            except UnicodeDecodeError:
                issues.append(f"{name}: knowledge-base export must be UTF-8")
                continue
            if "<!doctype html" not in raw_html[:200].lower():
                issues.append(f"{name}: knowledge-base export needs an HTML doctype")
            parser = self._parse(path)
            duplicate_ids = sorted(
                article_id
                for article_id in set(parser.article_ids)
                if parser.article_ids.count(article_id) > 1
            )
            if duplicate_ids:
                issues.append(f"{name}: duplicate article ids: {duplicate_ids}")
            external = sorted(
                {
                    ref
                    for ref in parser.references
                    if ref.lower().startswith(("http://", "https://", "//"))
                }
            )
            if external:
                issues.append(
                    f"{name}: archive must be self-contained; external references: "
                    f"{external}"
                )
            unresolved = sorted(
                {
                    ref
                    for ref in parser.references
                    if ref.startswith("#") and ref[1:] not in set(parser.article_ids)
                }
            )
            if unresolved:
                issues.append(
                    f"{name}: archive has unresolved internal references: {unresolved}"
                )
            lowered = raw_html.lower()
            leaked = sorted(
                marker for marker in _AUTHOR_ONLY_MARKERS if marker in lowered
            )
            if leaked:
                issues.append(f"{name}: author-only markers leaked into HTML: {leaked}")

            minimum_articles = artifact.metadata.get("minimum_articles", 1)
            if not isinstance(minimum_articles, int) or minimum_articles < 1:
                issues.append(f"{name}: minimum_articles must be an integer >= 1")
            elif len(parser.article_ids) < minimum_articles:
                issues.append(
                    f"{name}: archive has {len(parser.article_ids)} articles; "
                    f"minimum is {minimum_articles}"
                )

            manifest_path = artifact.metadata.get("eval_manifest_path")
            if not manifest_path:
                issues.append(f"{name}: eval_manifest_path is required")
            else:
                issues.extend(
                    self._validate_eval_manifest(
                        name,
                        Path(manifest_path),
                        artifact,
                        parser.article_ids,
                    )
                )
        return issues

    @staticmethod
    def _validate_eval_manifest(
        artifact_name: str,
        manifest_path: Path,
        artifact: TransformationArtifact,
        article_ids: list[str],
    ) -> list[str]:
        if not manifest_path.is_file():
            return [f"{artifact_name}: eval_manifest_path not found"]
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as error:
            return [f"{artifact_name}: invalid eval manifest JSON ({error})"]

        issues: list[str] = []
        if manifest.get("filename") != artifact.source_path.name:
            issues.append(f"{artifact_name}: eval manifest filename must match source")
        articles = manifest.get("articles") or []
        manifest_ids = [
            str(article.get("article_id"))
            for article in articles
            if isinstance(article, dict) and article.get("article_id")
        ]
        if len(manifest_ids) != len(set(manifest_ids)):
            issues.append(f"{artifact_name}: eval manifest article ids must be unique")
        if set(manifest_ids) != set(article_ids):
            issues.append(
                f"{artifact_name}: eval manifest articles must exactly match HTML "
                "data-article-id values"
            )

        owned: list[str] = []
        context_count = 0
        for article in articles:
            if not isinstance(article, dict):
                continue
            facts = article.get("authoritative_fact_ids") or []
            if facts:
                owned.extend(str(fact_id) for fact_id in facts)
            else:
                context_count += 1
        if len(owned) != len(set(owned)):
            issues.append(f"{artifact_name}: a fact is owned by multiple articles")
        if set(owned) != set(artifact.included_fact_ids):
            issues.append(
                f"{artifact_name}: article authority must exactly match "
                "included_fact_ids"
            )
        if set(manifest.get("authoritative_fact_ids") or []) != set(
            artifact.included_fact_ids
        ):
            issues.append(
                f"{artifact_name}: eval manifest authoritative_fact_ids must "
                "match included_fact_ids"
            )
        minimum_context = artifact.metadata.get("minimum_context_articles", 0)
        if not isinstance(minimum_context, int) or minimum_context < 0:
            issues.append(
                f"{artifact_name}: minimum_context_articles must be an integer >= 0"
            )
        elif context_count < minimum_context:
            issues.append(
                f"{artifact_name}: archive has {context_count} context articles; "
                f"minimum is {minimum_context}"
            )
        return issues

    @staticmethod
    def _parse(path: Path) -> _ArchiveParser:
        parser = _ArchiveParser()
        parser.feed(path.read_text())
        parser.close()
        return parser

    @staticmethod
    def _resolve(path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return DATA_DIR / resolved


register_transformation(KnowledgeBaseHTMLExportTransformation())
