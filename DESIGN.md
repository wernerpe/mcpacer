# Strava Running Coach — v2 Design Spec

This document describes the planned overhaul of the Strava Running Coach. The goal is a clean, standalone tool that any runner can set up in minutes and use daily from a terminal.

---

## Problems with v1

1. **MCP-only interface** — requires Claude Desktop or Cursor as a host. Not standalone, not portable.
2. **Context flooding** — `get_training_report` dumps raw JSON for every run in 4 weeks, including full per-lap splits, into the LLM context. Expensive and largely noise.
3. **Fragile memory** — the coach relies on the LLM proactively calling `save_coaching_note` with correctly-formed JSON at session end. If the session ends abruptly or the LLM skips it, nothing is saved. Notes are stored as JSON blobs, which are harder to read back than prose.
4. **Training plans stored as JSON** — deeply nested, error-prone to edit by hand, LLMs tend to regenerate the whole file rather than make surgical edits.
5. **No clean setup flow** — requires manual `.env` configuration, no guided onboarding.

---

## Target UX

Three commands, ever:

```bash
uv sync
strava-coach setup   # one-time
strava-coach         # launches the TUI
```

After setup, `strava-coach` is all a user ever runs.

---

## Setup Flow (`strava-coach setup`)

An interactive wizard run once:

### Step 1 — Strava Auth
- Opens browser to Strava OAuth flow
- User approves, tokens stored to `~/.strava-coach/config.toml`
- Based on the existing `misc/get_strava_token.py` — promote to a proper CLI step

### Step 2 — LLM Selection
- Menu: `[1] Claude  [2] OpenAI  [3] Other`
- For Claude: opens browser to Anthropic Console for API key (mirrors Claude Code auth UX)
- For others: prompt for API key
- Stored in `~/.strava-coach/config.toml`
- Use **LiteLLM** as the unified interface so the rest of the codebase is model-agnostic

### Step 3 — Onboarding Conversation
- Automatically triggered on first `strava-coach` launch (detected by absence of `~/.strava-coach/COACH_MEMORY.md`)
- See Onboarding section below

Config lives in `~/.strava-coach/` (never in the repo). Repo ships `example.config.toml`.

---

## TUI

Built with **Textual** (Python TUI framework). Layout:

```
┌─────────────────────────────────────────────────┐
│  🏃 Running Coach — Coach Roland                │
├─────────────────────────────────────────────────┤
│                                                  │
│  Coach: Hey Pete. Solid week — 35km long run    │
│  yesterday, HR controlled through 30km. Left    │
│  knee worth watching. What's on your mind?      │
│                                                  │
│  Pete: Thinking about adding a second tempo...  │
│                                                  │
├─────────────────────────────────────────────────┤
│  > _                                            │
└─────────────────────────────────────────────────┘
```

- Scrollable chat history pane
- Persistent input box at bottom
- Coach name shown in header (updates on persona selection)

### Startup Sequence (Every Session)

1. **Sync new activities** — fetch activities since last session, store locally (compact format, no streams)
2. **Select persona** — small menu presented before chat opens:
   ```
   Select coach: [1] Coach (default)  [2] David  [3] Roland  [4] Kim  [5] Hartmann
   ```
3. **Build context** (loaded into system prompt, not shown to user):
   - `COACH_MEMORY.md`
   - Compact digest of activities since last session
   - Last 2 daily session logs
4. **Coach opens** with a brief acknowledgment of what happened since last session, then hands it to the user

Each session is **fresh** (no conversation history carried over). Memory files provide continuity.

---

## Onboarding (First Run Only)

Detected by absence of `~/.strava-coach/COACH_MEMORY.md`.

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
Coach writes initial `~/.strava-coach/COACH_MEMORY.md`. This becomes the permanent foundation for all future sessions.

---

## Memory Architecture

