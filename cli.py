"""
EventReady CLI -- Terminal version of the Pre-Event Failure Detector.

Usage:
    python cli.py                    # interactive -- paste event plan
    python cli.py --file plan.txt    # read plan from a text file
    python cli.py --example          # run the built-in demo plan

The CLI runs the same two-phase logic as the Streamlit app:
  Phase 1 — AI extracts structured data (regex fallback if Ollama is slow)
  Phase 2 — Python tool functions check inventory, capacity, staff, budget
  Report  — Printed directly in the terminal with colour and formatting
"""

import sys
import json
import re
import argparse
import time

import os
import io
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ── Rich imports for beautiful terminal output ──
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.markup import escape

import ollama
from tools import (
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
)

console = Console(force_terminal=True, highlight=False, legacy_windows=False)
MODEL_NAME = "llama3.2:3b"

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


# ─────────────────────────
# Phase 1: Extract event data
# ─────────────────────────

EXTRACTION_PROMPT = """You are a data extractor. Read the event plan and return ONLY a JSON object.
No explanation. No markdown. Only the raw JSON object.

Extract this JSON structure:
{
  "room_name": "<room name, e.g. lab_1>",
  "expected_attendees": <integer>,
  "equipment": {<item>: <qty>, ...},
  "staff": {<role>: <qty>, ...},
  "accessibility": [<feature>, ...],
  "budget_items": [{"item": <key>, "quantity": <integer>}, ...]
}

Known rooms: seminar_hall_a, seminar_hall_b, lab_1, lab_2, classroom_101, classroom_102, auditorium, open_ground
Known equipment: laptops, projectors, microphones, speakers, whiteboards, extension_cords, hdmi_cables, webcams, printers, chairs, tables
Known staff: volunteers, coordinators, technical_support, security, first_aid, registration_desk
Known accessibility: wheelchair_ramps, sign_language_interpreter, hearing_loop, braille_materials, accessible_restrooms, reserved_seating
Known budget keys: refreshments_per_person, certificates_per_person, banners_per_unit, venue_booking_flat, marketing_flat

Return ONLY the JSON."""


def extract_ai(event_text: str) -> dict | None:
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": event_text},
            ],
        )
        content = response.get("message", {}).get("content", "").strip()
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content).strip()
        return json.loads(content)
    except Exception:
        return None


def extract_regex(event_text: str) -> dict:
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
    for item, pat in {
        "laptops": r"(\d+)\s*laptops?",
        "projectors": r"(\d+)\s*projectors?",
        "microphones": r"(\d+)\s*(?:microphones?|mics?)",
        "speakers": r"(\d+)\s*speakers?",
        "extension_cords": r"(\d+)\s*extension\s*cords?",
        "hdmi_cables": r"(\d+)\s*hdmi\s*cables?",
        "chairs": r"(\d+)\s*chairs?",
        "tables": r"(\d+)\s*tables?",
    }.items():
        m = re.search(pat, text)
        if m:
            equipment[item] = int(m.group(1))

    staff = {}
    for role, pat in {
        "volunteers": r"(\d+)\s*volunteers?",
        "coordinators": r"(\d+)\s*coordinators?",
        "technical_support": r"(\d+)\s*technical\s*(?:support)?",
        "security": r"(\d+)\s*security",
        "first_aid": r"(\d+)\s*first\s*aid",
        "registration_desk": r"(\d+)\s*registration",
    }.items():
        m = re.search(pat, text)
        if m:
            staff[role] = int(m.group(1))

    accessibility = []
    for feature, keywords in {
        "wheelchair_ramps": ["wheelchair", "ramp"],
        "accessible_restrooms": ["accessible restroom", "accessible bathroom"],
        "sign_language_interpreter": ["sign language", "interpreter"],
        "hearing_loop": ["hearing loop"],
        "braille_materials": ["braille"],
    }.items():
        if any(kw in text for kw in keywords):
            accessibility.append(feature)

    budget_items = []
    if attendees > 0:
        if any(w in text for w in ["refreshment", "food", "snack"]):
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


# ─────────────────────────
# Phase 2: Run tools
# ─────────────────────────

def run_tool(name: str, func, kwargs: dict) -> dict:
    """Run one tool with live terminal output."""
    console.print(f"  [cyan]▶ Calling[/cyan] [bold]{name}[/bold]...", end=" ")
    start = time.time()
    result = func(**kwargs)
    elapsed = time.time() - start
    console.print(f"[green]✓[/green] [dim]({elapsed:.2f}s)[/dim]")
    return result


