# Strava Running Coach — v2 Design Spec

This document describes the planned overhaul of the Strava Running Coach. The goal is a clean, standalone tool that any runner can set up in minutes and use daily from a terminal.

---

## Implementation Phases

### Phase 1 — Backend + Claude Skill (implement first)

Fix the foundation so the coach works well when used from Claude Code via the existing skill. Testable immediately without any new infrastructure.

1. **Memory overhaul** — replace fragile JSON session notes with `COACH_MEMORY.md` (section-level inline editing) + daily session logs
2. **Run context engine** — replace `get_training_report` with `get_run_context()` (server-rendered, age-tiered) + `get_run_detail()` (on-demand)
3. **Run digestion** — one-time LLM digest at ingest, incorporating athlete's Strava description; coach can annotate runs after the fact via `add_run_note()`
4. **Training plan format** — migrate JSON → YAML with ruamel.yaml; surgical editing tools instead of whole-file rewrites
5. **Update Claude skill** (`skills/running-coach/SKILL.md`) — reflect new tools and startup flow

**Done when:** the coach can be run from Claude Code via the skill and context usage is dramatically lower, with memory persisting correctly across sessions.

### Phase 2 — Plan Export + Repo Cleanup

Make the training plan useful outside the coaching session.

1. **Markdown table export** — `mcpacer export-plan [plan_id]` → `.md` file with week × day table
2. **Calendar export** — `mcpacer export-calendar [plan_id]` → `.ics` file for Google/Apple Calendar
3. **Repo cleanup** — README, `.gitignore`, remove OpenClaw-specific artifacts, `example.config.toml`

### Phase 3a — Terminal in a Browser

Minimum viable web app. Get Claude Code running in a dark-themed browser window.

1. **FastAPI skeleton** — PTY spawn for Claude Code, WebSocket bridge
2. **SvelteKit scaffold** — Tailwind dark theme, single-page layout
3. **xterm.js terminal** — full-screen, connected to backend via WebSocket
4. **`mcpacer` command** — starts backend + opens browser to `localhost:5173`
5. **Auto-run** — `/mcpacer` skill launches on connect

**Done when:** Full coaching session works in the browser. No panels yet — just a nice dark terminal.

### Phase 3b — Plan + Week Panels

Add the left sidebar with plan and week views.

1. **`/api/plan` endpoint** — reads plan YAML, returns structured JSON
2. **`/api/weeks` endpoint** — weekly volume (planned vs actual)
3. **PlanOverview component** — volume bars (gray=plan, colored=actual), click to select week
4. **WeekDetail component** — day-by-day list, completion status, copy-to-clipboard
5. **Layout split** — left panels + terminal on the bottom

**Done when:** Plan and weekly progress visible alongside coach chat. Clicking weeks updates detail panel.

### Phase 3c — Run Detail

Rich right panel with maps, charts, and lap data.

1. **`/api/runs/{id}` endpoint** — run detail + activity streams (latlng, HR, pace, altitude)
2. **RunDetail component** — Leaflet map (dark tiles, route polyline), summary stats, lap table, HR/pace chart
3. **Click-through** — completed run in WeekDetail → loads RunDetail on the right
4. **Four-panel layout** complete: plan overview, week detail, run detail, coach chat

**Done when:** Full layout working. Click plan → week → run with GPS map and charts.

### Phase 3d — Polish + Live Updates

1. **File watchers** — push plan/memory changes to frontend when coach modifies them mid-session
2. **Resizable dividers** — especially terminal height
3. **Route polyline** colored by pace or HR zones
4. **Elevation profile** chart
5. **Setup wizard** — Strava OAuth, LLM selection, config to `~/.mcpacer/`
6. **Onboarding flow** — first-run conversation, PR collection, initial `COACH_MEMORY.md` generation

---

## Problems with v1

1. **MCP-only interface** — requires Claude Desktop or Cursor as a host. Not standalone, not portable.
2. **Context flooding** — `get_training_report` dumps raw JSON for every run in 4 weeks, including full per-lap splits, into the LLM context. Expensive and largely noise.
3. **Fragile memory** — the coach relies on the LLM proactively calling `save_coaching_note` with correctly-formed JSON at session end. If the session ends abruptly or the LLM skips it, nothing is saved. Notes are stored as JSON blobs, which are harder to read back than prose. The separate `athlete_profile` and `plan_adjustments` stores were never actually used — all context ended up scattered across session notes.
4. **Training plans stored as JSON** — deeply nested, error-prone to edit by hand, LLMs tend to regenerate the whole file rather than make surgical edits. Plan adjustments were recorded in a separate log rather than in the plan itself, so the plan file diverged from reality.
5. **No clean setup flow** — requires manual `.env` configuration, no guided onboarding.
6. **Run data lacks athlete voice** — treadmill runs have notoriously inaccurate GPS paces, but the system had no way to incorporate the athlete's own description or post-hoc corrections. The coach had to rediscover context every session.

---

## Target UX

Three commands, ever:

```bash
uv sync
mcpacer setup   # one-time
mcpacer         # launches the TUI
```

After setup, `mcpacer` is all a user ever runs.

---

## Setup Flow (`mcpacer setup`)

An interactive wizard run once:

### Step 1 — Strava Auth
- Opens browser to Strava OAuth flow
- User approves, tokens stored to `~/.mcpacer/config.toml`
- Based on the existing `misc/get_strava_token.py` — promote to a proper CLI step

