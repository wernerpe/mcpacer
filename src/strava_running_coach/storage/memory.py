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
    "session_history": "Session History",
}

SESSION_HISTORY_MAX_LINES = 30


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

    # ── Session Log Distillation ───────────────────────────────────

    def _distill_log_to_oneliner(self, log_path: Path) -> str | None:
        """Extract a one-liner from a session log file.

        Takes the first non-header, non-empty line and truncates to 120 chars.
        Returns '- YYYY-MM-DD: <line>' or None if the file is empty/malformed.
        """
        content = self._load_text(log_path)
        if not content:
            return None

        date_str = log_path.stem  # YYYY-MM-DD
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("##"):
                continue
            if len(line) > 120:
                line = line[:117] + "..."
            return f"- {date_str}: {line}"
        return None

    def _distill_old_logs(self, keep_recent: int = 3) -> None:
        """Distill older session logs into one-liners in Session History.

        Keeps the most recent `keep_recent` logs as full files.
        Older logs are compressed into Session History in COACH_MEMORY.md
        and moved to the archive directory.
        """
        log_files = sorted(self.logs_dir.glob("*.md"), reverse=True)
        if len(log_files) <= keep_recent:
            return

        recent = log_files[:keep_recent]
        old = log_files[keep_recent:]

        # Generate one-liners for old logs
        new_oneliners = []
        files_to_archive = []
        for log_path in old:
            oneliner = self._distill_log_to_oneliner(log_path)
            if oneliner:
                new_oneliners.append(oneliner)
                files_to_archive.append(log_path)

        if not new_oneliners:
            return

        # Read existing Session History from coach memory
        full_text = self._load_text(self.memory_file) or ""
        existing_lines = []
        pattern = re.compile(
            r"^## Session History\s*\n(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(full_text)
        if match:
            for line in match.group(1).strip().split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    existing_lines.append(line)

        # Deduplicate by date prefix
        existing_dates = {line.split(":")[0] for line in existing_lines}
        for oneliner in new_oneliners:
            if oneliner.split(":")[0] not in existing_dates:
                existing_lines.append(oneliner)

        # Sort by date descending, cap at max
        existing_lines.sort(key=lambda l: l[2:12], reverse=True)
        existing_lines = existing_lines[:SESSION_HISTORY_MAX_LINES]

        # Write back to coach memory
        self.update_section("session_history", "\n".join(existing_lines))

        # Archive old log files
        archive_dir = self.logs_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        for log_path in files_to_archive:
            log_path.rename(archive_dir / log_path.name)

    # ── Archive Retrieval ────────────────────────────────────────────

    def get_archived_session_log(self, date_str: str) -> str:
        """Retrieve a full session log from the archive by date.

        Args:
            date_str: Date in YYYY-MM-DD format.

        Returns:
            The full session log content, or a message if not found.
        """
        # Check active logs first, then archive
        active_path = self.logs_dir / f"{date_str}.md"
        if active_path.exists():
            content = self._load_text(active_path)
            if content:
                return content

        archive_path = self.logs_dir / "archive" / f"{date_str}.md"
        if archive_path.exists():
            content = self._load_text(archive_path)
            if content:
                return content

        return f"No session log found for {date_str}."

    # ── Session Logs ─────────────────────────────────────────────────

    def get_session_logs(self, limit: int = 3) -> str:
        """Read the most recent daily session logs.

        Automatically distills older logs into Session History before
        returning the recent ones.

        Args:
            limit: Maximum number of log files to return (default 3).

        Returns:
            Concatenated session log content, or a message if none exist.
        """
        self._distill_old_logs(keep_recent=limit)
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