def run_all_tools(event_data: dict) -> dict:
    results = {}
    if event_data.get("room_name") and event_data.get("expected_attendees", 0) > 0:
        results["check_room_capacity"] = run_tool(
            "check_room_capacity", check_room_capacity,
            {"room_name": event_data["room_name"], "expected_attendees": event_data["expected_attendees"]},
        )
    if event_data.get("equipment"):
        results["check_resources"] = run_tool(
            "check_resources", check_resources,
            {"required_items": event_data["equipment"]},
        )
    if event_data.get("staff"):
        results["check_staffing"] = run_tool(
            "check_staffing", check_staffing,
            {"roles_needed": event_data["staff"]},
        )
    if event_data.get("accessibility"):
        results["check_accessibility"] = run_tool(
            "check_accessibility", check_accessibility,
            {"requirements": event_data["accessibility"]},
        )
    if event_data.get("budget_items"):
        results["calculate_budget"] = run_tool(
            "calculate_budget", calculate_budget,
            {"items": event_data["budget_items"]},
        )
    return results


# ─────────────────────────
# Terminal report renderer
# ─────────────────────────

def print_report(tool_results: dict, event_data: dict, suggestions: list):

    # ── Venue ──
    if "check_room_capacity" in tool_results:
        r = tool_results["check_room_capacity"]
        status = r.get("status", "UNKNOWN")
        color = "green" if status == "OK" else ("yellow" if status == "NEAR_CAPACITY" else "red")
        icon  = "✅" if status == "OK" else ("⚠️ " if status == "NEAR_CAPACITY" else "❌")

        t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
        t.add_column("Detail", style="bold")
        t.add_column("Value")
        t.add_row("Room", f"[bold]{r.get('room', 'N/A')}[/bold]")
        t.add_row("Capacity", str(r.get("room_capacity", "?")))
        t.add_row("Expected Attendees", str(r.get("expected_attendees", "?")))
        t.add_row("Status", f"[{color}]{icon} {status}[/{color}]")
        t.add_row("Projector", "✅" if r.get("has_projector") else "❌")
        t.add_row("AC", "✅" if r.get("has_ac") else "❌")
        t.add_row("Wheelchair Access", "✅" if r.get("wheelchair_accessible") else "❌")
        console.print(Panel(t, title="[bold]🏫 VENUE CHECK[/bold]", border_style=color))
        for w in r.get("warnings", []):
            console.print(f"  [yellow]⚠️  {w}[/yellow]")

    # ── Equipment ──
    if "check_resources" in tool_results:
        r = tool_results["check_resources"]
        t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
        t.add_column("Item", style="bold")
        t.add_column("Required", justify="right")
        t.add_column("In Stock", justify="right")
        t.add_column("Status")
        for item in r.get("available", []):
            t.add_row(item["item"], str(item["required"]), str(item["in_stock"]), "[green]✅ OK[/green]")
        for item in r.get("shortages", []):
            t.add_row(
                item["item"],
                str(item["required"]),
                f"[red]{item['in_stock']}[/red]",
                f"[red]❌ SHORT by {item['shortage']}[/red]",
            )
        for item in r.get("unknown", []):
            t.add_row(item["item"], str(item["required"]), "?", "[yellow]❓ UNKNOWN[/yellow]")
        console.print(Panel(t, title="[bold]🔧 EQUIPMENT CHECK[/bold]", border_style="cyan"))

    # ── Staffing ──
    if "check_staffing" in tool_results:
        r = tool_results["check_staffing"]
        t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
        t.add_column("Role", style="bold")
        t.add_column("Needed", justify="right")
        t.add_column("Available", justify="right")
        t.add_column("Status")
        for item in r.get("covered", []):
            t.add_row(item["role"], str(item["needed"]), str(item["available"]), "[green]✅ OK[/green]")
        for item in r.get("shortages", []):
            t.add_row(
                item["role"],
                str(item["needed"]),
                f"[red]{item['available']}[/red]",
                f"[red]❌ SHORT by {item['shortage']}[/red]",
            )
        for item in r.get("unknown", []):
            t.add_row(item["role"], str(item["needed"]), "?", "[yellow]❓ UNKNOWN[/yellow]")
        console.print(Panel(t, title="[bold]👥 STAFFING CHECK[/bold]", border_style="cyan"))

    # ── Accessibility ──
    if "check_accessibility" in tool_results:
        r = tool_results["check_accessibility"]
        t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
        t.add_column("Feature", style="bold")
        t.add_column("Status")
        for item in r.get("met", []):
            t.add_row(item["feature"].replace("_", " ").title(), "[green]✅ Available[/green]")
        for item in r.get("not_met", []):
            t.add_row(item["feature"].replace("_", " ").title(), "[red]❌ NOT AVAILABLE[/red]")
        for item in r.get("unknown", []):
            t.add_row(item["feature"].replace("_", " ").title(), "[yellow]❓ Unknown[/yellow]")
        console.print(Panel(t, title="[bold]♿ ACCESSIBILITY CHECK[/bold]", border_style="cyan"))

    # ── Budget ──
    if "calculate_budget" in tool_results:
        r = tool_results["calculate_budget"]
        t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
        t.add_column("Item", style="bold")
        t.add_column("Unit Price", justify="right")
        t.add_column("Qty", justify="right")
        t.add_column("Line Total", justify="right")
        for item in r.get("breakdown", []):
            t.add_row(
                item["item"],
                f"₹{item['unit_price']:,}",
                str(item["quantity"]),
                f"[bold]₹{item['line_total']:,}[/bold]",
            )
        for item in r.get("unknown_items", []):
            t.add_row(f"[yellow]{item['item']}[/yellow]", "?", "?", "[yellow]UNKNOWN[/yellow]")
        console.print(Panel(t, title="[bold]💰 BUDGET ESTIMATE[/bold]", border_style="cyan"))
        total = r.get("total_cost", 0)
        console.print(f"  [bold green]💵 TOTAL ESTIMATED COST: ₹{total:,.0f}[/bold green]\n")

    # ── Suggestions ──
    if suggestions:
        console.print(Rule("[bold yellow]💡 SMART FIX SUGGESTIONS[/bold yellow]"))
        for i, s in enumerate(suggestions, 1):
            console.print(f"\n  [bold]{i}. {s['area']}[/bold]")
            console.print(f"  [red]Issue:[/red] {escape(s['issue'])}")
            console.print("  [green]Fix:[/green]")
            for line in s["fix"].split("\n"):
                if line.strip():
                    console.print(f"    {escape(line)}")
        console.print()

    # ── Verdict ──
    console.print(Rule())
    all_shortages = []
    for key in ["check_resources", "check_staffing"]:
        if key in tool_results:
            all_shortages += tool_results[key].get("shortages", [])
    room_over = tool_results.get("check_room_capacity", {}).get("status") == "OVER_CAPACITY"
    access_missing = []
    if "check_accessibility" in tool_results:
        access_missing = tool_results["check_accessibility"].get("not_met", [])
    critical = all_shortages + access_missing + ([{"item": "venue over capacity"}] if room_over else [])

    if not critical:
        console.print(Panel(
            "[bold green]✅ All checks passed. Your event is good to go! 🎉[/bold green]",
            title="[bold green]📊 OVERALL READINESS: READY[/bold green]",
            border_style="green",
        ))
    else:
        issues_text = "\n".join(
            f"  🚨 [bold]{p.get('item') or p.get('role') or p.get('feature', '?')}[/bold]"
            + (f" — short by {p['shortage']}" if p.get("shortage") else " — unavailable/over capacity")
            for p in critical
        )
        console.print(Panel(
            f"[red]{len(critical)} critical issue(s) must be resolved:[/red]\n\n{issues_text}",
            title="[bold red]📊 OVERALL READINESS: ❌ NOT READY[/bold red]",
            border_style="red",
        ))


