# Strava Running Coach MCP

An AI-powered running coach that connects Claude to your Strava data. Get personalized training plans, track your progress, and receive coaching feedback with customizable coach personas.

## Features

- **Personalized Coaching**: Customizable coach personas (David Goggins-style tough love or a grumpy Swiss coach)
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

### Claude Desktop / Claude Code Configuration

Add to your MCP settings:

```json
{
  "mcpServers": {
    "strava": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/strava-running-coach-mcp",
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
| `get_coaching_context` | Load coach persona and athlete profile |
| `save_coaching_note` | Persist coaching insights |
| `update_athlete_profile` | Update athlete preferences and goals |

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

Edit `coaching_data/coaching_persona.md` to customize your coach's personality. Two examples are provided:
- `coaching_persona.md` - David Goggins-style tough love
- `coaching_persona_roland.md` - Grumpy Swiss coach with local expressions

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
