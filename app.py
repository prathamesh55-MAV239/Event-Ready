"""
EventReady — Pre-Event Failure Detector
Streamlit Application — Clean, reliable, and professional dashboard.

Features:
  - Header with Event Ready branding and local AI status
  - Event input form with natural-language description and 'Load Example'
  - Readiness Status: READY, READY WITH WARNINGS, or NOT READY
  - Key Findings summary (Passed, Blockers, Unknowns)
  - Evidence Ledger with detailed breakdown tables
  - Next Actions and Smart Suggestions engine
  - Report download button
  - Collapsible Sidebar with current inventory & rooms
"""

import json
import re
import streamlit as st
import pandas as pd
import ollama

from tools import (
    TOOL_REGISTRY,
    calculate_budget,
    check_resources,
    check_room_capacity,
    check_staffing,
    check_accessibility,
    generate_suggestions,
    EQUIPMENT_INVENTORY,
    ROOM_DATABASE,
    STAFF_AVAILABLE,
    UNIT_PRICES,
    ACCESSIBILITY_FEATURES,
)

# ─────────────────────────
# Configuration & Constants
# ─────────────────────────

MODEL_NAME = "llama3.2:3b"
SKILL_PROMPT_PATH = "skill.md"

EXAMPLE_PLAN = """We are organizing a Python Workshop in Lab 1.

Expected attendees: 45 students.

Equipment needed:
- 40 laptops
- 2 projectors
- 3 microphones
- 10 extension cords
- 50 chairs

Staff required:
- 20 volunteers
- 2 coordinators
- 2 technical support
- 1 first aid

Accessibility requirements:
- Wheelchair ramps
- Accessible restrooms
- Sign language interpreter

Budget items:
- Refreshments for 45 people
- Certificates for 45 people
- 3 banners
- Venue booking (1 unit)
- Marketing (1 unit)"""

# ──────────────────────────────────────
# Minimal, Scoped CSS (Soft Lavender)
# ──────────────────────────────────────

MINIMAL_CSS = """
<style>
/* ── Force cohesive light lavender & deep purple theme regardless of browser dark mode ── */

/* Main canvas background */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #F8F6FC !important;
    color: #202335 !important;
}

/* Sidebar background and text */
section[data-testid="stSidebar"], [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
    background-color: #EDE7F3 !important;
    border-right: 1px solid #DFD8EB !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div {
    color: #202335 !important;
}

/* Force dark, legible text on all headings */
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6 {
    color: #202335 !important;
    font-weight: 700 !important;
}

/* Force dark, legible text on all paragraphs and spans */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
p, span, label, [data-testid="stWidgetLabel"] p {
    color: #202335 !important;
}

/* Subtitles and captions */
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, .stCaption {
    color: #555869 !important;
    font-weight: 500 !important;
}

/* Text area & Inputs — crisp white card with dark text */
.stTextArea textarea, textarea, [data-baseweb="textarea"], [data-baseweb="textarea"] textarea {
    background-color: #FFFFFF !important;
    color: #202335 !important;
    border: 1.5px solid #D4CBE5 !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    font-size: 0.95rem !important;
}
.stTextArea textarea:focus, textarea:focus {
    border-color: #4335BC !important;
    box-shadow: 0 0 0 2px rgba(67, 53, 188, 0.15) !important;
}

/* Primary Button (Deep Purple with crisp white text) */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"],
button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background-color: #4335BC !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    padding: 10px 24px !important;
    box-shadow: 0 2px 6px rgba(67, 53, 188, 0.25) !important;
}
.stButton > button[kind="primary"]:hover,
button[kind="primary"]:hover {
    background-color: #3528A6 !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 10px rgba(67, 53, 188, 0.35) !important;
}

/* Secondary Button (Load Example) */
.stButton > button[kind="secondary"],
.stButton > button[data-testid="stBaseButton-secondary"],
button[kind="secondary"],
.stButton > button {
    background-color: #EDE7F3 !important;
    color: #4335BC !important;
    border: 1.5px solid #D4CBE5 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
.stButton > button:hover {
    background-color: #E2DAEC !important;
    color: #3528A6 !important;
    border-color: #4335BC !important;
}

/* Metric boxes */
[data-testid="stMetric"] {
    background-color: #FFFFFF !important;
    border: 1px solid #EBE4F5 !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
    box-shadow: 0 1px 4px rgba(67, 53, 188, 0.04) !important;
}
[data-testid="stMetricLabel"] p {
    color: #5D6073 !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] div, [data-testid="stMetricValue"] {
    color: #202335 !important;
    font-weight: 700 !important;
}

/* Expanders */
[data-testid="stExpander"], details {
    background-color: #FFFFFF !important;
    border: 1px solid #E5DDF0 !important;
    border-radius: 10px !important;
}
summary, summary span, [data-testid="stExpander"] summary p {
    color: #202335 !important;
    font-weight: 600 !important;
}

/* Status Banners */
.er-banner-ready {
    background-color: #EDF9F1 !important;
    border: 1px solid #BFEAD0 !important;
    border-left: 6px solid #2E7D4F !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    margin-bottom: 18px !important;
}
.er-banner-ready h3, .er-banner-ready p {
    color: #1E6E3E !important;
}

.er-banner-warning {
    background-color: #FFF9ED !important;
    border: 1px solid #FFE7B3 !important;
    border-left: 6px solid #D9822B !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    margin-bottom: 18px !important;
}
.er-banner-warning h3, .er-banner-warning p {
    color: #8A5400 !important;
}

.er-banner-not-ready {
    background-color: #FDF2F3 !important;
    border: 1px solid #F8C8CC !important;
    border-left: 6px solid #C0392B !important;
    border-radius: 10px !important;
    padding: 16px 20px !important;
    margin-bottom: 18px !important;
}
.er-banner-not-ready h3, .er-banner-not-ready p {
    color: #96271B !important;
}

/* Download button */
[data-testid="stDownloadButton"] > button {
    background-color: #4335BC !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
}
</style>
"""