### Step 2 — LLM Selection
- Menu: `[1] Claude  [2] OpenAI  [3] Other`
- For Claude: opens browser to Anthropic Console for API key (mirrors Claude Code auth UX)
- For others: prompt for API key
- Stored in `~/.mcpacer/config.toml`
- Use **LiteLLM** as the unified interface so the rest of the codebase is model-agnostic

### Step 3 — Onboarding Conversation
- Automatically triggered on first `mcpacer` launch (detected by absence of `~/.mcpacer/COACH_MEMORY.md`)
- See Onboarding section below

Config lives in `~/.mcpacer/` (never in the repo). Repo ships `example.config.toml`.

---

## Web App

SvelteKit + Tailwind CSS (dark theme) frontend, FastAPI backend, with Claude Code embedded via xterm.js. Single command launches the server and opens the browser.

```bash
mcpacer        # starts backend, opens browser to localhost:5173
```

### Tech Stack

| Layer | Tech | Purpose |
|-------|------|---------|
| Frontend | SvelteKit + Tailwind CSS | Dark-themed UI with reactive panels |
| Terminal | xterm.js | Embedded Claude Code session |
| Maps | Leaflet + OpenStreetMap tiles | GPS track visualization |
| Charts | Chart.js or uPlot | HR, pace, elevation over time |
| Backend | FastAPI (Python) | Serves data, spawns PTY, WebSocket bridge |
| PTY bridge | WebSocket | Connects xterm.js ↔ Claude Code process |
| Data | File watchers | Push updates when coach modifies plan/memory |

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ ┌─ Plan Overview ──────────┐  ┌─ Run Detail ───────────────────┐│
│ │                          │  │                                ││
│ │ W6  ████████░░ 72/75km   │  │  ┌─ GPS Track (Leaflet) ────┐ ││
│ │ W7  ██████░░░░ 68/80km   │  │  │                           │ ││
│ │ W8→ ███░░░░░░░ 44/70km   │  │  │    route polyline on      │ ││
│ │ W9  ░░░░░░░░░░  0/60km   │  │  │    dark map tiles         │ ││
│ │                          │  │  │                           │ ││
│ │ [click a week ↓]        │  │  └───────────────────────────┘ ││
│ ├─ Week Detail ────────────┤  │                                ││
│ │ W8 Taper — 44/70km      │  │  Tue Mar 24 — 12.9km           ││
│ │                          │  │  4:20/km | HR 160/182 | +23m  ││
│ │ Mon  5.0km easy      ✓  │  │                                ││
│ │ Tue  12.9km workout  ✓← │  │  ┌─ Laps ──────────────────┐  ││
│ │ Wed  rest                │  │  │ WU  2.8km  4:44  HR 140 │  ││
│ │ Thu  8.1km easy      ✓  │  │  │ R1  1.0km  3:35  HR 168 │  ││
│ │ Fri  11.0km easy     ✓  │  │  │ R2  1.0km  3:38  HR 170 │  ││
│ │ Sat  6.8km easy      ✓  │  │  │ ...                      │  ││
│ │ Sun  22km dress          │  │  └──────────────────────────┘  ││
│ │              [Copy week] │  │                                ││
│ └──────────────────────────┘  │  ┌─ HR / Pace Chart ────────┐  ││
│                               │  │  ♥ ╱╲  ╱╲╱╲              │  ││
│                               │  │   ╱  ╲╱      ╲           │  ││
│                               │  └──────────────────────────┘  ││
│                               └────────────────────────────────┘│
│ ┌─ Coach Chat (xterm.js) ─────────────────────────────────────┐ │
│ │ David: That 6x1km at 3:39 in taper week... the hay is in   │ │
│ │ the barn. Stop setting the damn barn on fire.               │ │
│ │ > _                                                         │ │
│ └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Panels

**Plan Overview (top-left)**
- Volume bars for each week: gray = planned, colored = actual
- Current week marked with arrow indicator
- Click any week → loads it in Week Detail below
- Shows whole plan at a glance (scrollable for long plans)

**Week Detail (bottom-left)**
- Day-by-day breakdown for the selected week
- Plan prescription on the left, completion status on the right
- Completed runs are clickable → loads Run Detail on the right
- Planned but not-yet-completed runs show the prescription
- Copy-to-clipboard button: exports the week as a clean text table

**Run Detail (right panel)**
- Shown when a completed run is clicked in Week Detail
- **GPS map** — Leaflet with dark map tiles (CartoDB Dark Matter or Mapbox Dark), route as a colored polyline (color by pace or HR)
- **Summary stats** — distance, avg pace, avg/max HR, elevation, duration
- **Lap table** — per-lap breakdown with pace, HR, elevation
- **Charts** — HR and pace over distance/time, elevation profile
- Empty state when no run is selected: shows the plan week overview or a motivational quote from the coach

**Coach Chat (bottom strip)**
- xterm.js terminal running Claude Code
- Auto-launches `/mcpacer` on session start
- Resizable — can drag the divider up for more chat space
- Coach persona shown in the prompt/header area

### Architecture

```
Browser (localhost:5173)
├── SvelteKit app (dark Tailwind theme)
│   ├── PlanOverview.svelte    — volume bars, week selector
│   ├── WeekDetail.svelte      — run list, copy button
│   ├── RunDetail.svelte       — map, laps, charts
│   └── CoachChat.svelte       — xterm.js terminal component
│
│   WebSocket ──→ FastAPI backend (localhost:8000)
│                 ├── /ws/terminal     — PTY bridge for Claude Code
│                 ├── /api/plan        — current plan data (from YAML)
│                 ├── /api/weeks       — week summaries with volume
│                 ├── /api/runs/{id}   — run detail + streams
│                 └── /api/memory      — coach memory (for display)
│
│                 File watchers → push updates via WebSocket
│                 when plan/memory files change mid-session
```

