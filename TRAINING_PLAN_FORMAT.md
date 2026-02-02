# Training Plan Format

This document describes the JSON format for storing marathon training plans.

## Overview

Training plans are stored as JSON files that can be analyzed against your actual Strava data. The format supports different types of workouts including runs, gym sessions, cross training, and rest days.

## JSON Structure

### Top Level Fields

```json
{
  "plan_name": "String - Name of your training plan",
  "goal_race": {
    "date": "YYYY-MM-DD - Race date",
    "race_type": "marathon | half_marathon | 10k | 5k",
    "distance_km": "Float - Race distance in kilometers",
    "goal_time": "HH:MM:SS - Target finish time",
    "goal_pace_min_per_km": "M:SS - Target race pace per km",
    "race_name": "String - Name of the race"
  },
  "created_date": "YYYY-MM-DD - When plan was created",
  "plan_start_date": "YYYY-MM-DD - Training plan start",
  "plan_end_date": "YYYY-MM-DD - Training plan end (race day)",
  "notes": "String - General notes about the plan",
  "weeks": [
    // Array of week objects (see below)
  ]
}
```

### Week Object

```json
{
  "week_number": "Integer - Sequential week number",
  "week_start_date": "YYYY-MM-DD - Monday of this week",
  "total_planned_distance_km": "Float - Total running distance for the week",
  "weekly_focus": "String - Theme/focus for this week",
  "runs": [
    // Array of run/workout objects (see below)
  ]
}
```

### Run/Workout Object

All workouts have these base fields:

```json
{
  "day_of_week": "Monday | Tuesday | ... | Sunday",
  "date": "YYYY-MM-DD - Specific date for this workout",
  "type": "See workout types below",
  "description": "String - Human-readable description"
}
```

#### Workout Types

**1. Easy Run**
```json
{
  "type": "easy",
  "distance_km": "Float - Distance in kilometers",
  "target_pace_min_per_km": "M:SS - Target pace per kilometer",
  "description": "Easy recovery run"
}
```

**2. Workout (Intervals, Tempo, etc.)**
```json
{
  "type": "workout",
  "distance_km": "Float - Total distance including warmup/cooldown",
  "target_pace_min_per_km": "M:SS - Main work pace",
  "structure": "String - Detailed workout structure",
  "description": "Threshold intervals"
}
```

Example structures:
- `"2km warmup, 5x1600m @ 4:00/km with 400m recovery, 2km cooldown"`
- `"3km warmup, 3x3km @ threshold pace with 2min rest, 2km cooldown"`
- `"2km warmup, 20min tempo @ 4:10/km, 2km cooldown"`

**3. Long Run**
```json
{
  "type": "long_run",
  "distance_km": "Float - Distance in kilometers",
  "target_pace_min_per_km": "M:SS - Target pace",
  "structure": "Optional - If progressive or with variations",
  "description": "Weekly long run"
}
```

**4. Tuneup Race**
```json
{
  "type": "tuneup_race",
  "distance_km": "Float - Race distance",
  "target_pace_min_per_km": "M:SS - Goal race pace",
  "race_name": "String - Name of the race",
  "description": "Half marathon tuneup race"
}
```

**5. Gym Session**
```json
{
  "type": "gym",
  "duration_minutes": "Integer - Session duration",
  "description": "Strength training - lower body focus"
}
```

**6. Cross Training**
```json
{
  "type": "cross_training",
  "duration_minutes": "Integer - Session duration",
  "description": "Cycling or swimming"
}
```

**7. Rest Day**
```json
{
  "type": "rest",
  "description": "Complete rest day"
}
```

## Using the Format

### Creating a New Training Plan

1. Copy `training_plan_template.json` to a new file (e.g., `my_marathon_plan.json`)
2. Update the goal race information
3. Fill in the weeks with your planned workouts
4. Save the file

### Analyzing Your Plan

Run the analysis script:
```bash
uv run strava-analyze-plan my_marathon_plan.json
```

This will show:
- Plan overview and days until race
- Upcoming workouts (next 7 days)
- Plan adherence statistics
- Missed workouts
- Completed workouts with actual vs. planned comparison

### Generating Plans with AI

When asking AI to create a training plan, use a prompt like:

```
I have a race on April 4th, 2026. It's a marathon and I want to target sub-3 hours.
Is this realistic given my recent training? Can you propose a training plan following
the format in TRAINING_PLAN_FORMAT.md that would get me there?

Please create a complete training_plan.json file with 16 weeks of training.
```

The AI will:
1. Analyze your recent training from `generate_training_report.py`
2. Assess if your goal is realistic
3. Generate a complete training plan in JSON format
4. You can save this as `training_plan.json` and start tracking with `analyze_training_plan.py`

## Tips

- **Be realistic with paces**: Use your recent training report to set appropriate paces
- **Include variety**: Mix easy runs, workouts, long runs, and recovery
- **Plan recovery weeks**: Every 3-4 weeks, reduce volume by 20-30%
- **Taper properly**: Final 2-3 weeks should reduce volume significantly
- **Update as needed**: Modify the JSON file based on how training is going

## Workflow Example

1. **Update your run data:**
   ```bash
   uv run strava-update-data
   ```

2. **Generate training report:**
   ```bash
   uv run strava-generate-report > my_training_report.txt
   ```

3. **Share report with AI and request plan:**
   - Paste the training report
   - Ask for a training plan
   - AI generates JSON following this format

4. **Save the plan:**
   - Save AI's response as `training_plan.json`

5. **Track your progress:**
   ```bash
   uv run strava-analyze-plan training_plan.json
   ```

6. **Repeat weekly:**
   - Run analysis to see upcoming workouts
   - Update run data after each workout
   - Ask AI for plan adjustments if needed