# ────────────────────────────────────────────────────
# Phase 1 — Extraction (AI with pattern fallback)
# ────────────────────────────────────────────────────

EXTRACTION_PROMPT = """You are a data extractor. Read the event plan and return ONLY a JSON object.
No explanation. No markdown. Only the raw JSON object.

Extract this JSON structure:
{
  "room_name": "<room name as a single word, e.g. lab_1, seminar_hall_a, auditorium>",
  "expected_attendees": <integer>,
  "equipment": {<item_name>: <quantity_integer>, ...},
  "staff": {<role_name>: <quantity_integer>, ...},
  "accessibility": [<feature_name_string>, ...],
  "budget_items": [{"item": <price_key>, "quantity": <integer>}, ...]
}

Known room names (use exactly): seminar_hall_a, seminar_hall_b, lab_1, lab_2, classroom_101, classroom_102, auditorium, open_ground
Known equipment names (use exactly): laptops, projectors, microphones, speakers, whiteboards, extension_cords, hdmi_cables, webcams, printers, chairs, tables
Known staff roles (use exactly): volunteers, coordinators, technical_support, security, first_aid, registration_desk
Known accessibility features (use exactly): wheelchair_ramps, sign_language_interpreter, hearing_loop, braille_materials, accessible_restrooms, reserved_seating, screen_reader_compatible_materials
Known budget price keys (use exactly): refreshments_per_person, certificates_per_person, banners_per_unit, venue_booking_flat, marketing_flat, laptops_rental_per_unit, projectors_rental_per_unit, microphones_rental_per_unit, speakers_rental_per_unit, chairs_rental_per_unit, tables_rental_per_unit

Return ONLY the JSON. Nothing else."""


def extract_event_data_ai(event_text: str) -> dict | None:
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": event_text},
            ],
            options={"temperature": 0.0},
        )
        content = response.get("message", {}).get("content", "").strip()
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content).strip()
        return json.loads(content)
    except Exception:
        return None


def extract_event_data_regex(event_text: str) -> dict:
    """Deterministic regex extraction — works when Ollama is unavailable."""
    text = event_text.lower()

    attendees = 0
    m = re.search(r"(\d+)\s*(?:students?|attendees?|participants?|people)", text)
    if m:
        attendees = int(m.group(1))

    room = "seminar_hall_a"
    for r in ROOM_DATABASE:
        if r.replace("_", " ") in text or r in text:
            room = r
            break

    equipment = {}
    item_patterns = {
        "laptops": r"(\d+)\s*laptops?",
        "projectors": r"(\d+)\s*projectors?",
        "microphones": r"(\d+)\s*(?:microphones?|mics?)",
        "speakers": r"(\d+)\s*speakers?",
        "extension_cords": r"(\d+)\s*extension\s*cords?",
        "hdmi_cables": r"(\d+)\s*hdmi\s*cables?",
        "webcams": r"(\d+)\s*webcams?",
        "chairs": r"(\d+)\s*chairs?",
        "tables": r"(\d+)\s*tables?",
        "whiteboards": r"(\d+)\s*whiteboards?",
        "printers": r"(\d+)\s*printers?",
    }
    for item, pat in item_patterns.items():
        m = re.search(pat, text)
        if m:
            equipment[item] = int(m.group(1))

    staff = {}
    staff_patterns = {
        "volunteers": r"(\d+)\s*volunteers?",
        "coordinators": r"(\d+)\s*coordinators?",
        "technical_support": r"(\d+)\s*technical\s*(?:support)?",
        "security": r"(\d+)\s*security",
        "first_aid": r"(\d+)\s*first\s*aid",
        "registration_desk": r"(\d+)\s*registration",
    }
    for role, pat in staff_patterns.items():
        m = re.search(pat, text)
        if m:
            staff[role] = int(m.group(1))

    accessibility = []
    access_keywords = {
        "wheelchair_ramps": ["wheelchair", "ramp"],
        "accessible_restrooms": ["accessible restroom", "accessible bathroom", "accessible toilet"],
        "sign_language_interpreter": ["sign language", "interpreter"],
        "hearing_loop": ["hearing loop"],
        "braille_materials": ["braille"],
        "reserved_seating": ["reserved seating"],
        "screen_reader_compatible_materials": ["screen reader"],
    }
    for feature, keywords in access_keywords.items():
        if any(kw in text for kw in keywords):
            accessibility.append(feature)

    budget_items = []
    if attendees > 0:
        if any(w in text for w in ["refreshment", "food", "snack", "meal"]):
            budget_items.append({"item": "refreshments_per_person", "quantity": attendees})
        if any(w in text for w in ["certificate", "cert"]):
            budget_items.append({"item": "certificates_per_person", "quantity": attendees})
    m = re.search(r"(\d+)\s*banners?", text)
    if m:
        budget_items.append({"item": "banners_per_unit", "quantity": int(m.group(1))})
    if "venue" in text:
        budget_items.append({"item": "venue_booking_flat", "quantity": 1})
    if "marketing" in text:
        budget_items.append({"item": "marketing_flat", "quantity": 1})

    return {
        "room_name": room,
        "expected_attendees": attendees,
        "equipment": equipment,
        "staff": staff,
        "accessibility": accessibility,
        "budget_items": budget_items,
    }


