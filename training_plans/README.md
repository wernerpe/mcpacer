# Training Plan YAML Format

Plans live here as `plan_<plan_id>.yaml`. The plan whose `goal_race.date` is the nearest future date auto-activates — no flag needed.

**No MCP tool exists for creating a plan.** Write the YAML file directly, then edit with the surgical MCP tools (`update_plan_run`, `update_plan_week`, `add_plan_run`, `remove_plan_run`, `add_plan_comment`) — never rewrite the whole file.

## Minimal template

```yaml
plan_name: Human-readable plan name
goal_race:
  date: 2026-05-09                   # YYYY-MM-DD
  race_type: 10_mile                 # marathon | half_marathon | 10_mile | 10k | 5k | other
  distance_km: 16.1
  goal_time: "59:59"
  goal_pace_min_per_km: "3:44"
  race_name: Race Name

plan_start_date: 2026-04-20          # first Monday of week 1
notes: One-paragraph block philosophy.

weeks:
- week_number: 1
  week_start_date: 2026-04-20        # MUST be a Monday
  total_planned_distance_km: 52
  weekly_focus: One-line focus
  runs:
  - day_of_week: Monday              # Monday..Sunday
    type: easy                       # easy | workout | long_run | recovery | shakeout | rest | race
    distance_km: 8
    target_pace_min_per_km: "5:20"
    description: Short label
  - day_of_week: Tuesday
    type: workout
    distance_km: 12
    target_pace_min_per_km: "4:00"
    structure: WU 2km + 4×1mile @ 3:55/km with 75s jog rec + CD 2km
    description: Threshold intervals
  - day_of_week: Sunday
    type: rest
    description: Complete rest
```

## Rules

- **`week_start_date` must be a Monday.** Current-week lookup scans `week_start <= today <= week_start + 6 days`.
- **`structure`** is optional but recommended for any day with intervals / tempo / progression — the frontend renders it under `description` in the week detail panel.
- **Rest days** omit `distance_km` and `target_pace_min_per_km`.
- **Dates derive at read time** from `week_start_date + day_of_week offset` — do not store per-workout dates.
- **Editing:** use surgical MCP tools (`update_plan_run`, etc.). LLMs rewriting whole YAML files introduce subtle errors (dropped workouts, lost comments, wrong dates).
- **Adjustments:** document in-flight changes as YAML `#` comments on the week via `add_plan_comment` — the comment persists through future reads and exports.

## Verification

After writing a new plan, confirm it's picked up:

```
mcp__strava__list_training_plans          # should show the new plan
mcp__strava__get_plan_context             # should render it as ACTIVE if race date is nearest future
```

If `get_plan_context` shows the new plan with `Status: Week N of M`, you're done.

## Reference files

- `plan_sub3-marathon-apr2026.yaml` — 9-week marathon build; example of in-flight adjustments documented as YAML comments
- See `DESIGN.md` (repo root) for full schema rationale and surgical-edit philosophy
