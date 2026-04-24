"""Storage for coaching personas and guidelines."""

from pathlib import Path

from mcpacer.storage.base import BaseStorage


class CoachingStorage(BaseStorage):
    """Storage for coaching personas and shared guidelines.

    Handles loading persona markdown files and the shared coaching guidelines.
    Memory (COACH_MEMORY.md, session logs) is handled by MemoryStorage.
    """

    DEFAULT_COACH = "coach"

    def __init__(self) -> None:
        super().__init__("coaching_data")

    def get_guidelines_path(self) -> Path:
        return self.data_dir / "coaching_guidelines.md"

    def get_guidelines(self) -> str | None:
        return self._load_text(self.get_guidelines_path())

    def get_onboarding_path(self) -> Path:
        return self.data_dir / "onboarding.md"

    def get_onboarding(self) -> str | None:
        return self._load_text(self.get_onboarding_path())

    def get_persona_path(self, coach_name: str | None = None) -> Path:
        if coach_name is None:
            coach_name = self.DEFAULT_COACH
        return self.data_dir / "personas" / f"{coach_name}.md"

    def get_persona(self, coach_name: str | None = None) -> str | None:
        """Get the combined coaching persona and guidelines content."""
        if coach_name is None:
            coach_name = self.DEFAULT_COACH

        persona_content = self._load_text(self.get_persona_path(coach_name))
        guidelines_content = self.get_guidelines()

        if persona_content is None:
            return None

        combined = f"{persona_content}\n\n# Coaching Guidelines\n\n"
        if guidelines_content:
            lines = guidelines_content.split("\n")
            if lines and lines[0].strip() == "# Coaching Guidelines":
                guidelines_content = "\n".join(lines[1:]).lstrip()
            combined += guidelines_content

        return combined

    def list_personas(self) -> list[str]:
        """List available coach persona names."""
        personas_dir = self.data_dir / "personas"
        if not personas_dir.exists():
            return []
        return [p.stem for p in personas_dir.glob("*.md")]