The backend reads the same files the MCP tools use (plan YAML, run cache, coach memory). It does NOT duplicate the MCP server — it's a read-only view layer. All writes go through Claude Code → MCP server.

### Dark Theme

Tailwind dark theme throughout. Key design tokens:
- Background: `slate-900` / `slate-950`
- Cards/panels: `slate-800` with `slate-700` borders
- Text: `slate-100` primary, `slate-400` secondary
- Accent: a single brand color for volume bars, active states, route polyline (e.g. `emerald-400` or `sky-400`)
- Map tiles: CartoDB Dark Matter (free, no API key) or Mapbox Dark
- Terminal: matches the dark theme naturally (xterm.js dark config)

### Startup Sequence

1. `mcpacer` command starts FastAPI backend
2. Backend spawns Claude Code in a PTY
3. Opens browser to `localhost:5173`
4. Frontend connects WebSocket to backend (terminal + data updates)
5. Claude Code auto-runs `/mcpacer` skill
6. Panels populate from backend API (plan, weeks, runs)
7. File watchers detect changes from the coaching session and push updates

Each session is **fresh** (no conversation history carried over). Memory files provide continuity.

---

## Onboarding (First Run Only)

Detected by absence of `~/.mcpacer/COACH_MEMORY.md`.

### Data fetched automatically (before first message):
- Last 4 weeks of activity summaries — for volume trend and recent context (~20 API calls)
- **No PR scanning** — see below

### Coach asks:

**1. Current PRs (self-reported)**
> *"To calibrate your training paces, what are your current estimated PRs? Approximate is fine — I just need a sense of where you're at.*
> *— 5k*
> *— 10k*
> *— Half marathon*
> *— Marathon (if applicable)"*

Then: *"Are those from recent races, or has your fitness changed significantly since then?"*

This approach is preferred over scanning Strava activity history for `best_efforts` because:
- Strava API budget is limited (~1000 requests/day, design conservatively around 200)
- Scanning 200 activities for PRs would consume the daily budget on a single onboarding
- Self-reported PRs better reflect current fitness (old Strava PRs may be years stale)
- The follow-up question surfaces fitness changes that raw data can't

**2. Goals & current phase**
- Base building / race prep / recovery post-race / off-season?
- Target race: distance, date, goal time (if applicable)

**3. Constraints**
- Training days per week
- Any active injuries or niggles

**4. Anything else**
- Open field for the athlete to share anything the coach should know

### At end of onboarding:
Coach writes initial `~/.mcpacer/COACH_MEMORY.md`. This becomes the permanent foundation for all future sessions.

---

## Memory Architecture

