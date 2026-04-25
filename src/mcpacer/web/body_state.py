"""In-memory body state shared between the web UI and the MCP body tools.

The UI POSTs painted regions here. MCP tools (running in a separate process)
read this state via HTTP and post highlight updates. Mutations broadcast on
the dashboard event WebSocket so the UI reflects agent-driven changes.
"""

# Canonical region catalog. Must match web/src/lib/BodyViewer.svelte REGIONS.
# Update both when adding/removing regions.
REGION_CATALOG: dict[str, str] = {
    # ===== FRONT =====
    "core": "Core / abdominals",
    "left_tfl": "TFL / hip outer (L)",
    "right_tfl": "TFL / hip outer (R)",
    "left_hip_flexor": "Hip flexor (L)",
    "right_hip_flexor": "Hip flexor (R)",
    "left_adductor": "Adductor / inner thigh (L)",
    "right_adductor": "Adductor / inner thigh (R)",
    "left_quad_upper": "Upper quad (L)",
    "left_quad_mid": "Mid quad (L)",
    "left_quad_lower": "Lower quad (L)",
    "right_quad_upper": "Upper quad (R)",
    "right_quad_mid": "Mid quad (R)",
    "right_quad_lower": "Lower quad (R)",
    "left_knee_outer": "Knee — outer (L)",
    "left_knee_front": "Knee — front (L)",
    "left_knee_inner": "Knee — inner (L)",
    "right_knee_inner": "Knee — inner (R)",
    "right_knee_front": "Knee — front (R)",
    "right_knee_outer": "Knee — outer (R)",
    "left_shin_lateral": "Shin — lateral / peroneal (L)",
    "left_shin_anterior": "Shin — anterior tib (L)",
    "right_shin_anterior": "Shin — anterior tib (R)",
    "right_shin_lateral": "Shin — lateral / peroneal (R)",
    "left_ankle": "Ankle (L)",
    "right_ankle": "Ankle (R)",
    "left_foot_top": "Foot — top (L)",
    "right_foot_top": "Foot — top (R)",
    # ===== BACK =====
    "left_upper_trap": "Upper trap (L)",
    "right_upper_trap": "Upper trap (R)",
    "left_mid_back": "Mid back / rhomboid (L)",
    "mid_back_center": "Mid back — center / thoracic spine",
    "right_mid_back": "Mid back / rhomboid (R)",
    "left_low_back": "Low back — left (QL)",
    "mid_low_back": "Low back — center",
    "right_low_back": "Low back — right (QL)",
    "left_glute_med": "Glute med (L)",
    "left_glute_max": "Glute max (L)",
    "right_glute_med": "Glute med (R)",
    "right_glute_max": "Glute max (R)",
    "left_ham_upper": "Upper hamstring (L)",
    "left_ham_mid": "Mid hamstring (L)",
    "left_ham_lower": "Lower hamstring (L)",
    "right_ham_upper": "Upper hamstring (R)",
    "right_ham_mid": "Mid hamstring (R)",
    "right_ham_lower": "Lower hamstring (R)",
    "left_itb_upper": "IT band — upper (L)",
    "left_itb_lower": "IT band — lower (L)",
    "right_itb_upper": "IT band — upper (R)",
    "right_itb_lower": "IT band — lower (R)",
    "left_knee_back": "Back of knee — popliteal (L)",
    "right_knee_back": "Back of knee — popliteal (R)",
    "left_calf_upper_lat": "Upper calf — lateral gastroc (L)",
    "left_calf_upper_med": "Upper calf — medial gastroc (L)",
    "left_calf_lower": "Lower calf / soleus (L)",
    "right_calf_upper_med": "Upper calf — medial gastroc (R)",
    "right_calf_upper_lat": "Upper calf — lateral gastroc (R)",
    "right_calf_lower": "Lower calf / soleus (R)",
    "left_achilles": "Achilles (L)",
    "right_achilles": "Achilles (R)",
    "left_heel": "Heel (L)",
    "left_arch": "Arch / plantar (L)",
    "right_heel": "Heel (R)",
    "right_arch": "Arch / plantar (R)",
}


# In-memory state (only meaningful in the FastAPI process).
_painted: list[str] = []
_highlighted: list[str] = []
_highlight_reason: str = ""


def get_state() -> dict:
    return {
        "painted": list(_painted),
        "highlighted": list(_highlighted),
        "highlight_reason": _highlight_reason,
    }


def set_painted(regions: list[str]) -> list[str]:
    global _painted
    _painted = [r for r in regions if r in REGION_CATALOG]
    return _painted


def set_highlighted(regions: list[str], reason: str = "") -> list[str]:
    global _highlighted, _highlight_reason
    _highlighted = [r for r in regions if r in REGION_CATALOG]
    _highlight_reason = reason or ""
    return _highlighted