# ───────────────────────────
# Interactive input collector
# ───────────────────────────

def get_interactive_input() -> str:
    console.print(Panel(
        "[bold cyan]Paste or type your event plan below.[/bold cyan]\n"
        "Include: venue, attendees, equipment, staff, accessibility, budget.\n\n"
        "[dim]When done, press [bold]Enter[/bold] then [bold]Ctrl+Z[/bold] (Windows) "
        "or [bold]Ctrl+D[/bold] (Mac/Linux) and [bold]Enter[/bold] to submit.[/dim]",
        title="📝 Enter Your Event Plan",
        border_style="cyan",
    ))
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines)


# ─────────────
# Main entry
# ─────────────

def main():
    parser = argparse.ArgumentParser(
        description="EventReady — Pre-Event Failure Detector (CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python cli.py                   Interactive mode — paste your plan
  python cli.py --example         Run the built-in demo plan
  python cli.py --file plan.txt   Read plan from a text file
""",
    )
    parser.add_argument("--example", action="store_true", help="Run the built-in demo event plan")
    parser.add_argument("--file", type=str, metavar="PATH", help="Path to a text file containing the event plan")
    args = parser.parse_args()

    # ── Banner ──
    console.print()
    console.print(Panel(
        "[bold white]EventReady -- Pre-Event Failure Detector[/bold white]\n"
        f"[dim]Model: {MODEL_NAME}  |  All checks run locally  |  No cloud APIs[/dim]",
        border_style="bright_blue",
        padding=(1, 4),
    ))
    console.print()

    # ── Get event plan text ──
    if args.example:
        event_text = EXAMPLE_PLAN
        console.print("[bold green]>> Using built-in example plan[/bold green]\n")
        console.print(Panel(event_text, title="📋 Event Plan", border_style="dim"))
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                event_text = f.read()
            console.print(f"[bold green]>> Loaded plan from:[/bold green] {args.file}\n")
            console.print(Panel(event_text, title="Event Plan", border_style="dim"))
        except FileNotFoundError:
            console.print(f"[red]File not found: {args.file}[/red]")
            sys.exit(1)
    else:
        event_text = get_interactive_input()

    if not event_text.strip():
        console.print("[red]No event plan provided. Exiting.[/red]")
        sys.exit(1)

    console.print()
    console.print(Rule("[bold]Phase 1 -- Extracting Event Details[/bold]"))

    # ── Phase 1: Extract ──
    with console.status("[cyan]Analysing your event plan via AI...[/cyan]"):
        event_data = extract_ai(event_text)
        method = "AI"

    if not event_data or not isinstance(event_data, dict):
        console.print("  [yellow]AI extraction failed -- using pattern-based extraction[/yellow]")
        event_data = extract_regex(event_text)
        method = "Pattern"
    else:
        console.print(f"  [green]✓[/green] Extracted via {method}")

    # Print extracted summary
    t = Table(box=box.SIMPLE, show_header=False)
    t.add_column("Key", style="bold cyan")
    t.add_column("Value")
    t.add_row("Room", event_data.get("room_name", "?"))
    t.add_row("Attendees", str(event_data.get("expected_attendees", "?")))
    t.add_row("Equipment items", str(len(event_data.get("equipment", {}))))
    t.add_row("Staff roles", str(len(event_data.get("staff", {}))))
    t.add_row("Accessibility checks", str(len(event_data.get("accessibility", []))))
    t.add_row("Budget items", str(len(event_data.get("budget_items", []))))
    console.print(t)

    # ── Phase 2: Run tools ──
    console.print()
    console.print(Rule("[bold]Phase 2 -- Running Checks[/bold]"))
    tool_results = run_all_tools(event_data)

    # ── Suggestions ──
    suggestions = generate_suggestions(tool_results, event_data)

    # ── Print report ──
    console.print()
    console.print(Rule("[bold bright_blue]READINESS REPORT[/bold bright_blue]"))
    console.print()
    print_report(tool_results, event_data, suggestions)

    # ── Save report option ──
    console.print()
    save = console.input("Save report to file? (y/N): ").strip().lower()
    if save == "y":
        filename = f"report_{event_data.get('room_name', 'event')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"EventReady — Readiness Report\n")
            f.write(f"Room: {event_data.get('room_name')} | Attendees: {event_data.get('expected_attendees')}\n\n")
            for key, result in tool_results.items():
                f.write(f"\n[{key}]\n{json.dumps(result, indent=2)}\n")
            if suggestions:
                f.write("\n[SUGGESTIONS]\n")
                for i, s in enumerate(suggestions, 1):
                    f.write(f"\n{i}. {s['area']}\nIssue: {s['issue']}\nFix: {s['fix']}\n")
        console.print(f"[green]Report saved to[/green] [bold]{filename}[/bold]")

    console.print()


if __name__ == "__main__":
    main()
