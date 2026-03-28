# Strava Running Coach MCP

An AI-powered running coach that connects Claude to your Strava data. Get personalized training plans, track your progress, and receive coaching feedback with customizable coach personas.

The strava MCP server was based off of https://github.com/tomekkorbak/strava-mcp-server.

## Features

- **Personalized Coaching**: Customizable coach personas
- **Training Plans**: Create, save, and track structured training plans in JSON format
- **Progress Tracking**: Automatically sync and analyze your Strava running data
- **Plan Adherence**: Compare planned vs actual workouts with completion rates
- **Session Memory**: Coaching notes persist across conversations for continuity
- **Visual Calendar**: Generate interactive HTML calendars showing your training plan

## Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://github.com/astral-sh/uv) package manager
- Strava API credentials

### Installation

```bash
# Clone the repository
git clone https://github.com/peteskomoroch/strava-running-coach-mcp.git
cd strava-running-coach-mcp

# Install dependencies
uv sync
```

### Strava API Setup

1. Create a Strava API application at https://www.strava.com/settings/api
2. Run the token helper:
   ```bash
   uv run python misc/get_strava_token.py
   ```
3. Follow the prompts to authorize and save your credentials to `.env`

Your `.env` file should contain:
```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token
```

## Usage

### 1. Register the MCP Server

**For Claude Code (recommended):**

```bash
claude mcp add strava -- uv run --directory /absolute/path/to/strava-running-coach-mcp strava-running-coach
```

Replace `/absolute/path/to/strava-running-coach-mcp` with the full path to your cloned repository. The `.env` file in the project root is loaded automatically.

