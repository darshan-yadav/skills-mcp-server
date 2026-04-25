---
version: alpha
name: Warm Ledger
description: A calm, editorial administration surface for curating skill bundles with clear hierarchy and a single warm accent.
colors:
  primary: "#17191C"
  secondary: "#67707A"
  tertiary: "#C2623D"
  neutral: "#F4EFE8"
  surface: "#FFFDF9"
  surface-alt: "#ECE4D8"
  border: "#D6C8B5"
  success: "#1F6A43"
  danger: "#9B3C2F"
typography:
  headline-lg:
    fontFamily: Iowan Old Style
    fontSize: 56px
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Iowan Old Style
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: -0.02em
  body-md:
    fontFamily: Avenir Next
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  label-sm:
    fontFamily: IBM Plex Mono
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: 0.04em
rounded:
  sm: 8px
  md: 14px
  lg: 22px
  full: 9999px
spacing:
  xs: 6px
  sm: 10px
  md: 16px
  lg: 24px
  xl: 32px
components:
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: 12px
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 12px
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    rounded: "{rounded.md}"
    padding: 16px
  code-editor:
    backgroundColor: "#F8F2E9"
    textColor: "{colors.primary}"
    rounded: "{rounded.sm}"
    padding: 16px
---

# Warm Ledger

## Overview

Warm Ledger is an admin-facing visual system for skill curation. It should feel editorial rather than dashboard-generic: deliberate hierarchy, soft paper-toned surfaces, and crisp operational tooling. The emotional tone is calm authority, not consumer cheerfulness or enterprise coldness.

## Colors

The palette is built on warm neutrals with one clay accent that carries almost all interaction weight.

- **Primary (`#17191C`)** is deep ink for headings, dense text, and anchors.
- **Secondary (`#67707A`)** is quiet slate for metadata, borders, and supporting labels.
- **Tertiary (`#C2623D`)** is the only warm action color for save, create, and high-intent actions.
- **Neutral (`#F4EFE8`)** is the page field: softer than white and intentionally tactile.
- **Surface / Surface-alt** create tonal layering instead of heavy chrome.
- **Success / Danger** are operational states only; they should never compete with the primary action color.

## Typography

Typography should separate strategic from operational information.

- **Headlines** use a serif display voice to create editorial gravity and clear hierarchy.
- **Body** uses a clean humanist sans for long-form readability.
- **Labels and metadata** use a mono voice for paths, source names, counts, timestamps, and system state.

## Layout

The admin UI uses a fixed-max content shell with roomy internal spacing and card containment. Dense information is allowed, but it must be grouped into strongly bounded surfaces with clear vertical rhythm. Search, edit, and upload affordances should always remain visually scannable.

## Elevation & Depth

Depth comes from tonal layers, subtle borders, and a soft ambient shadow. Avoid glossy or floating-product visuals. The interface should feel like crafted paper and tooling, not glass.

## Shapes

Use medium-soft corners consistently. Cards should feel approachable, but inputs and buttons still need engineered precision. Full-pill rounding is reserved for chips and status indicators.

## Components

- **Primary buttons** carry the clay accent and should be visually singular within a section.
- **Secondary buttons** are bordered and quiet.
- **Cards** are the default containment primitive for skills, sources, file lists, and editors.
- **Code/text editors** should feel distinct from cards through a slightly darker paper tone, not a black terminal aesthetic.

## Do's and Don'ts

- Do use the tertiary accent for one dominant action at a time.
- Do keep metadata visually subordinate using mono labels and muted tone.
- Do maintain WCAG AA contrast on text and controls.
- Don't introduce a second bright accent color.
- Don't mix radically different corner styles in the same view.
- Don't make the admin UI look like a consumer marketing page or a default analytics dashboard.
