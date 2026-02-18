---
name: running-coach
description: Perform a complete running coach check-in by loading coaching context, fetching fresh training data, analyzing plan adherence, and posting feedback on recent runs
---

# Running Coach Check-in

You are performing a running coach check-in. Follow these steps in order:

## 1. Select Coaching Persona
- First, call `mcp__strava__get_coaching_personas` to get the list of available coaching personas
- Use `AskUserQuestion` to ask the user which coaching persona to use for this check-in
- Present `coach` as the default/recommended option — it is the factual, data-driven coach built for consistency and goal tracking

## 2. Load Coaching Context
Call `mcp__strava__get_coaching_context` with the selected `coach_name` parameter to load:
- The coaching persona (adopt this personality)
- Athlete profile and preferences
- Recent coaching notes
- Active training plan summary

## 3. Get Fresh Training Data
Call `mcp__strava__get_training_report` with `refresh: true` to fetch the latest activities from Strava and get:
- Overall training summary
- Weekly breakdowns
- Individual run details with lap splits

## 4. Analyze Training Plan
- Call `mcp__strava__list_training_plans` to find the active plan
- Call `mcp__strava__get_training_plan` with the active plan ID
- Call `mcp__strava__analyze_plan_adherence` to see completion rates, missed workouts, and upcoming sessions

## 5. Post Feedback on Recent Runs
For each recent run (from the training report):
- Review the run details (distance, pace, heart rate, laps)
- Consider the context from the training plan and adherence
- Use `mcp__strava__add_coaching_feedback` to post personalized feedback directly to Strava
- Make feedback specific and aligned with the coaching persona

## Guidelines
- Adopt the coaching persona from the context (tone, style, personality)
- Reference specific metrics (pace, heart rate zones, splits)
- Connect runs to the broader training plan goals
- Note improvements or areas to focus on
- Post feedback to ALL recent runs that don't already have coaching feedback