# ──────────────────────────────────
# Phase 2 — Run Tools Deterministically
# ──────────────────────────────────

def run_all_tools(event_data: dict) -> dict:
    results = {}
    if event_data.get("room_name") and event_data.get("expected_attendees", 0) > 0:
        results["check_room_capacity"] = check_room_capacity(
            room_name=event_data["room_name"],
            expected_attendees=event_data["expected_attendees"],
        )
    if event_data.get("equipment"):
        results["check_resources"] = check_resources(required_items=event_data["equipment"])
    if event_data.get("staff"):
        results["check_staffing"] = check_staffing(roles_needed=event_data["staff"])
    if event_data.get("accessibility"):
        results["check_accessibility"] = check_accessibility(requirements=event_data["accessibility"])
    if event_data.get("budget_items"):
        results["calculate_budget"] = calculate_budget(items=event_data["budget_items"])
    return results


# ──────────────────────────────────────────
# Readiness Verdict & Findings Calculator
# ──────────────────────────────────────────

def calculate_readiness(tool_results: dict) -> dict:
    """
    Evaluates check results into:
      - status: READY | READY WITH WARNINGS | NOT READY
      - passed_checks: list of verified passing items
      - blockers: list of confirmed critical shortages or failures
      - warnings: list of non-critical warnings
      - unknowns: list of items without database records
    """
    blockers = []
    warnings = []
    passed = []
    unknowns = []

    # 1. Venue
    if "check_room_capacity" in tool_results:
        r = tool_results["check_room_capacity"]
        v_status = r.get("status", "UNKNOWN")
        room_name = r.get("room", "venue").replace("_", " ").title()
        cap = r.get("room_capacity", "?")
        att = r.get("expected_attendees", "?")

        if v_status == "OVER_CAPACITY":
            blockers.append(f"Venue `{room_name}` over capacity: holds {cap}, but {att} expected.")
        elif v_status == "NEAR_CAPACITY":
            warnings.append(f"Venue `{room_name}` near capacity ({att}/{cap} seats filled).")
            passed.append(f"Venue capacity ({att}/{cap} seats)")
        elif v_status == "OK":
            passed.append(f"Venue capacity ({att}/{cap} seats)")

        for w in r.get("warnings", []):
            warnings.append(f"Venue: {w}")

    # 2. Equipment
    if "check_resources" in tool_results:
        r = tool_results["check_resources"]
        for it in r.get("shortages", []):
            name = it["item"].replace("_", " ").title()
            blockers.append(f"Equipment shortage: `{name}` needs {it['required']}, only {it['in_stock']} in stock (short by {it['shortage']}).")
        for it in r.get("available", []):
            name = it["item"].replace("_", " ").title()
            passed.append(f"Equipment `{name}` available ({it['in_stock']} in stock, need {it['required']})")
        for it in r.get("unknown", []):
            name = it["item"].replace("_", " ").title()
            unknowns.append(f"Equipment `{name}`: not tracked in college inventory database.")

    # 3. Staff
    if "check_staffing" in tool_results:
        r = tool_results["check_staffing"]
        for st_it in r.get("shortages", []):
            role = st_it["role"].replace("_", " ").title()
            blockers.append(f"Staff shortage: `{role}` needs {st_it['needed']}, only {st_it['available']} available (short by {st_it['shortage']}).")
        for st_it in r.get("covered", []):
            role = st_it["role"].replace("_", " ").title()
            passed.append(f"Staff role `{role}` covered ({st_it['available']} available, need {st_it['needed']})")
        for st_it in r.get("unknown", []):
            role = st_it["role"].replace("_", " ").title()
            unknowns.append(f"Staff role `{role}`: not tracked in staff database.")

    # 4. Accessibility
    if "check_accessibility" in tool_results:
        r = tool_results["check_accessibility"]
        for ac in r.get("not_met", []):
            feat = ac["feature"].replace("_", " ").title()
            blockers.append(f"Accessibility requirement `{feat}` is not available.")
        for ac in r.get("met", []):
            feat = ac["feature"].replace("_", " ").title()
            passed.append(f"Accessibility `{feat}` verified available")
        for ac in r.get("unknown", []):
            feat = ac["feature"].replace("_", " ").title()
            unknowns.append(f"Accessibility `{feat}`: unverified/unknown.")

    # 5. Budget
    if "calculate_budget" in tool_results:
        r = tool_results["calculate_budget"]
        passed.append(f"Budget calculated: ₹{r.get('total_cost', 0):,.0f} across {len(r.get('breakdown', []))} items")
        for u in r.get("unknown_items", []):
            unknowns.append(f"Budget item `{u['item']}`: pricing unknown.")

    # Decide verdict
    if blockers:
        status = "NOT READY"
    elif warnings:
        status = "READY WITH WARNINGS"
    else:
        status = "READY"

    return {
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "passed": passed,
        "unknowns": unknowns,
    }


