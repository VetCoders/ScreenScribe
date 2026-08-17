# Shared HTML shell (review + analyze)

Both browser surfaces — the `review` report viewer and the `analyze` workspace —
render through **one** server-composed HTML skeleton. There is no per-mode HTML
fork: each mode is a declarative config that the shared renderer turns into a
full document.

## Where it lives

| Piece | Path | Role |
|-------|------|------|
| Skeleton | `screenscribe/html_pro_assets/templates/shell.html` | The invariant frame with `{slot:...}` placeholders. |
| Slot renderer | `screenscribe/shell/renderer.py` | `render_surface(config, context)` fills every slot, owns asset/script ordering, server-side i18n, and asserts no slot is left unfilled. |
| Surface configs | `screenscribe/shell/surface.py` | `REVIEW_SURFACE` and `ANALYZE_SURFACE` — the per-mode capability maps. |
| Partials | `screenscribe/html_pro_assets/templates/partials/` | Reusable slot bodies (`video_panel`, `transcript_panel`, `tabbar`, `header_right`, `export_panel`, …). |
| Layout controller | `screenscribe/html_pro_assets/scripts/lib/layout-control.js` | Measures the wrapped header and keeps `--header-height` synchronized for both surfaces and every responsive breakpoint. |

The review renderer (`screenscribe/html_pro/renderer.py`,
`render_html_report_pro`) builds review-specific context and calls
`render_surface(REVIEW_SURFACE, context)`. The analyze server
(`screenscribe/analyze_server.py`) calls `render_surface(ANALYZE_SURFACE, context)`.

The header is intentionally allowed to wrap below 1200 px. Do not hardcode a
second breakpoint-specific content offset: the shared layout controller measures
the rendered header (including language and window-action rows) and writes the
actual pixel height to `--header-height`. The desktop fixed shell and the mobile
stacked shell both consume that one value.

Tabs use a roving-tabindex contract: the active tab has `tabindex="0"`, inactive
tabs have `tabindex="-1"`, and `activateTab` updates both `tabindex` and
`aria-selected`. The sidebar separator exposes its real pixel min/max/current
values through ARIA; do not mix percentage bounds with a pixel current value.

## How a mode extends the shell

A mode is a `SurfaceConfig` (see `surface.py`). It declares — not forks — its
chrome:

- `tabs` — ordered `TabConfig` list; the first tab renders active.
- `header_right` — ordered `HeaderCellConfig` list (meta, mode, language toggle…).
- `main_panels` / `sidebar_panels` — which partials fill the player zone and the
  right rail.
- `footer` — optional always-visible sidebar footer partial (review only).
- `modals`, `features`, `extra_styles`, `scripts`, i18n namespace, persistence
  mode, title prefix.

Adding a brand-new surface is config-only — proven by
`tests/test_shell_third_surface_config_only.py`, which renders a third demo
surface without touching `renderer.py` or any template.

## Adding a mode-specific tab or panel safely

1. Add a partial under `templates/partials/` whose top-level element is
   `<div id="tab-<id>" class="tab-content" role="tabpanel" tabindex="0">…</div>`
   and list it in the surface's `sidebar_panels` (or `main_panels`).
2. Add a `TabConfig("<id>", "<label_key>")` to the surface's `tabs`.
3. Add `<label_key>` to **every** i18n source the surface actually touches, en +
   pl. The project has **three** i18n stores, and a key must land in each one that
   renders the string:
   - `_SERVER_I18N[...]["<namespace>"]` in
     `screenscribe/shell/renderer.py` — server-side render of the shared shell
     chrome (tabs, header cells, language toggle).
   - `_I18N` (via `_t()`) in `screenscribe/html_pro/renderer.py` — server-side
     render of the review report body (findings, verdicts, section labels).
   - the matching namespace in `screenscribe/html_pro_assets/scripts/i18n.js` —
     the client runtime that resolves `data-i18n` anchors in the browser.

   Rule of thumb: **a new key goes into every source whose surface shows it, in
   both EN and PL (parity is mandatory).** Shell chrome → `shell/renderer.py`;
   report body → `html_pro/renderer.py`; anything the client re-renders live →
   `i18n.js`. The parity guard `tests/test_i18n_no_hardcoded_dom.py` fails on any
   key missing in either language.
4. Use `data-i18n="<key>"` anchors for any visible chrome — never hardcode
   user-facing text in markup or JS DOM writes.

## Export actions — the rule

**Artifact downloads live only in the final `Export` / `Eksport` tab.** They are
never always-visible footer/side buttons.

- **analyze**: `export_panel.html` is the last tab. Its download buttons start
  `disabled` and a gate hint (`export-gate-hint`) tells the user export unlocks
  after the first marked moment; the client enables them once artifacts exist.
- **review**: the `tab-export` panel in `review_sidebar.html` hosts the
  TODO / JSON / ZIP downloads. *Save review* (review-state persistence, not an
  artifact download) stays in the sidebar footer beside *Reset review*. Reset is
  a confirmed, server-backed return to the generated report: it removes the
  reviewer name, human verdicts, notes, manual merge overlays, manual moments,
  and review-created work items while preserving the generated findings and
  unrelated report data. Each reset advances a server-issued generation carried
  by review-state, cross-window snapshots, and manual-frame requests. A newer
  generation outranks snapshot timestamps, so delayed Add/Analyze work from
  before the reset cannot recreate cleared moments. Ordinary same-generation
  hydration preserves an annotation edit in progress; reset hydration discards
  that stale editor explicitly.

The review report's findings always exist, so its downloads are not readiness-
gated; analyze gates because its artifacts do not exist until the user marks a
moment.

> The `Statistics` / `Statystyki` tab was removed from the review UI. Severity
> counts remain available to export logic — only the user-facing tab and its
> stat-card markup were dropped.

## Review moment and merge contracts

`Moments (N)` counts logical moments represented in the current review: every
visible AI finding card, including rejected cards, plus every manual moment. A
human merge replaces N source cards with one logical card, so the count decreases
by `N - 1`; unmerge restores the source-card count. Rejection never changes the
count because the rejected card remains visible and auditable.

Human merges are reversible. The draft and saved survivor keep additive
`member_reviews` / `merged_member_reviews` snapshots of the source findings.
Unmerge keeps notes, priorities, and annotations edited on the survivor while it
was merged, but restores its pre-merge verdict because merge's automatic
`accepted` state is mechanics rather than a new reviewer decision. Other members
recover their pre-merge verdicts, priorities, notes, and annotations. Chaining a
merged survivor into an earlier finding snapshots that survivor's current review
state before it becomes an absorbed member, so intermediate edits survive the
eventual unmerge. Legacy saved merges without snapshots remain compatible: the
survivor keeps its state and absorbed members return as unreviewed.
