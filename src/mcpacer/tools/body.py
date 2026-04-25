"""MCP tools for body region marking — bidirectional with the web UI.

The MCP server runs in a separate process from the FastAPI dashboard, so
these tools talk to the dashboard over HTTP. The shared catalog of region
IDs lives in mcpacer.web.body_state.REGION_CATALOG.
"""

import json
import os
import urllib.error
import urllib.request

from mcpacer.web.body_state import REGION_CATALOG

_DEFAULT_API_BASE = "http://127.0.0.1:8000"


def _api_base() -> str:
    return os.environ.get("MCPACER_API_BASE", _DEFAULT_API_BASE)


def _http_get(path: str) -> dict:
    url = _api_base() + path
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post(path: str, body: dict) -> dict:
    url = _api_base() + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Group regions by body area for the discoverability tool.
_GROUPS: list[tuple[str, list[str]]] = [
    ("Front — Hip / Core", ["core", "tfl", "hip_flexor", "adductor"]),
    ("Front — Quad", ["quad"]),
    ("Front — Knee (front view)", ["knee_front", "knee_outer", "knee_inner"]),
    ("Front — Shin / Foot", ["shin", "ankle", "foot_top"]),
    ("Back — Upper / Mid / Low back", ["upper_trap", "mid_back", "low_back"]),
    ("Back — Glute", ["glute"]),
    ("Back — Hamstring", ["ham_"]),
    ("Back — IT band / Knee back", ["itb", "knee_back"]),
    ("Back — Calf", ["calf"]),
    ("Back — Achilles / Heel / Arch", ["achilles", "heel", "arch"]),
]


def _group_for(rid: str) -> str:
    for label, patterns in _GROUPS:
        if any(p in rid for p in patterns):
            return label
    return "Other"


def register_body_tools(mcp):
    """Register body region MCP tools."""

    @mcp.tool()
    def list_body_regions() -> str:
        """
        List all valid body region IDs that can be highlighted on the body
        diagram or that the athlete might paint as a source of pain or
        tightness. Use this to discover region IDs before calling
        highlight_body_regions.

        Each region has a stable ID (e.g. left_itb_lower) and a human-
        readable label (e.g. "IT band — lower (L)"). Regions are grouped
        by body area.

        Returns:
            Grouped list of region IDs and labels.
        """
        grouped: dict[str, list[tuple[str, str]]] = {}
        for rid, label in REGION_CATALOG.items():
            grouped.setdefault(_group_for(rid), []).append((rid, label))

        # Render in a fixed order matching _GROUPS, then any leftovers.
        order = [g for g, _ in _GROUPS] + ["Other"]
        lines: list[str] = []
        for group in order:
            items = grouped.get(group, [])
            if not items:
                continue
            lines.append(f"## {group}")
            for rid, label in items:
                lines.append(f"  {rid:34s}  {label}")
            lines.append("")
        return "\n".join(lines).rstrip()

    @mcp.tool()
    def get_painted_regions() -> str:
        """
        Read the body regions the athlete has painted/marked on the body
        diagram. These are areas the athlete is reporting pain, tightness,
        or concern. Call this when the athlete refers to "what I've marked",
        "this area", or "where it hurts" — or proactively to check whether
        anything has been flagged.

        Returns:
            A list of painted region IDs with their human labels, or a
            note that nothing is painted.
        """
        try:
            state = _http_get("/api/body/state")
        except urllib.error.URLError as e:
            return f"Error reading painted regions: {e}"

        painted = state.get("painted", []) or []
        if not painted:
            return "(no regions painted by the athlete)"
        lines = ["The athlete has painted these regions:"]
        for rid in painted:
            label = REGION_CATALOG.get(rid, rid)
            lines.append(f"  - {rid}: {label}")
        return "\n".join(lines)

    @mcp.tool()
    def highlight_body_regions(regions: list[str], reason: str = "") -> str:
        """
        Highlight one or more body regions in the dashboard's Body panel
        (shown amber). Use this to draw the athlete's attention to a chain
        of related structures, suggest "is this what hurts?", or visualize
        the kinematic chain you're reasoning about.

        Calling this REPLACES the previous highlight set (it is not
        additive). To wipe, pass an empty list or call clear_body_highlights.

        Args:
            regions: List of region IDs (use list_body_regions to discover
                     valid IDs). Invalid IDs are silently dropped.
            reason: Short caption explaining why these are highlighted —
                    shown to the athlete in the panel (e.g.
                    "checking IT band kinematic chain").

        Returns:
            Confirmation with the regions actually highlighted.
        """
        try:
            result = _http_post(
                "/api/body/highlighted",
                {"regions": regions, "reason": reason},
            )
        except urllib.error.URLError as e:
            return f"Error setting highlights: {e}"

        applied = result.get("highlighted", []) or []
        if not applied:
            return (
                "Highlight set is empty (regions filtered as invalid). "
                "Call list_body_regions to see valid IDs."
            )
        labels = [REGION_CATALOG.get(r, r) for r in applied]
        return f"Highlighted {len(applied)} region(s): {', '.join(labels)}"

    @mcp.tool()
    def clear_body_highlights() -> str:
        """
        Clear all amber highlights in the Body panel. Does NOT touch what
        the athlete has painted — only the agent-driven highlights.

        Returns:
            Confirmation.
        """
        try:
            _http_post("/api/body/highlighted", {"regions": [], "reason": ""})
        except urllib.error.URLError as e:
            return f"Error clearing highlights: {e}"
        return "Highlights cleared."