# ──────────────────────────────────────────
# Markdown Report Generator (for download)
# ──────────────────────────────────────────

def build_report_text(tool_results: dict, event_data: dict, suggestions: list, readiness: dict) -> str:
    lines = [
        "# EVENTREADY — PRE-EVENT FAILURE DETECTION REPORT",
        f"**Venue:** `{event_data.get('room_name', 'N/A')}` | **Expected Attendees:** `{event_data.get('expected_attendees', 'N/A')}`",
        f"**Overall Status:** {readiness['status']}",
        "",
        "---",
        "",
        "## 1. READINESS VERDICT",
        f"**Status:** {readiness['status']}",
        f"- Blockers: {len(readiness['blockers'])}",
        f"- Warnings: {len(readiness['warnings'])}",
        f"- Passed Checks: {len(readiness['passed'])}",
        f"- Unknowns: {len(readiness['unknowns'])}",
        "",
    ]

    if readiness["blockers"]:
        lines.append("### Critical Blockers")
        for b in readiness["blockers"]:
            lines.append(f"- 🚨 {b}")
        lines.append("")

    if readiness["warnings"]:
        lines.append("### Warnings")
        for w in readiness["warnings"]:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    lines.append("## 2. EVIDENCE & AUDIT DETAILS")

    # Venue
    if "check_room_capacity" in tool_results:
        r = tool_results["check_room_capacity"]
        lines.append(f"### Venue: {r.get('room')}")
        lines.append(f"- Capacity: {r.get('room_capacity')} | Expected: {r.get('expected_attendees')}")
        lines.append(f"- Projector: {'Yes' if r.get('has_projector') else 'No'} | AC: {'Yes' if r.get('has_ac') else 'No'} | Wheelchair: {'Yes' if r.get('wheelchair_accessible') else 'No'}")
        lines.append("")

    # Equipment
    if "check_resources" in tool_results:
        r = tool_results["check_resources"]
        lines.append("### Equipment")
        for it in r.get("available", []):
            lines.append(f"- [PASS] {it['item']}: {it['in_stock']} in stock (needed: {it['required']})")
        for it in r.get("shortages", []):
            lines.append(f"- [FAIL] {it['item']}: {it['in_stock']} in stock, needed: {it['required']} (short by {it['shortage']})")
        for it in r.get("unknown", []):
            lines.append(f"- [UNKNOWN] {it['item']}: not tracked")
        lines.append("")

    # Staff
    if "check_staffing" in tool_results:
        r = tool_results["check_staffing"]
        lines.append("### Staffing")
        for st_it in r.get("covered", []):
            lines.append(f"- [PASS] {st_it['role']}: {st_it['available']} available (needed: {st_it['needed']})")
        for st_it in r.get("shortages", []):
            lines.append(f"- [FAIL] {st_it['role']}: {st_it['available']} available, needed: {st_it['needed']} (short by {st_it['shortage']})")
        for st_it in r.get("unknown", []):
            lines.append(f"- [UNKNOWN] {st_it['role']}: not tracked")
        lines.append("")

    # Accessibility
    if "check_accessibility" in tool_results:
        r = tool_results["check_accessibility"]
        lines.append("### Accessibility")
        for ac in r.get("met", []):
            lines.append(f"- [PASS] {ac['feature']}: available")
        for ac in r.get("not_met", []):
            lines.append(f"- [FAIL] {ac['feature']}: NOT AVAILABLE")
        for ac in r.get("unknown", []):
            lines.append(f"- [UNKNOWN] {ac['feature']}: unverified")
        lines.append("")

    # Budget
    if "calculate_budget" in tool_results:
        r = tool_results["calculate_budget"]
        lines.append(f"### Budget (Total: ₹{r.get('total_cost', 0):,.0f})")
        for bi in r.get("breakdown", []):
            lines.append(f"- {bi['item']}: {bi['quantity']} × ₹{bi['unit_price']:,} = ₹{bi['line_total']:,}")
        lines.append("")

    # Next Actions
    if suggestions:
        lines.append("## 3. NEXT ACTIONS & FIXES")
        for idx, s in enumerate(suggestions, 1):
            lines.append(f"### {idx}. {s['area']}: {s['issue']}")
            lines.append(s["fix"])
            lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────
