# Design Review Checklist

## 1. Goal clarity

- [ ] User and goal are named.
- [ ] Success signal is stated in user-observable terms.
- [ ] Scope (and non-scope) of the design is written.

## 2. Flow integrity

- [ ] Every entry point is accounted for.
- [ ] Every user decision has both branches designed.
- [ ] Exits (cancel, back, dismiss, done) behave consistently.
- [ ] Error paths are real paths, not dead ends.

## 3. State coverage

For every screen, confirm designs exist for:

- Default
- Loading
- Empty (first-time)
- Empty (cleared / no matches)
- Partial / mixed-ready
- Error (recoverable)
- Error (terminal)
- Permission-denied
- Rate-limited
- Offline
- Read-only

## 4. Accessibility (WCAG 2.2 AA)

- [ ] Text contrast ≥ 4.5:1.
- [ ] Non-text contrast ≥ 3:1 on interactive boundaries.
- [ ] Keyboard reachability and focus order defined.
- [ ] Focus indicator visible on every background.
- [ ] Target sizes meet the minimum (≥ 24×24, 44×44 for touch primaries).
- [ ] No colour-only signalling.
- [ ] Motion respects `prefers-reduced-motion`.
- [ ] Screen reader names for icon-only controls.

## 5. Design system consistency

- [ ] Tokens used (no raw hex / px).
- [ ] Components used from the system where applicable.
- [ ] Any "exception" component is justified and flagged for system intake.
- [ ] Spacing rhythm consistent with existing screens.

## 6. Copy quality

- [ ] Every primary and secondary CTA has intentional wording.
- [ ] Errors: what, why, what to do next.
- [ ] No "Something went wrong" without detail.
- [ ] Numbers, dates, currency are localisation-safe.
- [ ] Character limits stated where text reflows.

## 7. Responsive & RTL

- [ ] Breakpoints named; reflow rules defined.
- [ ] RTL layout considered for direction-sensitive elements.

## 8. Handoff readiness

- [ ] Engineering can map every interactive element to a component.
- [ ] Every state has a frame or a written spec.
- [ ] Motion durations and easing named.
- [ ] Open questions have owners and deadlines.
- [ ] Acceptance criteria exist and are user-observable.

## Comment style

- Lead with the user harm or engineering blocker.
- Concrete examples: name the screen / component / string.
- Severity on every comment: **blocker**, **non-blocker**, **nit**.
- Praise at least one thing.
