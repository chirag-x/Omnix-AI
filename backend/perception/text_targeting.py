"""Deterministic text-target ranking for UIA and OCR observations.

The vision layer must prefer refusing an ambiguous click over selecting the first
rough substring match.  This module contains no desktop dependencies so the
matching behavior can be regression-tested without moving the user's mouse.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata


@dataclass
class TextCandidate:
    text: str
    left: int
    top: int
    right: int
    bottom: int
    confidence: float = 1.0
    source: str = "unknown"
    payload: object = None

    @property
    def center(self):
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def _text_score(target: str, candidate: str, exact: bool = True) -> float:
    target_n = normalize_text(target)
    candidate_n = normalize_text(candidate)
    if not target_n or not candidate_n:
        return 0.0
    if target_n == candidate_n:
        return 1.0

    target_words = target_n.split()
    candidate_words = candidate_n.split()
    if target_words and len(target_words) <= len(candidate_words):
        for start in range(len(candidate_words) - len(target_words) + 1):
            if candidate_words[start:start + len(target_words)] == target_words:
                # Whole-word containment is safe enough for labels that include
                # a role suffix, but exact labels still rank first.
                extra = len(candidate_words) - len(target_words)
                return max(0.90, 0.96 - min(extra, 6) * 0.01)

    ratio = SequenceMatcher(None, target_n, candidate_n).ratio()
    # OCR commonly confuses I/l/1 or drops one character. Keep the fuzzy gate
    # high so neighboring contacts with merely similar names are not accepted.
    minimum = 0.91 if exact else 0.86
    if ratio >= minimum:
        return ratio * 0.94
    return 0.0


def _region_bounds(region: str, window_bounds):
    left, top, right, bottom = window_bounds
    width, height = right - left, bottom - top
    mid_x, mid_y = left + width * 0.5, top + height * 0.5
    name = normalize_text(region or "any").replace(" ", "_")
    if name in {"any", "all", "window"}:
        return left, top, right, bottom
    if name in {"left", "chat_list"}:
        return left, top, left + width * 0.48, bottom
    if name == "right":
        return mid_x, top, right, bottom
    if name == "top":
        return left, top, right, top + height * 0.35
    if name == "bottom":
        return left, top + height * 0.65, right, bottom
    if name in {"top_left", "left_top"}:
        return left, top, mid_x, mid_y
    if name in {"top_right", "right_top", "chat_header", "header"}:
        return left + width * 0.42, top, right, top + height * 0.25
    if name in {"bottom_right", "right_bottom", "message_box"}:
        return left + width * 0.42, top + height * 0.60, right, bottom
    if name in {"bottom_left", "left_bottom"}:
        return left, mid_y, mid_x, bottom
    raise ValueError(f"Unknown screen region '{region}'.")


def _in_region(candidate: TextCandidate, bounds) -> bool:
    x, y = candidate.center
    left, top, right, bottom = bounds
    return left <= x < right and top <= y < bottom


def _overlap_ratio(a: TextCandidate, b: TextCandidate) -> float:
    left, top = max(a.left, b.left), max(a.top, b.top)
    right, bottom = min(a.right, b.right), min(a.bottom, b.bottom)
    intersection = max(0, right - left) * max(0, bottom - top)
    if not intersection:
        return 0.0
    area_a = max(1, (a.right - a.left) * (a.bottom - a.top))
    area_b = max(1, (b.right - b.left) * (b.bottom - b.top))
    return intersection / min(area_a, area_b)


def _deduplicate(candidates):
    kept = []
    for candidate in sorted(candidates, key=lambda item: item.confidence, reverse=True):
        duplicate = any(
            normalize_text(candidate.text) == normalize_text(other.text)
            and (_overlap_ratio(candidate, other) >= 0.55
                 or (abs(candidate.center[0] - other.center[0]) <= 5
                     and abs(candidate.center[1] - other.center[1]) <= 5))
            for other in kept
        )
        if not duplicate:
            kept.append(candidate)
    return kept


def select_text_candidate(
    candidates,
    target: str,
    window_bounds,
    region: str = "any",
    exact: bool = True,
    min_confidence: float = 0.45,
):
    """Return ``(candidate, error)`` after strict ranking and ambiguity checks."""
    try:
        bounds = _region_bounds(region, window_bounds)
    except ValueError as exc:
        return None, f"Error: {exc}"

    ranked = []
    for candidate in _deduplicate(candidates):
        if candidate.confidence < min_confidence or not _in_region(candidate, bounds):
            continue
        text_score = _text_score(target, candidate.text, exact=exact)
        if not text_score:
            continue
        combined = text_score * (0.75 + 0.25 * min(1.0, candidate.confidence))
        ranked.append((combined, text_score, candidate))

    if not ranked:
        return None, (
            f"Error: No reliable {'exact ' if exact else ''}match for '{target}' "
            f"was found in region '{region}'."
        )

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best = ranked[0]
    if len(ranked) > 1:
        second = ranked[1]
        separated = (
            abs(best[2].center[0] - second[2].center[0]) > 12
            or abs(best[2].center[1] - second[2].center[1]) > 12
        )
        if separated and (best[0] - second[0] < 0.045 or best[1] == second[1] == 1.0):
            locations = ", ".join(
                f"'{item[2].text}' at {item[2].center}" for item in ranked[:3]
            )
            return None, (
                f"Error: Ambiguous text target '{target}'. Multiple strong matches were found: "
                f"{locations}. Narrow the region or provide more identifying text."
            )
    return best[2], None


def build_ocr_candidates(detections, offset_x=0, offset_y=0):
    """Create word/phrase candidates from OCR detections, including split lines.

    Each input item is ``(bbox, text, confidence)`` where bbox contains four
    corner points in image-relative coordinates.
    """
    raw = []
    for bbox, text, confidence in detections:
        cleaned = str(text or "").strip()
        if not cleaned or not bbox:
            continue
        xs = [float(point[0]) for point in bbox]
        ys = [float(point[1]) for point in bbox]
        raw.append(TextCandidate(
            cleaned,
            int(offset_x + min(xs)), int(offset_y + min(ys)),
            int(offset_x + max(xs)), int(offset_y + max(ys)),
            float(confidence if confidence is not None else 0.0),
            "ocr",
        ))

    lines = []
    for candidate in sorted(raw, key=lambda item: (item.center[1], item.left)):
        height = max(1, candidate.bottom - candidate.top)
        line = next((row for row in lines if abs(row[0][0].center[1] - candidate.center[1]) <= max(height, row[1]) * 0.65), None)
        if line is None:
            lines.append([[candidate], height])
        else:
            line[0].append(candidate)
            line[1] = max(line[1], height)

    combined = list(raw)
    for row, height in lines:
        row.sort(key=lambda item: item.left)
        for start in range(len(row)):
            phrase = []
            for end in range(start, min(len(row), start + 7)):
                current = row[end]
                if phrase and current.left - phrase[-1].right > max(24, height * 3.2):
                    break
                phrase.append(current)
                if len(phrase) < 2:
                    continue
                combined.append(TextCandidate(
                    " ".join(item.text for item in phrase),
                    min(item.left for item in phrase), min(item.top for item in phrase),
                    max(item.right for item in phrase), max(item.bottom for item in phrase),
                    min(item.confidence for item in phrase),
                    "ocr-phrase",
                ))
    return _deduplicate(combined)


def build_tesseract_candidates(data, offset_x=0, offset_y=0):
    detections = []
    count = len(data.get("text", []))
    for index in range(count):
        text = str(data["text"][index] or "").strip()
        if not text:
            continue
        left = int(data.get("left", [0] * count)[index])
        top = int(data.get("top", [0] * count)[index])
        width = int(data.get("width", [0] * count)[index])
        height = int(data.get("height", [0] * count)[index])
        raw_conf = data.get("conf", [75] * count)[index]
        try:
            confidence = max(0.0, min(1.0, float(raw_conf) / 100.0))
        except (TypeError, ValueError):
            confidence = 0.75
        bbox = [[left, top], [left + width, top], [left + width, top + height], [left, top + height]]
        detections.append((bbox, text, confidence))
    return build_ocr_candidates(detections, offset_x, offset_y)