**For Claude Desktop:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "strava": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/strava-running-coach-mcp",
        "run",
        "strava-running-coach"
      ],
      "env": {
        "STRAVA_REFRESH_TOKEN": "your_refresh_token",
        "STRAVA_CLIENT_ID": "your_client_id",
        "STRAVA_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

After adding the configuration, restart Claude Desktop or Claude Code to load the MCP server.

### 2. Install the Running Coach Skill

The `/running-coach-v2` skill automates your coaching check-in workflow (load context, digest runs, post feedback, open conversation). To install it:

```bash
# Copy the skill into the project's Claude Code skills directory
mkdir -p .claude/skills/running-coach-v2
cp skills/running-coach-v2/SKILL.md .claude/skills/running-coach-v2/SKILL.md
```

**Usage:** Open Claude Code in the project directory and run `/running-coach-v2`

### CLI Commands

```bash
# Update local run data from Strava
uv run strava-update-data

# Generate a training report
uv run strava-generate-report

# Analyze plan adherence
uv run strava-analyze-plan [plan_id]

# Generate visual training calendar
uv run strava-generate-calendar [plan_id]
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_activities` | Get recent activities from Strava |
| `get_training_report` | Comprehensive training summary with weekly breakdowns |
| `save_training_plan` | Save a training plan (JSON format) |
| `list_training_plans` | List all saved training plans |
| `get_training_plan` | Retrieve a specific plan |
| `analyze_plan_adherence` | Compare planned vs actual workouts |
| `get_coaching_personas` | List available coaching personas |
| `get_coaching_context` | Load coach persona and athlete profile |
| `save_coaching_note` | Persist coaching insights |
| `update_athlete_profile` | Update athlete preferences and goals |
| `add_coaching_feedback` | Post coaching feedback to Strava activity descriptions |

## Coaching Workflows

### Starting a Coaching Session

Ask Claude to load the coaching context:
> "Let's do a coaching check-in. Load my coaching context and review my recent training."

### Creating a Training Plan

> "I have a marathon on April 4th targeting sub-3 hours. Create a 16-week training plan based on my recent fitness."

### Weekly Check-ins

> "How did my training go this week? What should I focus on?"

### Adjusting Plans

> "I'm feeling some knee pain. Can you adjust my plan for this week?"

## Customizing Your Coach

Coach personas are stored in `coaching_data/personas/`. You can customize existing personas or create new ones by adding `.md` files to this directory.

## Memory & Context Architecture

Every coaching session starts fresh — no conversation history carries over. All continuity comes from structured context loaded at session start via MCP tools.

### What gets loaded

```
SESSION CONTEXT (~4000 tokens)
├── Coach Memory .............. ~600 tok
│   Long-term athlete knowledge: goals, PRs, injuries, patterns, flags
│   └── Session History (one-liners for older sessions)
│
├── Run Context ............... ~1400 tok
│   Training data from Strava, tiered by age
│   Old weeks: one-liner  |  Recent weeks: per-run detail + digests
│
├── Plan Context .............. ~1100 tok
│   Day-by-day training prescriptions, current week marked
│
├── Session Logs .............. ~200 tok
│   Last 3 full session summaries for conversation continuity
│
└── Persona ................... ~500 tok
    Coaching tone, personality, communication style
```

### Coach Memory (`coaching_data/COACH_MEMORY.md`)

The coach's long-term knowledge about the athlete. LLM-written and LLM-maintained via section-level updates (`update_coach_memory(section, content)`). Sections:

| Section | Purpose |
|---------|---------|
| **Athlete** | Name, role, training partners, persona preference |
| **Goals** | Target race, goal time, current training phase |
| **PRs** | Self-reported personal records |
| **Training Context** | Peak volume, key workout paces, plan adjustments, equipment |
| **Active Flags** | Injuries, concerns, things to monitor — reviewed each session |
| **Patterns & Insights** | Behavioral observations (pace creep, workout modifications, etc.) |
| **Session History** | Compressed one-liners from older sessions (auto-generated) |

Updates happen **in real-time** during sessions, not deferred to session end. If the athlete mentions a new injury, it goes into Active Flags immediately.

### Session Logs (`coaching_data/memory/YYYY-MM-DD.md`)

Short summaries (3-5 lines) of each coaching conversation. Written at session end. Provide conversation continuity — "last time we discussed X."

**Two-tier system:**
- **Recent (last 3):** Loaded in full at session start
- **Older:** Auto-distilled into one-liners in the Session History section of coach memory, raw files archived to `memory/archive/`
- **Archive retrieval:** If a one-liner isn't enough, `get_archived_session_log(date)` pulls the full original

Distillation happens automatically when `get_session_logs()` is called — no manual step needed.

```
Day 1  ──→  full log (recent)
Day 2  ──→  full log (recent)
Day 3  ──→  full log (recent)
Day 4  ──→  distilled to one-liner in Session History, raw → archive/
Day 5  ──→  distilled to one-liner in Session History, raw → archive/
...
Day 30 ──→  oldest one-liners drop off (30-line cap)
```

### Run Context

Synced from Strava at session start. Uses the same tiered pattern:
- **Older weeks (10+):** One-liner per week (total km, run count, avg pace/HR, key workout, long run)
- **Recent weeks (3):** Per-run breakdown with activity IDs, paces, HR, elevation, and LLM-generated digest lines

### Run Digestion

Each run gets a compact single-line digest summarizing its structure (e.g. `WU 2km @5:00/km | 8x1km @3:45/km HR 165→185 rec 90s | CD 2km | +110m [workout]`). Generated by the LLM at session start for any undigested runs, saved locally via `save_run_digest()`.

### Plan Context

The active training plan rendered as compact text — two lines per week with the current week highlighted. Loaded separately from run context so the coach can compare prescription vs execution.

### Coaching Persona

Full personality definition loaded from `coaching_data/personas/{name}.md`. Includes tone, communication style, vocabulary, and behavioral rules. Auto-loaded from the persona preference in coach memory — no selection prompt needed each session.

## Project Structure

```
strava-running-coach-mcp/
├── src/strava_running_coach/
│   ├── server.py           # MCP server entry point
│   ├── strava_client.py    # Strava API client
│   ├── tools/              # MCP tool implementations
│   ├── models/             # Pydantic data models
│   ├── storage/            # JSON persistence layer
│   ├── utils/              # Utilities (dates, formatting)
│   └── cli/                # CLI commands
├── coaching_data/          # Coach personas (tracked)
├── run_data/               # Cached Strava data (gitignored)
├── training_plans/         # Saved plans (gitignored)
└── misc/                   # Helper scripts
```

## Acknowledgements

This project is a fork of [strava-mcp-server](https://github.com/tomek-korbak/strava-mcp-server) by Tomek Korbak, extended with coaching features, training plan management, and persistent memory.

## License

MIT License - see [LICENSE](LICENSE) for details.