# Sidebar: System & College Data
# ──────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.subheader("🎯 EventReady")
        st.caption("Plan confidently. Execute flawlessly.")
        st.markdown("---")

        # Model Status
        try:
            ollama.list()
            st.success(f"🤖 Ollama Model: `{MODEL_NAME}` (Active)")
        except Exception:
            st.warning("⚠️ Ollama offline — pattern fallback active")

        st.markdown("### 🏫 College Database")

        with st.expander("📦 Equipment Inventory", expanded=False):
            df_eq = pd.DataFrame([
                {"Equipment": k.replace("_", " ").title(), "Stock": v}
                for k, v in EQUIPMENT_INVENTORY.items()
            ])
            st.dataframe(df_eq, hide_index=True, use_container_width=True)

        with st.expander("🏛️ Rooms & Capacity", expanded=False):
            rooms_list = []
            for r, inf in ROOM_DATABASE.items():
                rooms_list.append({
                    "Room": r.replace("_", " ").title(),
                    "Cap": inf["capacity"],
                    "Projector": "Yes" if inf["has_projector"] else "No",
                    "AC": "Yes" if inf["has_ac"] else "No",
                    "Wheelchair": "Yes" if inf["wheelchair_accessible"] else "No",
                })
            st.dataframe(pd.DataFrame(rooms_list), hide_index=True, use_container_width=True)

        with st.expander("👥 Staff Available", expanded=False):
            df_st = pd.DataFrame([
                {"Role": k.replace("_", " ").title(), "Available": v}
                for k, v in STAFF_AVAILABLE.items()
            ])
            st.dataframe(df_st, hide_index=True, use_container_width=True)

        with st.expander("💰 Price List", expanded=False):
            df_pr = pd.DataFrame([
                {"Item": k.replace("_", " ").title(), "Rate (₹)": f"₹{v:,}"}
                for k, v in UNIT_PRICES.items()
            ])
            st.dataframe(df_pr, hide_index=True, use_container_width=True)


# ──────────────────────────────────────
# Main Application Layout
# ──────────────────────────────────────