All memory lives in `~/.strava-coach/` (user's home, not the repo).

### `COACH_MEMORY.md` — Long-term memory

The coach's curated knowledge about the athlete. LLM-written and LLM-maintained. Read on every session start.

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

Coach should update this file when significant new information emerges (new injury flag, goal change, notable pattern identified). Update is done inline — rewrite the relevant section, not append.

### `memory/YYYY-MM-DD.md` — Daily session logs

Auto-written by the TUI at session end (not LLM-dependent — the TUI writes it regardless). One file per session day. Raw notes for recent context.

```markdown
## Session [date] — Coach [name]
- [What was discussed]
- [Any flags raised]
- [Decisions made]
- [Adjustments to plan]
```

The TUI asks the coach to produce a 3–5 line session summary at the end of each conversation, then writes it to this file automatically. The coach cannot "forget" to save — the save is triggered by the TUI, not the LLM.

### Run database — `~/.strava-coach/run_data/run_*.json`

Local cache of Strava activities. Same structure as v1. What changes is what gets **fed to the LLM context**:

| Situation | What goes into context |
|---|---|
| Session startup | Compact digest of runs since last session |
| Weekly overview | 4-week summary table (one line per week) |
| Discussing a specific run | Full detail fetched on demand |
| **Never** | Raw streams, full lap arrays, map polylines |

**Compact run format (one line per run):**
```
Mar 15 | Long Run  | 35.0km  2:51h | 4:53/km | HR 149/184 | 309m ↑
Mar 14 | Easy      |  9.5km  0:49m | 5:10/km | HR 136/151 |  87m ↑
Mar 12 | Workout   | 14.5km  1:03m | 4:21/km | HR 162/185 |  45m ↑
```

**Weekly summary format:**
```
Week Mar 10–16: 4 runs | 71.3km | 7h02m | Avg HR 143 | Long run ✓
Week Mar  3–9:  5 runs | 68.1km | 6h45m | Avg HR 141 | Tempo ✓
```

---

## API Budget

Strava rate limit: 100 requests/15 min, 1000 requests/day. Design conservatively around 200/day to leave headroom.

| Operation | Calls |
|---|---|
| Onboarding activity fetch (4 weeks) | ~20 |
| Session startup sync (per new activity) | 1 per run |
| On-demand run detail | 1 per activity |
| Streams | Never automatically; only if coach explicitly requests |
| **Typical daily total** | **~5–10** |

---

## Training Plan Format

Switch from JSON to **YAML**. Same structure, same parsing logic, but:
- Human-readable without a JSON formatter
- Supports inline comments (`# Recovery week — cut volume ~20%`)
- LLMs make surgical edits without regenerating the whole file
- No trailing comma / bracket mismatch errors

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
        structure: 2km WU, 5×1600m @4:00 w/400m rec, 2km CD
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

**Migration:** one-time script converts existing `plan_*.json` → `plan_*.yaml`.

Use **ruamel.yaml** (not PyYAML) so that round-trip edits preserve comments and formatting.

---

## Calendar Export

Training plan → calendar in two phases:

**Phase 1 (implement first): ICS export**
- `strava-coach export-calendar [plan_id]` generates a `.ics` file
- User imports into Google Calendar / Apple Calendar / anything
- Zero infrastructure, works everywhere
- Limitation: static — re-export and re-import after plan edits

**Phase 2 (later): Google Calendar API**
- Write workouts directly to a dedicated "Training Plan" calendar
- Events update when the plan changes
- Requires one-time OAuth setup (same pattern as Strava auth in setup wizard)
- Worth it if plan editing mid-block becomes common

---

## Repo Cleanup (Pre-Release Checklist)

- [ ] All secrets in `~/.strava-coach/config.toml`, `.env` removed from repo patterns
- [ ] `run_data/`, `training_plans/`, `coaching_data/athlete_profile_*.json`, `coaching_data/session_notes_*.json` in `.gitignore`
- [ ] `skills/running-coach/SKILL.md` — remove or move to `docs/` with a note that it's for OpenClaw users
- [ ] README rewritten: covers setup, daily use, LLM configuration
- [ ] `example.config.toml` ships in repo
- [ ] `misc/get_strava_token.py` promoted into `strava-coach setup` wizard, old script removed
- [ ] License verified ✓

---

## MCP Server

Keep it. Users running Claude Desktop or other MCP hosts can still use the server directly. But it's no longer the primary interface — the TUI is. The MCP server and TUI share the same underlying storage, tools, and memory files.

---

## What Stays the Same

- Coaching persona system (`coaching_data/personas/`) — solid, no changes
- `add_coaching_feedback` tool (posts to Strava activity descriptions) — keep
- Local run caching pattern (`RunStorage`) — keep, just change what gets reported from it
- `pyproject.toml` / `uv` toolchain — keep