All memory lives in `~/.mcpacer/` (user's home, not the repo).

### `COACH_MEMORY.md` — Long-term memory

The coach's curated knowledge about the athlete. **LLM-written and LLM-maintained** via section-level inline editing tools. Read in full on every session start.

```markdown
## Athlete
- Name: [name], [location]
- Weight: [kg]

## PRs (self-reported, [date assessed])
- 5k: [time]
- 10k: [time]
- Half: [time]
- Marathon: [time]
- Notes: [e.g. "5k PR is from 2023, current fitness is ~30s slower"]

## Goals
- [Target race, date, goal time]
- Current phase: [base building / race prep / recovery / off-season]

## Active Flags
- [e.g. "Left knee lateral twinge on long runs >28km — first noted YYYY-MM-DD"]

## Training Context
- Current weekly volume: ~[X]km/week
- Agreed volume cap: [X]km/week
- Training days: [days]
- Schedule constraints: [any]

## Patterns & Insights
- [Observations the coach has made, e.g. "tends to go out too fast on tempos"]
```

**What goes here:** what is true *now*. Current state, not event history.

**When to update:** when significant new information emerges mid-session — new injury, goal change, notable pattern. The coach calls the section-level update tool inline, not at session end. This means memory updates happen the moment something important is said, not deferred.

#### Memory Tools

**`read_coach_memory()`** — returns the full `COACH_MEMORY.md` content. Available on demand (also loaded into system prompt at session start).

**`update_coach_memory(section, content)`** — rewrites a specific section in-place. The `section` parameter maps to the `## ` headers: `athlete`, `prs`, `goals`, `active_flags`, `training_context`, `patterns`. The tool finds the matching `## ` header, replaces everything up to the next `## ` (or EOF), and writes the file. If the section doesn't exist, it appends a new section.

No whole-file rewrite tool. If the coach needs to update multiple sections, it calls `update_coach_memory` once per section. This keeps changes auditable — each tool call shows exactly what changed and why.

Example:
```
Coach notices athlete mentions a new knee issue →
  update_coach_memory("active_flags",
    "- Groin pull from gym — first noted 2026-03-19, improving\n- Left knee twinge on long runs >28km — first noted 2026-03-23")
```

### `memory/YYYY-MM-DD.md` — Daily session logs

Auto-written by the TUI at session end (not LLM-dependent — the TUI writes it regardless). One file per session day.

```markdown
## Session [date] — Coach [name]
- [What was discussed]
- [Any flags raised]
- [Decisions made]
- [Adjustments to plan]
```

The TUI asks the coach to produce a 3–5 line session summary at the end of each conversation, then writes it to this file automatically. The coach cannot "forget" to save — the save is triggered by the TUI, not the LLM.

**What goes here:** what happened *when*. Event history, not current state.

**Boundary with COACH_MEMORY.md:** the session log records "discussed groin pain, decided to skip Wednesday workout." The coach memory records "groin pull — first noted 2026-03-19, improving." If a fact matters beyond its session, it belongs in COACH_MEMORY.md. Session logs are raw notes for recent context only.

**How many get loaded:** all session logs since the last session, capped at 5. This handles both daily users (1 log) and someone returning after a week off (5 logs covering the gap). For a Phase 1 Claude Skill session (no TUI), the skill reads the most recent 3 session log files from `memory/`.

---

## Run Context Engine

### The problem

v1 dumped raw JSON for every run in 4 weeks including full lap splits. This flooded the context with noise. But the coach genuinely needs a complete picture of the training block — you can't coach a marathon build from the last 3 runs.

### Solution: `get_run_context()`

A single MCP tool that builds a **server-rendered, age-tiered text snapshot** of the athlete's training. No JSON. No arrays of objects. A pre-formatted text block ready for the LLM to read immediately.

The server does all orchestration internally:
1. Syncs any new activities from Strava (1 API call per new run + 1 laps call if digestion needed)
2. Renders the tiered output based on date ranges

`get_run_context()` is purely actual run data — no plan awareness. The plan context is loaded separately via `get_plan_context()` (see below). The coach sees both blocks and makes the comparison itself, which allows nuanced interpretation ("did 10×1km instead of 5×1km — ambitious but HR looked fine") rather than a mechanical pass/fail.

#### Tiering Rules

| Age | Format | Detail level |
|-----|--------|--------------|
| **Older weeks** (>2 weeks ago, or pre-plan) | One-liner per week | Total km, run count, key sessions (long run + workout), pass/fail |
| **Recent weeks** (current + previous 1–2) | One line per run | Compact format with digest line for workouts/long runs |

Weeks older than 12 weeks or before the plan start date are omitted entirely.

#### Output format

```
=== TRAINING OVERVIEW ===

Weeks 1–6 (Feb 2 – Mar 15):
W1  Feb 2   75km | 5 runs | Long 27km | Workout: 5×1600m @4:00 ✓
W2  Feb 9   83km | 5 runs | Long 30km | Workout: 6×1200m @3:55 ✓
W3  Feb 16  88km | 5 runs | Long 28km | Workout: 3×4km @4:03 ✓
W4  Feb 23  65km | 4 runs | Long 28km (easy, deload) | ⚠ Deload — bad weather
W5  Mar 2   95km | 5 runs | Long 34km w/16km MP | Workout: 8×800m @3:40 ✓
W6  Mar 9   72km | 4 runs | Long 32km | Tempo 10km @4:10 ✓

=== RECENT DETAIL ===

Week 7 — Mar 16–22
  Mon Mar 16 🟢 Easy 5.0km 0:27m | 5:24/km | HR 128/142 | #17750001
  Tue Mar 17 🟢 Easy 11.9km 1:03m | 5:19/km | HR 130/148 | #17760002
       → Best paced easy run in weeks. Controlled throughout.
  Wed Mar 18 — rest (groin recovery)
  Thu Mar 19 🔴 Workout 12.0km 0:48m | 4:01/km | HR 158/182 | #17770003
       → 10×1km @~3:45/km (treadmill, GPS pace unreliable). Felt manageable.
       📝 Athlete did 10×1km instead of prescribed 5×1km — double volume on taper week
  Fri Mar 20 🟢 Easy 4.5km 0:24m | 5:20/km | HR 132/145 | #17780004

Week 8 — Mar 23–29 (current)
  (no runs yet)

For detail on any run: get_run_detail(activity_id)
```

**Key properties:**
- The entire output is a single string, rendered server-side — the LLM reads it like a document, not structured data
- Activity IDs are inline (`#17770003`) so the coach can drill into any run on demand
- The `📝` lines are coach notes added via `add_run_note()` — they persist across sessions
- The `→` digest lines are generated once at ingest time (see Run Digestion)
- Weekly one-liners are computed on the fly from the run cache — no separate compaction store needed

### `get_plan_context()`

Returns the active training plan rendered as compact text. If no active plan exists, returns `"No active training plan."` — the coach works fine without one (off-season, casual running, etc.).

The plan is small enough to load in full. A 16-week plan at one line per week is ~1,600–2,000 chars — trivially fits in context.

#### Output format

```
=== ACTIVE PLAN: Sub-3 Marathon Build ===
Race: Marathon — Apr 4, 2026 — Goal 2:59:59 (4:15/km)
Status: Week 8 of 9 (taper)

W1  Feb 2   75km  Base building
    Mon 10km easy | Tue 12km easy | Wed 2km WU, 5×1600m @4:00 w/400m jog rec, 2km CD | Thu 💪 Gym 60min | Fri 8km recovery | Sun 27km easy
W2  Feb 9   83km  Building volume
    Mon 8km recovery | Tue 12km easy | Wed 2km WU, 6×1200m @3:55 w/400m jog rec, 2km CD | Thu 💪 Gym 60min | Fri 10km easy | Sun 30km easy
W3  Feb 16  88km  Intro MP work
    Mon 8km recovery | Tue 12km easy | Wed 2km WU, 3×4km @4:03 w/3min jog rec, 2km CD | Thu 💪 Gym 60min | Fri 10km easy | Sun 28km w/10km MP
W4  Feb 23  65km  # Deload — bad weather
    Mon 8km recovery | Tue 10km easy | Wed treadmill workout | Fri 8km easy | Sun 28km easy
W5  Mar 2   95km  Peak week
    Mon 10km easy | Tue 12km easy | Wed 2km WU, 8×800m @3:40 w/90s standing rec, 2km CD | Thu 6km AM + 6km PM recovery | Fri 10km easy | Sun 34km w/16km MP
W6  Mar 9   72km  Recovery week
    Mon 8km recovery | Wed tempo 10km @4:10 | Thu 💪 Gym 60min | Fri 8km easy | Sun 32km easy
W7  Mar 16  80km  Final quality
    Mon 10km easy | Tue 12km easy | Wed 2km WU, 5×1km @3:50 w/400m jog rec, 2km CD | Thu 8km recovery | Fri 6km easy | Sun 28km @5:00
→ W8  Mar 23  70km  Taper  ← CURRENT
    Mon 8km recovery | Tue 10km easy | Wed 2km WU, 4×1km @3:55 w/400m jog rec, 2km CD | Fri 6km easy | Sat 24km easy
W9  Mar 30  60km  Race week
    Mon 6km easy | Wed 4km shakeout | Fri 3km shakeout | Sat RACE Apr 4

For full plan YAML: get_training_plan("sub3-marathon-apr2026")
```

Each week gets two lines: a header with total volume and weekly focus, then the day-by-day prescription. Every run is listed with its day, distance, and type (easy, recovery, shakeout, etc.). Workouts include the full structure with rest type and duration between intervals (e.g. `w/400m jog rec`, `w/90s standing rec`). Long runs show distance and intent (easy, MP blocks, etc.). Non-running days (gym, rest) are included where prescribed.

The `→` marker and `← CURRENT` label highlight the active week. YAML comments from `add_plan_comment()` are rendered inline on the header line (e.g. `# Deload — bad weather`).

A 16-week plan at two lines per week is ~3,000–4,000 chars — still very manageable in context.

The coach can call `get_training_plan(plan_id)` for the full YAML if it needs to inspect or edit individual workouts.

### `get_run_detail(activity_id)`

On-demand deep dive into a single run. Returns full lap splits, HR zones, elevation profile, and any coach notes. Used for post-race analysis, anomalies, or when the athlete asks about specific splits. Costs 0–1 Strava API calls (0 if data is already cached with laps).

---

## Run Digestion

The problem: for structured workouts and long runs, average pace and HR tell the coach almost nothing. But full lap splits and streams are too large to include in every session context.

### Solution: one-time hybrid digestion at ingest time

When a new run is stored, if it qualifies for digestion, laps are fetched (1 API call) and compiled into a compact lap table. This table — along with the **athlete's Strava description** — is sent to a small, cheap LLM (e.g. Claude Haiku, GPT-4o-mini). The resulting digest is stored permanently in the run JSON. Cost paid once at ingest, zero cost per session.

### Run data model (stored in `run_*.json`)

Each run has two annotation fields beyond the raw Strava data:

```json
{
  "run_digest": "10×1km @~3:45/km (treadmill, GPS pace unreliable). HR 158→172.",
  "coach_notes": [
    "Athlete did 10×1km instead of prescribed 5×1km — double volume on taper week"
  ]
}
```

**`run_digest`** — generated once at ingest by the digestion LLM. Immutable after creation.

**`coach_notes`** — a list that grows over time as the coach annotates runs during conversation. Added via `add_run_note(activity_id, note)`.

### Digestion input: athlete description is authoritative

The digestion LLM receives both the compact lap table AND the athlete's Strava activity description (the free-text field they write on the app). The prompt treats the athlete's description as ground truth:

```
Summarize this workout structure from the lap data below.

IMPORTANT: The athlete's description is authoritative. If they mention treadmill,
treat GPS pace data as approximate and prefer any paces they state. If the
description contradicts lap data, prefer the description.

Activity name: "10x1km treadmill"
Athlete description: "10x1km on treadmill, ~3:45 pace, felt smooth. Groin OK."

Laps (dist, pace, HR, elev gain):
1: 1.01km  4:12/km  HR 158  +0m
2: 0.98km  4:08/km  HR 162  +0m
3: 1.02km  4:15/km  HR 160  +0m
...
```

Output: `10×1km @~3:45/km (treadmill, GPS pace unreliable). HR 158→172. Groin OK.`

Without the description, the digester would report ~4:12/km from GPS — completely wrong for treadmill. The athlete's stated ~3:45 is what matters.

**If no description is provided,** the digester works from lap data alone (same as before). The description is an optional but high-value signal.

### `add_run_note(activity_id, note)`

MCP tool that appends a note to the run's `coach_notes` array in the cached JSON. The coach calls this during conversation when the athlete says something that changes interpretation of a run.

Example flow:
> Athlete: "That Thursday run, my watch was glitching for the first 2km, ignore those splits"
> Coach calls: `add_run_note(17770003, "Watch GPS glitch first 2km — ignore those splits")`

Coach notes are always rendered when that run appears in context (via `get_run_context()` or `get_run_detail()`), prefixed with `📝`. They persist across sessions — the next time any coach sees this run, the note is there.

### Why not pure rule-based digestion

Real-world lap data is too messy. Athletes mix auto-lap (1km) with manual lap presses; Strava does not expose which is which. Progression runs look nothing like intervals or tempo. Elevation changes make pace interpretation misleading without context. Treadmill GPS is garbage. A small LLM handles all these cases naturally — especially when the athlete's own description provides the missing context.

### Why not raw data digestion

Sending full streams (1 data point/second) or hundreds of lap fields is expensive and noisy. The compact lap table — distance, pace, HR, elevation per lap — is typically 50–150 tokens. The athlete description adds another 10–50 tokens. Cheap, fast, sufficient.

### LLM output format — structured segments

Interval workout:
```
WU 5km @5:00/km HR 140 | 12×400m @3:38/km HR 165→185 rec 90s | CD 5km @5:00/km HR 138 | +110m
```

Tempo:
```
WU 2km @5:30/km HR 132 | Tempo 20min @4:08/km HR 162→171 | CD 2km @5:30/km HR 138 | +45m
```

Progression run:
```
Progression 16km @5:20→4:35/km HR 138→162 | +85m
```

Long run with fade:
```
0–28km @4:53/km HR 142→155 | 28–35km @5:20/km HR 155→162 (fade) | +180m
```

Easy run: **no digestion** — the one-liner is sufficient.

**Elevation** is included as total gain at the end of the digest. For hilly runs this gives the coach essential context for interpreting pace without needing per-segment breakdown.

### Classification (to decide whether to fetch laps and digest)

- Activity name contains "interval", "tempo", "track", "workout", "progression" → digest
- HR variability (std dev) above threshold → likely structured, digest
- Distance > 25km → long run, digest
- Otherwise → easy run, skip

---

## API Budget

Strava rate limit: 100 requests/15 min, 1000 requests/day. Design conservatively around 200/day to leave headroom.

| Operation | Calls |
|---|---|
| Onboarding activity fetch (4 weeks) | ~20 |
| Session startup sync (per new activity) | 1 summary + 1 laps (if digested) per run |
| On-demand run detail | 1 per activity |
| Streams | Never automatically; only if coach explicitly requests |
| **Typical daily total** | **~5–15** |

---

## Training Plan Format

Switch from JSON to **YAML**. Same structure, same parsing logic, but:
- Human-readable without a JSON formatter
- Supports inline comments (`# Recovery week — cut volume ~20%`)
- LLMs make surgical edits via dedicated tools without regenerating the whole file
- No trailing comma / bracket mismatch errors
- Plan adjustments are documented *in the plan itself* as comments, not in a separate log

Workout dates are **derived at read time** from `week_start_date + offset(day_of_week)` rather than stored per-workout. This means moving a training block only requires updating `week_start_date`, not editing 112 individual date fields.

```yaml
plan_name: Boston 2027 Marathon Plan
goal_race:
  date: 2027-04-19
  race_type: marathon
  distance_km: 42.195
  goal_time: "3:05:00"
  goal_pace_min_per_km: "4:22"
  race_name: Boston Marathon

plan_start_date: 2027-01-06
notes: 16-week build. Focus on threshold volume and long run progression.

weeks:
  - week_number: 1
    week_start_date: 2027-01-06
    total_planned_distance_km: 65
    weekly_focus: Base building  # Establish aerobic base, keep HR controlled
    runs:
      - day_of_week: Monday
        type: easy
        distance_km: 10
        target_pace_min_per_km: "5:30"
        description: Recovery run

      - day_of_week: Tuesday
        type: workout
        distance_km: 12
        target_pace_min_per_km: "4:15"
        structure: 2km WU, 5×1600m @4:00 w/400m jog rec, 2km CD
        description: Threshold intervals

      - day_of_week: Thursday
        type: gym
        duration_minutes: 60
        description: Lower body, core

      - day_of_week: Saturday
        type: long_run
        distance_km: 20
        target_pace_min_per_km: "5:00"
        description: Steady long run

      - day_of_week: Sunday
        type: cross_training
        duration_minutes: 45
        description: Cycling or swimming — active recovery
```

Use **ruamel.yaml** (not PyYAML) so that round-trip edits preserve comments and formatting.

### Training Plan Tools

No whole-plan rewrite tool. All modifications are surgical:

**`get_training_plan(plan_id)`** — returns the YAML content as-is (human-readable).

**`list_training_plans()`** — lists available plans with basic metadata (name, race date, status).

**`update_plan_run(plan_id, week_number, day_of_week, updates)`** — modifies a single workout within a week. `updates` is a dict of fields to change. The tool loads the YAML via `ruamel.yaml`, finds the matching week + day, patches only the specified fields, and writes back preserving all comments and formatting.

Example: `update_plan_run("boston-2027", 4, "Sunday", {type: "easy", distance_km: 28, description: "Easy long run — deload week, no MP block"})`

**`update_plan_week(plan_id, week_number, updates)`** — updates week-level metadata (`weekly_focus`, `total_planned_distance_km`).

**`add_plan_run(plan_id, week_number, run)`** — adds a new workout to a week.

**`remove_plan_run(plan_id, week_number, day_of_week)`** — removes a workout from a week.

**`add_plan_comment(plan_id, week_number, comment)`** — appends a YAML comment to the week block (e.g. `# Deload week — groin recovery, cut volume 30%`). This is how adjustments get documented *in the plan itself* rather than in a separate adjustments log. The comment persists through all future reads and exports.

**`analyze_plan_adherence(plan_id)`** — compares planned vs actual workouts using the run cache. Returns a compact summary of what was hit, missed, or modified.

**Why no whole-file rewrite:** LLMs tend to regenerate entire plan files when given the chance, introducing subtle errors (wrong dates, dropped workouts, lost comments). Surgical tools force targeted changes that show up clearly in diffs and preserve everything the LLM didn't touch.

**Migration:** one-time script converts existing `plan_*.json` → `plan_*.yaml`.

---

## Training Plan Export

### Markdown Table (Phase 1 — implement first)

`mcpacer export-plan [plan_id]` generates a `.md` file with a week × day table. Renders well in GitHub, VS Code, Obsidian, or any markdown viewer.

**Layout:** rows = weeks, columns = Mon–Sun + summary. Week column contains number and focus theme.

**Cell format (single line, compact):**

| Type | Format |
|------|--------|
| Easy run | `Jan 27 🟢 Easy 10km` |
| Workout | `Jan 28 🔴 Workout 12km · 5×1600m @4:00` |
| Long run | `Feb 1 🔵 Long 20km · 5:00/km` |
| Gym | `Jan 30 💪 Gym 60min` |
| Cross training | `Feb 2 🔄 XT 45min` |
| Rest | `Jan 27 💤 Rest` |
| Tuneup race | `Mar 8 🏁 Half-Marathon` |

For workouts, include the full key structure (e.g. `5×1600m @4:00 w/90s rec`) and target pace. The table is the primary human-readable artifact for the plan, so cells should contain all relevant details — not truncated. Warmup/cooldown can be abbreviated (`2km WU/CD`) but the main set should be complete.

**Summary column (rightmost):** total running km for the week + quality km (workouts + long run combined) + weekly focus label.

Example:
```
**65km** · quality 32km · Base building
```

**Example rendered row:**

| Week | Mon | Tue | Wed | Thu | Fri | Sat | Sun | Summary |
|------|-----|-----|-----|-----|-----|-----|-----|---------|
| **W1** Base building | Jan 27 🟢 Easy 10km | Jan 28 🔴 Workout 12km · 5×1600m @4:00 | Jan 29 🟢 Easy 8km | Jan 30 💪 Gym 60min | Jan 31 🟢 Easy 10km | Feb 1 🔵 Long 20km | Feb 2 🔄 XT 45min | **65km** · quality 32km |

The export is generated from the YAML plan at any time — re-run after edits to get an updated table. Output path defaults to `training_plan_[plan_id].md` in the current directory.

---

## Calendar Export

Training plan → calendar in two phases:

**Phase 1 (implement first): ICS export**
- `mcpacer export-calendar [plan_id]` generates a `.ics` file
- User imports into Google Calendar / Apple Calendar / anything
- Zero infrastructure, works everywhere
- Limitation: static — re-export and re-import after plan edits

**Phase 2 (later): Google Calendar API**
- Write workouts directly to a dedicated "Training Plan" calendar
- Events update when the plan changes
- Requires one-time OAuth setup (same pattern as Strava auth in setup wizard)
- Worth it if plan editing mid-block becomes common

---

## Session Startup Flow

Whether running from the TUI or the Claude Skill, every session follows the same sequence:

```
1. Load persona
2. Call read_coach_memory()   → long-term athlete knowledge
3. Call get_run_context()     → syncs new runs, returns tiered training snapshot
4. Call get_plan_context()    → returns active plan as compact text (or "no plan")
5. Call get_session_logs()    → recent session summaries for conversation continuity
6. Coach opens conversation with full context
```

In the **TUI**, steps 1–5 are automated before the first message. In the **Claude Skill**, the skill prescribes these as the first tool calls.

The output of steps 2–5 forms the complete coaching context — everything the coach needs to have the full picture without being flooded with raw data. Run data and plan data are loaded independently so either can exist without the other.

---

## MCP Tool Summary

### Memory Tools
| Tool | Purpose |
|------|---------|
| `read_coach_memory()` | Returns full COACH_MEMORY.md content |
| `update_coach_memory(section, content)` | Rewrites a specific section inline |
| `get_session_logs(limit=3)` | Returns the most recent N daily session logs as concatenated text |

### Run Tools
| Tool | Purpose |
|------|---------|
| `get_run_context()` | Server-rendered tiered training snapshot (the main context tool) |
| `get_run_detail(activity_id)` | Full detail on a single run (on-demand) |
| `add_run_note(activity_id, note)` | Annotate a run with coach/athlete context |

### Strava API Tools (raw access)
| Tool | Purpose |
|------|---------|
| `get_activities(limit)` | Fetch recent activities from Strava (raw) |
| `get_activities_by_date_range(start, end)` | Fetch activities in a date range (raw) |
| `get_activity_by_id(activity_id)` | Full raw activity data including streams/laps |
| `get_recent_activities(days)` | Activities from the last N days (raw) |

These are the existing v1 Strava tools, kept as-is. They return raw Strava API data and are **not** the primary context-loading path — `get_run_context()` handles that. Use these for edge cases: debugging sync issues, looking up non-running activities, or when the coach needs raw data that the tiered context doesn't surface.

### Training Plan Tools
| Tool | Purpose |
|------|---------|
| `get_plan_context()` | Server-rendered compact plan snapshot (the main plan context tool) |
| `get_training_plan(plan_id)` | Returns full YAML plan content (for inspection/editing) |
| `list_training_plans()` | Lists available plans |
| `update_plan_run(plan_id, week, day, updates)` | Modify a single workout |
| `update_plan_week(plan_id, week, updates)` | Modify week-level metadata |
| `add_plan_run(plan_id, week, run)` | Add a workout to a week |
| `remove_plan_run(plan_id, week, day)` | Remove a workout |
| `add_plan_comment(plan_id, week, comment)` | Add YAML comment to a week |
| `analyze_plan_adherence(plan_id)` | Compare planned vs actual |

### Coaching Tools
| Tool | Purpose |
|------|---------|
| `get_coaching_personas()` | List available coach personas |
| `add_coaching_feedback(activity_id, feedback)` | Post feedback to Strava activity description |

### Session Tools (TUI only)
| Tool | Purpose |
|------|---------|
| `save_session_log(date, content)` | Write daily session log (called by TUI, not LLM) |

---

## TUI Architecture (Phase 2)

### Overview

The TUI is a standalone Python process that acts as an **MCP client** — it spawns the existing MCP server as a subprocess and drives it via the stdio transport. The server code does not change. The TUI gets the full tool suite automatically.

```
mcpacer (entry point)
       │
  Agent loop
       ├── LLM client (LiteLLM — model agnostic, configured in ~/.mcpacer/config.toml)
       └── MCP client (mcp.client.stdio)
                │  spawns as subprocess, stdio transport
                ▼
    mcpacer-server MCP server (existing code, unchanged)
            ├── memory tools
            ├── run tools
            ├── training plan tools
            └── coaching tools
```

### Agent Loop

```python
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        tools = await session.list_tools()
        # convert MCP tool specs → LiteLLM tool format
        # build system prompt: persona + COACH_MEMORY + run context + session logs
        # run streaming LLM loop:
        #   LLM responds → stream to terminal via Rich
        #   LLM calls tool → execute via MCP session → return result → continue
```

### Rendering

**Rich** for output rendering:
- LLM text streams in as generated
- Tool calls shown as dim inline annotations: `[fetching recent runs...]`
- No windowed layout — scrolling terminal output, same aesthetic as Claude Code

**prompt_toolkit** for input:
- Bottom-of-screen input with readline history
- `/exit`, `/memory`, `/plan` slash commands

### Startup Sequence

```
$ mcpacer
  Select coach: [1] Coach  [2] David  [3] Roland  [4] Kim  [5] Hartmann
  > 3

  Syncing activities... 2 new runs since Mar 14.

  Coach Roland: Hey Pete. Big week — 35km long run on Sunday, HR
  looked solid through 30km. What are we working on today?
  >
```

### Session Close

When the user exits (`/exit` or Ctrl+C):
1. TUI sends a final message to the LLM: *"Session ending. Write a 3–5 line summary of what was discussed."*
2. LLM responds with summary
3. TUI writes summary to `~/.mcpacer/memory/YYYY-MM-DD.md` automatically — not LLM-dependent

### Config (`~/.mcpacer/config.toml`)

```toml
[strava]
client_id = "..."
client_secret = "..."
refresh_token = "..."

[llm]
provider = "anthropic"   # or "openai", "ollama", etc.
model = "claude-sonnet-4-5"
api_key = "..."
```

---

## Repo Cleanup (Pre-Release Checklist)

- [ ] All secrets in `~/.mcpacer/config.toml`, `.env` removed from repo patterns
- [ ] `run_data/`, `training_plans/`, `coaching_data/athlete_profile_*.json`, `coaching_data/session_notes_*.json` in `.gitignore`
- [ ] `skills/running-coach/SKILL.md` — remove or move to `docs/` with a note that it's for OpenClaw users
- [ ] README rewritten: covers setup, daily use, LLM configuration
- [ ] `example.config.toml` ships in repo
- [ ] `misc/get_strava_token.py` promoted into `mcpacer setup` wizard, old script removed
- [ ] License verified ✓

---

## MCP Server

Keep it. Users running Claude Desktop or other MCP hosts can still use the server directly. But it's no longer the primary interface — the TUI is. The MCP server and TUI share the same underlying storage, tools, and memory files.

---

## What Stays the Same

- Coaching persona system (`coaching_data/personas/`) — solid, no changes
- `add_coaching_feedback` tool (posts to Strava activity descriptions) — keep
- Raw Strava API tools (`get_activities`, `get_activities_by_date_range`, `get_activity_by_id`, `get_recent_activities`) — keep for edge cases and raw data access
- Local run caching pattern (`RunStorage`) — keep, just change what gets reported from it
- Strava client (`strava_client.py`) — keep, unchanged
- `pyproject.toml` / `uv` toolchain — keep

---

## Code Cleanup

This is a rewrite, not a patch. Old code that is replaced by v2 should be **deleted, not left around**. Specifically:

- **`get_training_report`** — replaced by `get_run_context()`. Delete the tool and its report-generation logic entirely.
- **`save_coaching_note` / `get_session_notes`** — replaced by `COACH_MEMORY.md` + daily session logs. Delete the JSON session notes system.
- **`update_athlete_profile` / `get_athlete_profile`** — never worked in practice, replaced by `COACH_MEMORY.md`. Delete the athlete profile JSON system.
- **`plan_adjustments` storage** — never used, replaced by YAML comments in the plan itself. Delete.
- **`save_training_plan` (whole-file write)** — replaced by surgical YAML editing tools. Delete.
- **`get_coaching_context` (v1 monolith loader)** — replaced by the separate startup flow (`read_coach_memory` + `get_run_context` + `get_plan_context` + session logs). Delete.
- **JSON training plan storage** — replaced by YAML. Delete `TrainingPlanStorage` JSON logic, keep only YAML read/write.
- **`CoachingStorage` class** — most of it is obsolete (session notes, athlete profile, plan adjustments). Gut it down to just persona loading, or inline that into the coaching tools directly.
- **CLI commands** (`mcpacer-generate-report`, `mcpacer-analyze-plan`, `mcpacer-generate-calendar`) — evaluate which are still needed after v2 tools exist. Don't keep dead entry points.

The goal is a clean codebase where every file and function earns its place. If something is replaced by a v2 equivalent, the old version goes away — no compatibility shims, no "legacy" modules, no dead code behind flags.
