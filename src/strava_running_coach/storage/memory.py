"""Storage for coach memory (COACH_MEMORY.md) and daily session logs."""

import re
from datetime import date
from pathlib import Path

from strava_running_coach.storage.base import BaseStorage


# Valid section names mapping to ## headers in COACH_MEMORY.md
MEMORY_SECTIONS = {
    "athlete": "Athlete",
    "prs": "PRs",
    "goals": "Goals",
    "active_flags": "Active Flags",
    "training_context": "Training Context",
    "patterns": "Patterns & Insights",
}


class MemoryStorage(BaseStorage):
    """Storage for COACH_MEMORY.md and daily session logs.

    Memory lives in the coaching_data/ directory (same base as personas).
    - coaching_data/COACH_MEMORY.md — long-term athlete knowledge
    - coaching_data/memory/YYYY-MM-DD.md — daily session logs
    """

    def __init__(self) -> None:
        super().__init__("coaching_data")
        self.memory_file = self.data_dir / "COACH_MEMORY.md"
        self.logs_dir = self.data_dir / "memory"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ── COACH_MEMORY.md ──────────────────────────────────────────────

    def read_memory(self) -> str:
        """Read the full COACH_MEMORY.md content.

        Returns:
            The markdown content, or a message if no memory exists yet.
        """
        content = self._load_text(self.memory_file)
        if content is None:
            return "No coach memory found. This athlete has not been onboarded yet."
        return content

    def update_section(self, section: str, content: str) -> str:
        """Rewrite a specific section of COACH_MEMORY.md in-place.

        The section parameter maps to ## headers:
            athlete → ## Athlete
            prs → ## PRs
            goals → ## Goals
            active_flags → ## Active Flags
            training_context → ## Training Context
            patterns → ## Patterns & Insights

        If the section doesn't exist, it is appended. If the file doesn't
        exist, it is created with just this section.

        Args:
            section: Section key (one of MEMORY_SECTIONS keys)
            content: New content for the section (everything after the ## header)

        Returns:
            Confirmation message.
        """
        if section not in MEMORY_SECTIONS:
            valid = ", ".join(MEMORY_SECTIONS.keys())
            return f"Invalid section '{section}'. Valid sections: {valid}"

        header = MEMORY_SECTIONS[section]
        full_text = self._load_text(self.memory_file) or ""

        # Ensure content has a trailing newline
        content = content.rstrip("\n") + "\n"

        # Pattern: find ## Header through to next ## or EOF
        pattern = re.compile(
            rf"(^## {re.escape(header)}\s*\n).*?(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )

        replacement = f"## {header}\n{content}\n"

        if pattern.search(full_text):
            # Replace existing section
            new_text = pattern.sub(replacement, full_text)
        else:
            # Append new section
            if full_text and not full_text.endswith("\n"):
                full_text += "\n"
            new_text = full_text + replacement

        self._save_text(self.memory_file, new_text)
        return f"Updated '{header}' section in coach memory."

    # ── Session Logs ─────────────────────────────────────────────────

    def get_session_logs(self, limit: int = 3) -> str:
        """Read the most recent daily session logs.

        Args:
            limit: Maximum number of log files to return (default 3).

        Returns:
            Concatenated session log content, or a message if none exist.
        """
        log_files = sorted(self.logs_dir.glob("*.md"), reverse=True)

        if not log_files:
            return "No previous session logs found."

        logs = []
        for log_file in log_files[:limit]:
            content = self._load_text(log_file)
            if content:
                logs.append(content.strip())

        if not logs:
            return "No previous session logs found."

        return "\n\n---\n\n".join(logs)

    def save_session_log(self, summary: str, coach_name: str = "Coach") -> str:
        """Save a session log for today.

        Args:
            summary: The session summary (3-5 lines).
            coach_name: Name of the coach persona used.

        Returns:
            Confirmation message.
        """
        today = date.today().isoformat()
        log_path = self.logs_dir / f"{today}.md"

        content = f"## Session {today} — {coach_name}\n{summary.strip()}\n"

        # If a log already exists for today, append to it
        existing = self._load_text(log_path)
        if existing:
            content = existing.rstrip("\n") + "\n\n" + content

        self._save_text(log_path, content)
        return f"Session log saved for {today}."
