"""Modality profiles for kit materialization.

One canonical bundle backs every capability tier. Each artifact keeps its
authored rendition set (a screenshot's PNG next to the HTML it was rendered
from, a phone call's transcript next to its committed ``.m4a``), and the kit
builder *materializes* the tree for a target model class by substitution:
an artifact whose delivered modality exceeds the profile is replaced by its
shippable text rendition; an artifact with a richer rendition the profile
allows (a phone call under an audio-capable profile) is upgraded to it.

Substitution — never addition — matters: shipping a screenshot's visible
text next to its PNG would let vision models grep the text and skip
``view_image``, collapsing the image-fact-discovery signal the benchmark
measures. A profile therefore selects exactly one rendition per artifact.

Profiles are sets of modalities encoded as a ``+``-joined string in the
fixed order ``text+image+audio+video`` (``"full"`` is an alias for all
four). ``text`` is always implied. The default profile preserves the
pre-profile kit contents byte-for-byte: images and videos ship natively,
audio stays an opt-in upgrade of text-native call records.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MODALITY_ORDER: tuple[str, ...] = ("text", "image", "audio", "video")

_IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
_AUDIO_SUFFIXES = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}
_VIDEO_SUFFIXES = {".mkv", ".mov", ".mp4", ".webm"}


@dataclass(frozen=True)
class ModalityProfile:
    """The set of artifact modalities a kit materialization may deliver."""

    modalities: frozenset[str]

    def __post_init__(self) -> None:
        unknown = self.modalities - set(MODALITY_ORDER)
        if unknown:
            raise ValueError(f"unknown modalities: {sorted(unknown)}")
        if "text" not in self.modalities:
            object.__setattr__(
                self, "modalities", self.modalities | frozenset(["text"])
            )

    def allows(self, modality: str) -> bool:
        return modality in self.modalities

    def __str__(self) -> str:
        return "+".join(m for m in MODALITY_ORDER if m in self.modalities)


def parse_modality_profile(spec: str | ModalityProfile) -> ModalityProfile:
    """Parse ``"text+image"``-style profile strings (alias ``"full"``)."""
    if isinstance(spec, ModalityProfile):
        return spec
    normalized = str(spec).strip().lower()
    if not normalized:
        raise ValueError("modality profile must not be empty")
    if normalized == "full":
        return ModalityProfile(frozenset(MODALITY_ORDER))
    tokens = [token.strip() for token in normalized.split("+")]
    unknown = [token for token in tokens if token not in MODALITY_ORDER]
    if unknown:
        raise ValueError(
            f"unknown modalities {unknown} in profile {spec!r}; expected "
            f"a '+'-joined subset of {list(MODALITY_ORDER)} or 'full'"
        )
    return ModalityProfile(frozenset(tokens))


#: Preserves pre-profile kit contents: images and videos ship natively,
#: audio remains an opt-in upgrade for audio-capable model classes.
DEFAULT_KIT_MODALITY_PROFILE = parse_modality_profile("text+image+video")


def modality_for_suffix(suffix: str) -> str:
    """Classify a delivered file's modality by suffix.

    Anything that is not a raster image, audio, or video container counts as
    text: office formats and PDFs in this tree are HTML-derived prints with
    real text layers, extractable with the sandbox's shell tools.
    """
    normalized = suffix.lower()
    if normalized in _IMAGE_SUFFIXES:
        return "image"
    if normalized in _AUDIO_SUFFIXES:
        return "audio"
    if normalized in _VIDEO_SUFFIXES:
        return "video"
    return "text"


def modality_for_path(path: str | Path) -> str:
    return modality_for_suffix(Path(path).suffix)
