# Designer Reference

## States every screen must have

- **Default** — nominal data, one user, one role.
- **Loading** — skeleton or spinner, with expected time cue.
- **Empty (first-time)** — no data yet; teach the primary action.
- **Empty (cleared)** — user cleared filters / results; offer a reset.
- **Partial** — some data, some not (e.g. one column still loading).
- **Error (recoverable)** — failure with a retry affordance.
- **Error (terminal)** — failure that requires escalation; explain what to do.
- **Permission-denied** — logged-in but not allowed.
- **Rate-limited / throttled** — what the user sees and when to try again.
- **Offline** — cached view + banner explaining staleness.
- **Read-only** — view without edit affordances; explain why.

## Component spec checklist

- [ ] Sizes, spacing, corner radius, elevation — all from design tokens.
- [ ] Colour tokens only — no hex values in specs.
- [ ] Type scale token named per element (not "16px semibold").
- [ ] Interaction states: default, hover, focus-visible, active, disabled, loading.
- [ ] Keyboard: tab order, Enter/Space behaviour, Esc to dismiss, arrow keys where relevant.
- [ ] Screen reader: accessible name, role, state announcements.
- [ ] Motion: duration, easing, and a reduced-motion variant.
- [ ] Responsive breakpoints and reflow behaviour.
- [ ] RTL behaviour.

## Accessibility floor (WCAG 2.2 AA)

- [ ] Text contrast ≥ 4.5:1 (≥ 3:1 for large text).
- [ ] Non-text contrast ≥ 3:1 for interactive boundaries and icons.
- [ ] Every interactive element reachable and operable by keyboard.
- [ ] Focus indicator is visible against every background it sits on.
- [ ] No information conveyed by colour alone.
- [ ] Form fields have persistent labels, not placeholder-as-label.
- [ ] Errors identified in text, not only by colour.
- [ ] Target size ≥ 24×24 CSS px (44×44 recommended for touch primary actions).
- [ ] Animations respect `prefers-reduced-motion`.

## Copy principles

- Lead with the user's action, not the system's state ("Save changes", not "Submission successful").
- Errors: what happened, why, what to do next.
- Never blame the user.
- Numbers: localisation-safe format.
- Dates & times: relative near-term, absolute far-term; always include timezone when it matters.

## Anti-patterns

- Hand-off with only "happy path" Figma frames.
- Error state = generic "Something went wrong."
- Empty state = blank page.
- Tooltips carrying critical information.
- Icon-only buttons without `aria-label`.
- Modals stacked on modals.
- Placeholder as the only label.
- "We'll refine the copy later."
- Interaction described in prose but not in the prototype.

## Design review self-check before handoff

- [ ] Every flow has a named user and a named goal.
- [ ] Every screen × every state exists.
- [ ] Every string is final or owned.
- [ ] Every component ties to a token or a system component.
- [ ] Accessibility pass complete.
- [ ] Engineering can build it with zero back-and-forth on basic states.
