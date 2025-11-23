# ESP32OS Design Enhancement Plan

> Focus: Elevate UI/UX quality, consistency, accessibility, performance, and export parity across simulator, web designer, ASCII, and firmware C exports.

## 1. Design Principles
 
- Consistency: Single source of truth for tokens (color, spacing, typography, elevation).
- Clarity: Reduce visual noise; prioritize readable hierarchy (size, weight, contrast).
- Responsiveness: Seamless scaling across terminal sizes, web viewport widths, and embedded display dimensions.
- Accessibility: Contrast ratios, keyboard navigation, semantic grouping, predictable focus ordering.
- Performance: Animation efficiency (frame budget), minimal layout thrash, batching updates.
- Parity: Visual + interactive equivalence across ASCII, HTML, and exported C assets.

## 2. Token & Theming System

| Category | Status | Action | Output |
|----------|--------|--------|--------|
| Colors | Basic palettes | Introduce semantic roles (primary, surface, info, warning) | `ui_themes.py` enhancement |
| Spacing | Ad-hoc values | Define scale (4px steps) | Token map + doc |
| Typography | Limited weight tracking | Add size tiers + monospace fallback | Unified font map |
| Elevation | Not formalized | Add depth levels (0–4) with ASCII shading strategy | Elevation API |
| Animation | Scattered constants | Centralize durations & easing curves | `ui_animations.py` tokens |

## 3. Component Library Refinement

| Component | Gap | Improvement | Test Strategy |
|-----------|-----|------------|---------------|
| Button | Variant duplication | Variant enum + style resolver | Snapshot + ASCII diff |
| Dialog | Inconsistent padding | Apply spacing tokens | Layout measurement tests |
| Palette/Icon Grid | Alignment drift | Grid spec + min cell size | Export parity check |
| Tooltip | Contrast issues | Semantic color use + delay token | Interaction timing test |
| List / Tree | Scroll jitter | Virtualization prototype (batch render) | Perf frame log |

## 4. Layout & Responsive Rules

- Define breakpoint tiers: tiny (<40 cols), small (40–80), medium (80–120), wide (>120).
- ASCII compression rules: truncate labels, reduce padding first, then collapse icons.
- Web designer: auto-flow into 2–3 column adaptive grids for property panels.
- Firmware display: fallback rendering path with minimal diff from simulator.

## 5. Interaction & Keyboard Model

| Action | Key Default | Enhancement |
|--------|-------------|-------------|
| Focus cycle | Tab / Shift+Tab | Add Home/End jump |
| Component palette navigation | Arrows | Add type-to-filter and highlight |
| Undo/Redo | Ctrl+Z / Ctrl+Y | Show transient overlay "Reverted / Reapplied" |
| Multi-select add/remove | Shift+Click | Extend to Shift+Arrow for range |
| Context actions | Right-click | Provide keyboard menu (F10) |

## 6. Accessibility Targets

| Metric | Target |
|--------|--------|
| Color contrast (normal text) | WCAG AA (≥4.5:1) |
| Focus indicator | Minimum 2px, high-contrast |
| Keyboard coverage | 100% actionable elements |
| Reduced motion mode | All animations skip / shorten (<50ms) |

## 7. Animation Strategy

- Standard durations: fast 80ms, base 160ms, modal 240ms.
- Easing: use cubic-bezier tokens (easeOut, easeInOut).
- Frame budget: target ≤ 4ms per animation tick (CPU-bound).
- Profiling hook: add lightweight timing wrapper logging to `performance_profiler.py`.

## 8. Export Parity Workflow

| Stage | Action | Validation |
|-------|--------|------------|
| Design | Create / modify component | Visual diff (HTML vs ASCII) |
| Preview | Render in simulator | FPS + layout metrics captured |
| Export C | Generate header + assets | Compare dimensions & theming |
| HTML Snapshot | Write preview file | Pixel diff tolerance (<2%) |
| ASCII Snapshot | Write text grid | Rune diff (exact match) |

## 9. Performance Budgets (Design-Specific)

| Area | Budget | Monitoring |
|------|--------|-----------|
| Initial UI load (sim) | < 500ms | Timestamp logs |
| Palette open time | < 120ms | Event profiler |
| Animation CPU usage | < 10% single core | Profiler sampling |
| Reflow operations per action | ≤ 2 | Debug counters |

## 10. Proposed Refactors

- Central Token Registry: New `design_tokens.py` consolidating theme + spacing + typography + animation.
- Component Rendering Hooks: Introduce pre/post render callbacks for instrumentation.
- Responsive Evaluator: Utility to map current size class to component adjustments.
- ASCII Render Layer Cleanup: Replace scattered width calculations with unified function.

## 11. New Testing Additions

| Test Name | Purpose |
|-----------|---------|
| `test_design_tokens_consistency.py` | Ensure no duplicate / conflicting tokens |
| `test_ascii_html_parity_grid.py` | Snapshot parity for grid-based components |
| `test_responsive_breakpoints.py` | Assert layout changes at defined cols |
| `test_animation_budget.py` | Validate duration & easing registry |
| `test_accessibility_focus_cycle.py` | Ensure full keyboard traversal |

## 12. Incremental Delivery Plan

1. Token registry scaffold (read-only mapping consumed by existing modules).
2. Migrate color + spacing usage in 2–3 representative components.
3. Add responsive evaluator + breakpoints tests.
4. Integrate animation tokens; refactor existing constants.
5. Add accessibility focus traversal audit test.
6. Build export parity snapshot harness (HTML + ASCII + C sizes).
7. Integrate performance logging instrumentation.
8. Adopt virtualization experiment for large lists.

## 13. Risks & Mitigation (Design Scope)

| Risk | Mitigation |
|------|-----------|
| Token churn causing regressions | Migrate in small slices + snapshot tests |
| Over-abstraction slowing dev | Keep pure data maps; avoid dynamic factories early |
| Accessibility ignored in refactors | Add mandatory checklist in PR template |
| Performance instrumentation overhead | Lazy-enable instrumentation via flag |

## 14. Success Criteria (Design Focus)

- All core components use centralized tokens (≥90%).
- Export parity tests green across three formats for top 10 components.
- Accessibility keyboard coverage 100% in audit test.
- Animation CPU budget not exceeded in profiler runs.
- Responsive breakpoint tests stable for ASCII + HTML.

## 15. Immediate Action Candidates

| Priority | Task |
|----------|------|
| High | Create `design_tokens.py` scaffold |
| High | Add responsive breakpoint evaluator |
| High | Implement snapshot parity harness |
| Medium | Refactor color usage to semantic roles |
| Medium | Add accessibility focus traversal test |
| Medium | Integrate animation token map |
| Low | Virtualized list prototype |
| Low | Performance overlay for undo/redo feedback |

---
*This plan complements `PROJECT_ROADMAP.md` with deep UI/UX execution detail. Begin with token registry + responsive evaluator to minimize initial risk.*
