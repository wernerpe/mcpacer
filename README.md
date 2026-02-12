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

Add the Strava MCP server to your Claude configuration file:

**For Claude Desktop:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

**For Claude Code:** Edit `~/.claude/mcp_config.json`

Add the following configuration:

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

**Important:** Replace `/absolute/path/to/strava-running-coach-mcp` with the full path to your cloned repository.

After adding the configuration, restart Claude Desktop or Claude Code to load the MCP server.

### 2. Install the Running Coach Skill (Optional)

The `/running-coach` skill automates your coaching check-in workflow. To install it:

```bash
# Create the skills directory if it doesn't exist
mkdir -p ~/.claude/skills

# Copy the skill to your personal skills directory
cp -r skills/running-coach ~/.claude/skills/
```

Once installed, you can use `/running-coach` in any Claude conversation to:
1. Select your coaching persona
2. Load coaching context and athlete profile
3. Fetch fresh training data from Strava
4. Analyze plan adherence
5. Post personalized feedback on all recent runs

The skill is immediately available - no restart required!

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
