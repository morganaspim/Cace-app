from __future__ import annotations

from dataclasses import dataclass

from .hybrid import GrowResult


@dataclass(frozen=True)
class GrowCandidate:
    candidate_id: str
    target_kind: str
    target_ids: tuple[str, ...]
    title: str
    detail: str
    score: float
    novelty: float | None = None


def _short_fragment_id(fragment_id: str) -> str:
    source = fragment_id.split(":", 1)[0]
    name = source.rsplit("/", 1)[-1]
    return name or source or fragment_id[:48]


def build_grow_candidates(
    result: GrowResult,
    *,
    limit: int = 5,
    max_groups: int = 3,
) -> tuple[GrowCandidate, ...]:
    """Build a small, stable, mixed shortlist for explicit user feedback.

    Group and fragment scores are not directly comparable, so the shortlist
    intentionally reserves space for both rather than pretending they share one
    calibrated score scale.
    """
    limit = max(1, int(limit))
    max_groups = max(0, min(int(max_groups), limit))
    candidates: list[GrowCandidate] = []

    for index, group in enumerate(result.groups[:max_groups], start=1):
        ids = tuple(sorted(group.fragment_ids))
        names = tuple(_short_fragment_id(item) for item in ids)
        candidates.append(
            GrowCandidate(
                candidate_id="group:" + "|".join(ids),
                target_kind="group",
                target_ids=ids,
                title=f"Combination {index}: " + " + ".join(names),
                detail=(
                    f"{group.rationale} "
                    f"Diversity {group.diversity:.2f}; novelty {group.novelty:.2f}."
                ),
                score=float(group.score),
                novelty=float(group.novelty),
            )
        )

    remaining = limit - len(candidates)
    used_fragment_ids = {
        fragment_id
        for candidate in candidates
        for fragment_id in candidate.target_ids
    }

    ranked_fragments = [
        item
        for item in result.retrieved
        if item.fragment.fragment_id not in used_fragment_ids
    ]
    # If group coverage consumed nearly every top fragment, allow the strongest
    # individual fragments back in rather than leaving empty card slots.
    if len(ranked_fragments) < remaining:
        seen = {item.fragment.fragment_id for item in ranked_fragments}
        ranked_fragments.extend(
            item
            for item in result.retrieved
            if item.fragment.fragment_id not in seen
        )

    added: set[str] = set()
    for ranked in ranked_fragments:
        fragment = ranked.fragment
        if fragment.fragment_id in added:
            continue
        added.add(fragment.fragment_id)
        candidates.append(
            GrowCandidate(
                candidate_id="fragment:" + fragment.fragment_id,
                target_kind="fragment",
                target_ids=(fragment.fragment_id,),
                title=f"Source idea: {_short_fragment_id(fragment.fragment_id)}",
                detail=(
                    f"{fragment.kind} · {fragment.source}. "
                    "Rate this source concept independently from combinations."
                ),
                score=float(ranked.score),
                novelty=None,
            )
        )
        if len(candidates) >= limit:
            break

    return tuple(candidates[:limit])
