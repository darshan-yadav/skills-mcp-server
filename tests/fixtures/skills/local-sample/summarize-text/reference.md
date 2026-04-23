# Summarisation rubric (reference)

This reference is loaded by the `summarize-text` skill. It exists primarily
as a test fixture for the bundle-layout rules in SPEC §6.2 and the
resource-exposure rules in SPEC §8.2.

## Length heuristics

| Input length (words) | Recommended action |
|---|---|
| < 80 | Decline; offer a rewrite instead. |
| 80-400 | Single-paragraph TL;DR, 3 bullets. |
| 400-2000 | TL;DR sentence, 5 bullets. |
| > 2000 | Ask the user to chunk or specify a focus area first. |

## Style notes

- Prefer active voice.
- Never invent facts not in the source.
- Preserve named entities, numbers, dates, and direct quotes verbatim.
- If the source text contains contradictions, surface them explicitly in a
  final "Tensions" bullet rather than silently picking one side.