def main():
    st.set_page_config(
        page_title="EventReady — Pre-Event Failure Detector",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject lightweight scoped styling
    st.markdown(MINIMAL_CSS, unsafe_allow_html=True)

    # Render clean native sidebar
    render_sidebar()

    # Session State
    if "event_plan_text" not in st.session_state:
        st.session_state["event_plan_text"] = ""
    if "assessment_done" not in st.session_state:
        st.session_state["assessment_done"] = False
    if "tool_results" not in st.session_state:
        st.session_state["tool_results"] = None
    if "event_data" not in st.session_state:
        st.session_state["event_data"] = None
    if "suggestions" not in st.session_state:
        st.session_state["suggestions"] = None
    if "readiness" not in st.session_state:
        st.session_state["readiness"] = None
    if "extraction_method" not in st.session_state:
        st.session_state["extraction_method"] = ""

    # ── 1. Header with Event Ready Branding ──
    st.title("🎯 EventReady")
    st.markdown("**Pre-Event Failure Detector** — Validate your event logistics against verified college inventory, venue capacities, staff rosters, and budgets before committing.")
    st.markdown("---")

    # ── 2. Event Input Form ──
    st.subheader("📝 1. Enter Event Plan")
    st.caption("Provide event details in natural language. Mention venue, expected attendance, required equipment, staff roles, accessibility needs, and budget requirements.")

    c_load, c_clear = st.columns([1, 5])
    with c_load:
        if st.button("📋 Load Example Plan", use_container_width=True):
            st.session_state["event_plan_text"] = EXAMPLE_PLAN
            st.rerun()

    event_text = st.text_area(
        label="Event Plan Description",
        value=st.session_state["event_plan_text"],
        height=220,
        placeholder="Type or paste your event description here...",
        help="Include venue, attendees, equipment quantities, staff roles, and accessibility features.",
    )
    st.session_state["event_plan_text"] = event_text

    # ── 3. One Clear Action Button ──
    run_clicked = st.button("🔍 Run Readiness Assessment", type="primary", use_container_width=True)

    if run_clicked:
        if not event_text.strip():
            st.warning("⚠️ Please enter an event plan first or click 'Load Example Plan'.")
            return

        with st.spinner("Analyzing event plan and running verification checks..."):
            # Phase 1: Extract
            event_data = extract_event_data_ai(event_text)
            method = "Ollama Local AI"
            if not event_data or not isinstance(event_data, dict):
                event_data = extract_event_data_regex(event_text)
                method = "Deterministic Regex Fallback"

            # Phase 2: Run all tools
            tool_results = run_all_tools(event_data)

            # Suggestions & Readiness
            suggestions = generate_suggestions(tool_results, event_data)
            readiness = calculate_readiness(tool_results)

            # Save state
            st.session_state["assessment_done"] = True
            st.session_state["tool_results"] = tool_results
            st.session_state["event_data"] = event_data
            st.session_state["suggestions"] = suggestions
            st.session_state["readiness"] = readiness
            st.session_state["extraction_method"] = method

    # Render results if assessment is available
    if st.session_state["assessment_done"] and st.session_state["tool_results"]:
        tool_results = st.session_state["tool_results"]
        event_data = st.session_state["event_data"]
        suggestions = st.session_state["suggestions"]
        readiness = st.session_state["readiness"]
        method = st.session_state["extraction_method"]

        st.markdown("---")

        # ── 4. Prominent Readiness Status Section ──
        st.subheader("📊 2. Event Readiness Status")

        status = readiness["status"]
        if status == "READY":
            st.markdown(
                """<div class="er-banner-ready">
                    <h3 style="color:#2E7D4F; margin:0 0 6px 0;">✅ READY</h3>
                    <p style="margin:0; color:#2E7D4F;">All checks passed against college inventory, venue capacity, and staff availability. Your event is clear to proceed.</p>
                </div>""",
                unsafe_allow_html=True,
            )
        elif status == "READY WITH WARNINGS":
            st.markdown(
                f"""<div class="er-banner-warning">
                    <h3 style="color:#D9822B; margin:0 0 6px 0;">⚠️ READY WITH WARNINGS</h3>
                    <p style="margin:0; color:#8A5400;">The event can proceed, but {len(readiness['warnings'])} non-critical warning(s) require attention.</p>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div class="er-banner-not-ready">
                    <h3 style="color:#C0392B; margin:0 0 6px 0;">❌ NOT READY</h3>
                    <p style="margin:0; color:#96271B;">The event cannot proceed in its current state. <strong>{len(readiness['blockers'])} critical blocker(s)</strong> must be resolved.</p>
                </div>""",
                unsafe_allow_html=True,
            )

        # ── 5. Key Findings Section ──
        st.subheader("📋 3. Key Findings")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Passed Checks", len(readiness["passed"]))
        m2.metric("Critical Blockers", len(readiness["blockers"]))
        m3.metric("Warnings", len(readiness["warnings"]))
        m4.metric("Unrecorded Items", len(readiness["unknowns"]))

        # Blocker & Warning lists
        if readiness["blockers"]:
            with st.container():
                st.markdown("**Critical Blockers:**")
                for b in readiness["blockers"]:
                    st.error(f"🚨 {b}")

        if readiness["warnings"]:
            with st.container():
                st.markdown("**Warnings:**")
                for w in readiness["warnings"]:
                    st.warning(f"⚠️ {w}")

        if readiness["unknowns"]:
            with st.expander("❓ Unrecorded / Unknown Requirements", expanded=False):
                for u in readiness["unknowns"]:
                    st.markdown(f"- {u}")

        st.markdown("---")

        # ── 6. Evidence Section (Actual vs Recorded) ──
        st.subheader("🔍 4. Evidence & Verification Ledger")
        st.caption(f"Requirements extracted via **{method}** and cross-referenced with recorded college databases.")

        # Venue evidence
        if "check_room_capacity" in tool_results:
            r = tool_results["check_room_capacity"]
            st.markdown(f"**Venue Check: `{r.get('room', 'N/A')}`**")
            col_v1, col_v2, col_v3 = st.columns(3)
            col_v1.metric("Room Capacity", f"{r.get('room_capacity', '?')} seats")
            col_v2.metric("Expected Attendees", r.get("expected_attendees", "?"))
            col_v3.metric("Capacity Status", r.get("status", "UNKNOWN"))

            features_str = f"Projector: {'✅ Yes' if r.get('has_projector') else '❌ No'} | AC: {'✅ Yes' if r.get('has_ac') else '❌ No'} | Wheelchair Ramp: {'✅ Yes' if r.get('wheelchair_accessible') else '❌ No'}"
            st.caption(features_str)

        # Equipment & Staffing Tables
        col_eq, col_st = st.columns(2)

        with col_eq:
            st.markdown("##### 🔧 Equipment Verification")
            if "check_resources" in tool_results:
                r_eq = tool_results["check_resources"]
                rows = []
                for it in r_eq.get("available", []):
                    rows.append({"Item": it["item"].replace("_", " ").title(), "Required": it["required"], "In Stock": it["in_stock"], "Status": "PASS"})
                for it in r_eq.get("shortages", []):
                    rows.append({"Item": it["item"].replace("_", " ").title(), "Required": it["required"], "In Stock": it["in_stock"], "Status": f"FAIL (-{it['shortage']})"})
                for it in r_eq.get("unknown", []):
                    rows.append({"Item": it["item"].replace("_", " ").title(), "Required": it.get("required", "?"), "In Stock": "0", "Status": "UNKNOWN"})

                if rows:
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                else:
                    st.info("No equipment items specified.")

        with col_st:
            st.markdown("##### 👥 Staffing Verification")
            if "check_staffing" in tool_results:
                r_st = tool_results["check_staffing"]
                rows_st = []
                for it in r_st.get("covered", []):
                    rows_st.append({"Role": it["role"].replace("_", " ").title(), "Needed": it["needed"], "Available": it["available"], "Status": "PASS"})
                for it in r_st.get("shortages", []):
                    rows_st.append({"Role": it["role"].replace("_", " ").title(), "Needed": it["needed"], "Available": it["available"], "Status": f"FAIL (-{it['shortage']})"})
                for it in r_st.get("unknown", []):
                    rows_st.append({"Role": it["role"].replace("_", " ").title(), "Needed": it.get("needed", "?"), "Available": "0", "Status": "UNKNOWN"})

                if rows_st:
                    st.dataframe(pd.DataFrame(rows_st), hide_index=True, use_container_width=True)
                else:
                    st.info("No staff roles specified.")

        # Accessibility & Budget
        col_acc, col_bg = st.columns(2)

        with col_acc:
            st.markdown("##### ♿ Accessibility Compliance")
            if "check_accessibility" in tool_results:
                r_ac = tool_results["check_accessibility"]
                rows_ac = []
                for it in r_ac.get("met", []):
                    rows_ac.append({"Feature": it["feature"].replace("_", " ").title(), "Status": "PASS (Available)"})
                for it in r_ac.get("not_met", []):
                    rows_ac.append({"Feature": it["feature"].replace("_", " ").title(), "Status": "FAIL (Unavailable)"})
                for it in r_ac.get("unknown", []):
                    rows_ac.append({"Feature": it["feature"].replace("_", " ").title(), "Status": "UNKNOWN"})

                if rows_ac:
                    st.dataframe(pd.DataFrame(rows_ac), hide_index=True, use_container_width=True)
                else:
                    st.info("No accessibility requirements specified.")

        with col_bg:
            st.markdown("##### 💰 Budget Estimate")
            if "calculate_budget" in tool_results:
                r_bg = tool_results["calculate_budget"]
                b_rows = []
                for it in r_bg.get("breakdown", []):
                    b_rows.append({
                        "Item": it["item"].replace("_", " ").title(),
                        "Unit Rate": f"₹{it['unit_price']:,}",
                        "Qty": it["quantity"],
                        "Line Total": f"₹{it['line_total']:,}",
                    })
                if b_rows:
                    st.dataframe(pd.DataFrame(b_rows), hide_index=True, use_container_width=True)
                    st.markdown(f"**Total Estimated Budget:** `₹{r_bg.get('total_cost', 0):,.0f}`")
                else:
                    st.info("No budget items specified.")

        st.markdown("---")

        # ── 7. Simple Next-Actions Section ──
        st.subheader("💡 5. Next Actions & Recommended Fixes")
        if suggestions:
            for idx, s in enumerate(suggestions, 1):
                with st.expander(f"Action {idx}: {s['area']} — {s['issue']}", expanded=True):
                    st.markdown(f"**Identified Issue:** {s['issue']}")
                    st.markdown("**Actionable Fix:**")
                    for fix_line in s["fix"].split("\n"):
                        if fix_line.strip():
                            st.markdown(f"- {fix_line.strip()}")
        else:
            st.success("🎉 No corrective actions needed. All event requirements are fulfilled.")

        # ── 8. Report Download ──
        st.markdown("---")
        report_text = build_report_text(tool_results, event_data, suggestions, readiness)
        st.download_button(
            label="⬇️ Download Official Readiness Report (.md)",
            data=report_text,
            file_name=f"eventready_report_{event_data.get('room_name', 'event')}.md",
            mime="text/markdown",
            use_container_width=True,
            help="Download the complete, timestamped pre-event verification report.",
        )


def run_terminal():
    """Terminal CLI mode when executed directly via `python app.py`."""
    import argparse
    import sys

    # Configure UTF-8 output on Windows terminal
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="EventReady — Pre-Event Failure Detector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--example", action="store_true", help="Run the built-in demo event plan")
    parser.add_argument("--file", type=str, metavar="PATH", help="Path to text file containing event plan")
    parser.add_argument("--ui", action="store_true", help="Launch the Streamlit web dashboard in your browser")
    args = parser.parse_args()

    # Launch web UI if requested
    if args.ui:
        print("Launching Streamlit Web Dashboard...")
        from streamlit.web import cli as stcli
        sys.argv = ["streamlit", "run", __file__]
        sys.exit(stcli.main())

    print()
    print("=" * 72)
    print("  🎯 EventReady — Pre-Event Failure Detector (Terminal Mode)")
    print(f"  Model: {MODEL_NAME}  |  Local AI Engine  |  Zero Cloud Calls")
    print("=" * 72)
    print()

    # Determine event plan text
    if args.example:
        event_text = EXAMPLE_PLAN
        print(">> Using built-in example plan (Python Workshop in Lab 1)\n")
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                event_text = f.read()
            print(f">> Loaded event plan from: {args.file}\n")
        except Exception as e:
            print(f"Error reading file '{args.file}': {e}")
            sys.exit(1)
    else:
        print("Options:")
        print("  [Enter]  Run built-in example demo plan")
        print("  [p]      Paste/type your own custom event plan")
        print("  [u]      Launch Streamlit Web UI")
        try:
            choice = input("\nSelect an option [default: Enter for demo]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = ""

        if choice in ("u", "ui", "web"):
            print("Launching Streamlit Web Dashboard...")
            from streamlit.web import cli as stcli
            sys.argv = ["streamlit", "run", __file__]
            sys.exit(stcli.main())
        elif choice in ("p", "paste", "custom"):
            print("\nPaste your event plan below. Press Ctrl+Z (Windows) or Ctrl+D (Mac/Linux) then Enter when done:")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            event_text = "\n".join(lines).strip()
            if not event_text:
                print("No input provided. Falling back to example plan.\n")
                event_text = EXAMPLE_PLAN
        else:
            event_text = EXAMPLE_PLAN
            print("\n>> Running built-in demo plan (Python Workshop in Lab 1)...\n")

    # Phase 1: Extract
    print("-" * 72)
    print("🧠 Phase 1: Extracting event details...")
    event_data = extract_event_data_ai(event_text)
    method = "Ollama Local AI"
    if not event_data or not isinstance(event_data, dict):
        event_data = extract_event_data_regex(event_text)
        method = "Deterministic Regex Fallback"
    print(f"✓ Extracted via {method}")
    print(f"  - Room: {event_data.get('room_name', '?')}")
    print(f"  - Expected Attendees: {event_data.get('expected_attendees', '?')}")
    print(f"  - Equipment items: {len(event_data.get('equipment', {}))}")
    print(f"  - Staff roles: {len(event_data.get('staff', {}))}")
    print(f"  - Accessibility features: {len(event_data.get('accessibility', []))}")
    print(f"  - Budget items: {len(event_data.get('budget_items', []))}")
    print()

    # Phase 2: Run tools
    print("-" * 72)
    print("🔧 Phase 2: Verifying against college databases...")
    tool_results = run_all_tools(event_data)
    suggestions = generate_suggestions(tool_results, event_data)
    readiness = calculate_readiness(tool_results)

    # Print Readiness Verdict
    print()
    print("=" * 72)
    if readiness["status"] == "READY":
        print("  📊 OVERALL READINESS: ✅ READY")
        print("  All checks passed. The event is clear to proceed!")
    elif readiness["status"] == "READY WITH WARNINGS":
        print("  📊 OVERALL READINESS: ⚠️ READY WITH WARNINGS")
        print(f"  Event can proceed, but {len(readiness['warnings'])} non-critical warning(s) found.")
    else:
        print("  📊 OVERALL READINESS: ❌ NOT READY")
        print(f"  {len(readiness['blockers'])} critical blocker(s) must be resolved before proceeding:")
        for b in readiness["blockers"]:
            print(f"    🚨 {b}")
    print("=" * 72)
    print()

    # Print Findings & Checks
    # 1. Venue
    if "check_room_capacity" in tool_results:
        r = tool_results["check_room_capacity"]
        print("🏫 VENUE CHECK:")
        print(f"   Room: {r.get('room')} (Capacity: {r.get('room_capacity')} | Expected: {r.get('expected_attendees')})")
        print(f"   Status: {r.get('status')}")
        print(f"   Projector: {'Yes' if r.get('has_projector') else 'No'} | AC: {'Yes' if r.get('has_ac') else 'No'} | Accessible: {'Yes' if r.get('wheelchair_accessible') else 'No'}")
        for w in r.get("warnings", []):
            print(f"   ⚠️ Warning: {w}")
        print()

    # 2. Equipment
    if "check_resources" in tool_results:
        r = tool_results["check_resources"]
        print("🔧 EQUIPMENT CHECK:")
        for it in r.get("available", []):
            print(f"   ✅ PASS: {it['item']} — {it['in_stock']} in stock (needed: {it['required']})")
        for it in r.get("shortages", []):
            print(f"   ❌ FAIL: {it['item']} — only {it['in_stock']} in stock, needed: {it['required']} (SHORT by {it['shortage']})")
        for it in r.get("unknown", []):
            print(f"   ❓ UNKNOWN: {it['item']} — not tracked in inventory")
        print()

    # 3. Staffing
    if "check_staffing" in tool_results:
        r = tool_results["check_staffing"]
        print("👥 STAFFING CHECK:")
        for st_it in r.get("covered", []):
            print(f"   ✅ PASS: {st_it['role']} — {st_it['available']} available (needed: {st_it['needed']})")
        for st_it in r.get("shortages", []):
            print(f"   ❌ FAIL: {st_it['role']} — only {st_it['available']} available, needed: {st_it['needed']} (SHORT by {st_it['shortage']})")
        for st_it in r.get("unknown", []):
            print(f"   ❓ UNKNOWN: {st_it['role']} — not tracked in staff roster")
        print()

    # 4. Accessibility
    if "check_accessibility" in tool_results:
        r = tool_results["check_accessibility"]
        print("♿ ACCESSIBILITY CHECK:")
        for ac in r.get("met", []):
            print(f"   ✅ PASS: {ac['feature']} — available")
        for ac in r.get("not_met", []):
            print(f"   ❌ FAIL: {ac['feature']} — NOT AVAILABLE")
        for ac in r.get("unknown", []):
            print(f"   ❓ UNKNOWN: {ac['feature']} — unverified")
        print()

    # 5. Budget
    if "calculate_budget" in tool_results:
        r = tool_results["calculate_budget"]
        print(f"💰 BUDGET ESTIMATE (Total: ₹{r.get('total_cost', 0):,.0f}):")
        for bi in r.get("breakdown", []):
            print(f"   - {bi['item']}: {bi['quantity']} × ₹{bi['unit_price']:,} = ₹{bi['line_total']:,}")
        print()

    # Smart Fix Suggestions
    if suggestions:
        print("💡 SMART FIX RECOMMENDATIONS:")
        for idx, s in enumerate(suggestions, 1):
            print(f"   {idx}. [{s['area']}] Issue: {s['issue']}")
            for fl in s["fix"].split("\n"):
                if fl.strip():
                    print(f"      👉 {fl.strip()}")
        print()

    # Option to save report
    try:
        save = input("Save full report to markdown file? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        save = "n"
    if save == "y":
        fname = f"eventready_report_{event_data.get('room_name', 'event')}.md"
        report_text = build_report_text(tool_results, event_data, suggestions, readiness)
        with open(fname, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"✓ Report successfully saved to: {fname}")
    print()


if __name__ == "__main__":
    if hasattr(st, "runtime") and st.runtime.exists():
        main()
    else:
        run_terminal()

