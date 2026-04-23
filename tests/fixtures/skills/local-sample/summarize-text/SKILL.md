---
name: summarize-text
description: Use when the user asks to summarise a chunk of prose into a short TL;DR plus a bullet list of the key points.
version: 0.1.0
license: MIT
tags: [writing, summarisation]
resources:
  - SKILL.md
  - reference.md
---

# Text summariser

Produce a concise summary of the user-supplied text in two parts.

## 1. TL;DR

Write a single sentence of no more than 30 words that captures the core claim or event of the source text. Do not hedge; pick the strongest reading.

## 2. Key points

Emit 3-5 bullets. Each bullet is one sentence. Preserve proper nouns, numbers, and dates verbatim from the source — no paraphrasing of those.

## 3. When to defer

If the input text is shorter than ~80 words, tell the user it is already short enough and ask whether they want a rewrite instead of a summary. See `reference.md` for the detailed rubric.
