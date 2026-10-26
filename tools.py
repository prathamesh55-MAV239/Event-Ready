"""
EventReady — Tool Functions
Deterministic Python functions that the AI model can call via tool-use.
Each function operates on hardcoded inventory data (hackathon demo).
No guessing — if a resource is not in inventory, it is reported as UNKNOWN.
"""

# ──────────────────────────────────────────────
# Simulated college inventory / pricing database
# ──────────────────────────────────────────────

EQUIPMENT_INVENTORY = {
    "laptops": 32,
    "projectors": 4,
    "microphones": 6,
    "speakers": 8,
    "whiteboards": 10,
    "extension_cords": 20,
    "hdmi_cables": 15,
    "webcams": 5,
    "printers": 2,
    "chairs": 200,
    "tables": 50,
}

ROOM_DATABASE = {
    "seminar_hall_a": {"capacity": 120, "has_projector": True, "has_ac": True, "wheelchair_accessible": True},
    "seminar_hall_b": {"capacity": 80, "has_projector": True, "has_ac": True, "wheelchair_accessible": True},
    "lab_1": {"capacity": 40, "has_projector": False, "has_ac": True, "wheelchair_accessible": False},
    "lab_2": {"capacity": 35, "has_projector": True, "has_ac": True, "wheelchair_accessible": True},
    "classroom_101": {"capacity": 60, "has_projector": True, "has_ac": False, "wheelchair_accessible": True},
    "classroom_102": {"capacity": 50, "has_projector": False, "has_ac": True, "wheelchair_accessible": False},
    "auditorium": {"capacity": 300, "has_projector": True, "has_ac": True, "wheelchair_accessible": True},
    "open_ground": {"capacity": 500, "has_projector": False, "has_ac": False, "wheelchair_accessible": True},
}

STAFF_AVAILABLE = {
    "volunteers": 15,
    "coordinators": 4,
    "technical_support": 3,
    "security": 5,
    "first_aid": 2,
    "registration_desk": 4,
}

UNIT_PRICES = {
    "laptops_rental_per_unit": 500,
    "projectors_rental_per_unit": 1000,
    "microphones_rental_per_unit": 300,
    "speakers_rental_per_unit": 400,
    "chairs_rental_per_unit": 50,
    "tables_rental_per_unit": 150,
    "banners_per_unit": 800,
    "refreshments_per_person": 150,
    "certificates_per_person": 30,
    "venue_booking_flat": 5000,
    "marketing_flat": 2000,
}

ACCESSIBILITY_FEATURES = {
    "wheelchair_ramps": True,
    "sign_language_interpreter": False,
    "hearing_loop": False,
    "braille_materials": False,
    "accessible_restrooms": True,
    "reserved_seating": True,
    "screen_reader_compatible_materials": False,
}


# ──────────────────────────
# Tool function definitions
# ──────────────────────────

def calculate_budget(items: list) -> dict:
    """
    Calculate total estimated budget from a list of cost items.

    Accepts items as:
      - dicts:  {"item": "refreshments_per_person", "quantity": 45}
      - strings: "refreshments_per_person:45"  or  "refreshments_per_person"

    Returns:
        dict with "breakdown" (list), "total_cost" (float),
        and "unknown_items" (list) for items not in the price database.
    """
    breakdown = []
    unknown_items = []
    total = 0.0

    for entry in items:
        # ── Normalise to (item_name, quantity) regardless of input format ──
        if isinstance(entry, dict):
            item_name = str(entry.get("item", "") or entry.get("name", "")).strip().lower()
            quantity = entry.get("quantity", entry.get("qty", 1))
        elif isinstance(entry, str):
            # Support "item_name:qty" or just "item_name"
            if ":" in entry:
                parts = entry.split(":", 1)
                item_name = parts[0].strip().lower()
                try:
                    quantity = int(parts[1].strip())
                except ValueError:
                    quantity = 1
            else:
                item_name = entry.strip().lower()
                quantity = 1
        else:
            unknown_items.append({"item": str(entry), "reason": "Unrecognised format"})
            continue

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1

        if quantity < 0:
            unknown_items.append({"item": item_name, "reason": "Invalid quantity"})
            continue

        if item_name in UNIT_PRICES:
            cost = UNIT_PRICES[item_name] * quantity
            breakdown.append({
                "item": item_name,
                "unit_price": UNIT_PRICES[item_name],
                "quantity": quantity,
                "line_total": cost,
            })
            total += cost
        else:
            unknown_items.append({
                "item": item_name,
                "reason": "UNKNOWN — not found in pricing database",
            })

    return {
        "breakdown": breakdown,
        "total_cost": total,
        "unknown_items": unknown_items,
    }


def check_resources(required_items: dict) -> dict:
    """
    Compare required equipment against available inventory.

    Args:
        required_items: dict mapping equipment name (str) to quantity needed (int).
                        Example: {"laptops": 40, "projectors": 2}

    Returns:
        dict with "available" items, "shortages", and "unknown" items.
    """
    results = {"available": [], "shortages": [], "unknown": []}

    for item_name, qty_needed in required_items.items():
        item_key = str(item_name).strip().lower()
        qty_needed = int(qty_needed)

        if item_key in EQUIPMENT_INVENTORY:
            qty_have = EQUIPMENT_INVENTORY[item_key]
            if qty_have >= qty_needed:
                results["available"].append({
                    "item": item_key,
                    "required": qty_needed,
                    "in_stock": qty_have,
                    "status": "OK",
                })
            else:
                results["shortages"].append({
                    "item": item_key,
                    "required": qty_needed,
                    "in_stock": qty_have,
                    "shortage": qty_needed - qty_have,
                    "status": "SHORTAGE",
                })
        else:
            results["unknown"].append({
                "item": item_key,
                "required": qty_needed,
                "status": "UNKNOWN — not tracked in inventory",
            })

    return results


def check_room_capacity(room_name: str, expected_attendees: int) -> dict:
    """
    Check if a room can accommodate the expected number of attendees.

    Args:
        room_name: Name of the room (must match a key in ROOM_DATABASE).
        expected_attendees: Number of people expected.

    Returns:
        dict with room info, capacity verdict, and any warnings.
    """
    room_key = str(room_name).strip().lower().replace(" ", "_")
    expected_attendees = int(expected_attendees)

    if room_key not in ROOM_DATABASE:
        available_rooms = list(ROOM_DATABASE.keys())
        return {
            "status": "UNKNOWN",
            "message": f"Room '{room_name}' not found in database.",
            "available_rooms": available_rooms,
        }

    room = ROOM_DATABASE[room_key]
    capacity = room["capacity"]
    warnings = []

    if expected_attendees > capacity:
        status = "OVER_CAPACITY"
        warnings.append(
            f"Room can hold {capacity} but {expected_attendees} expected. "
            f"Overflow of {expected_attendees - capacity} people."
        )
    elif expected_attendees > capacity * 0.9:
        status = "NEAR_CAPACITY"
        warnings.append(f"Room will be at {round(expected_attendees/capacity*100)}% capacity — tight fit.")
    else:
        status = "OK"

    if not room.get("has_ac") and expected_attendees > 30:
        warnings.append("No AC in this room — may be uncomfortable for large groups.")

    return {
        "room": room_key,
        "room_capacity": capacity,
        "expected_attendees": expected_attendees,
        "has_projector": room["has_projector"],
        "has_ac": room["has_ac"],
        "wheelchair_accessible": room["wheelchair_accessible"],
        "status": status,
        "warnings": warnings,
    }


def check_staffing(roles_needed: dict) -> dict:
    """
    Compare required staff roles against available staff.

    Args:
        roles_needed: dict mapping role name (str) to count needed (int).
                      Example: {"volunteers": 20, "technical_support": 2}

    Returns:
        dict with "covered" roles, "shortages", and "unknown" roles.
    """
    results = {"covered": [], "shortages": [], "unknown": []}

    for role, qty_needed in roles_needed.items():
        role_key = str(role).strip().lower().replace(" ", "_")
        qty_needed = int(qty_needed)

        if role_key in STAFF_AVAILABLE:
            qty_have = STAFF_AVAILABLE[role_key]
            if qty_have >= qty_needed:
                results["covered"].append({
                    "role": role_key,
                    "needed": qty_needed,
                    "available": qty_have,
                    "status": "OK",
                })
            else:
                results["shortages"].append({
                    "role": role_key,
                    "needed": qty_needed,
                    "available": qty_have,
                    "shortage": qty_needed - qty_have,
                    "status": "SHORTAGE",
                })
        else:
            results["unknown"].append({
                "role": role_key,
                "needed": qty_needed,
                "status": "UNKNOWN — role not in staff database",
            })

    return results


def check_accessibility(requirements: list) -> dict:
    """
    Check which accessibility features are available vs missing.

    Args:
        requirements: List of accessibility feature names (strings).
                      Example: ["wheelchair_ramps", "sign_language_interpreter"]

    Returns:
        dict with "met" requirements, "not_met", and "unknown" features.
    """
    results = {"met": [], "not_met": [], "unknown": []}

    for req in requirements:
        req_key = str(req).strip().lower().replace(" ", "_")

        if req_key in ACCESSIBILITY_FEATURES:
            if ACCESSIBILITY_FEATURES[req_key]:
                results["met"].append({"feature": req_key, "status": "AVAILABLE"})
            else:
                results["not_met"].append({"feature": req_key, "status": "NOT AVAILABLE"})
        else:
            results["unknown"].append({
                "feature": req_key,
                "status": "UNKNOWN — not tracked",
            })

    return results


# ──────────────────────────────────
# Smart Suggestions Engine
# ──────────────────────────────────

def generate_suggestions(tool_results: dict, event_data: dict) -> list:
    """
    Analyse tool results and produce a list of actionable fix suggestions.
    Each suggestion is a dict with keys: 'area', 'issue', 'fix'.
    """
    suggestions = []
    attendees = event_data.get("expected_attendees", 0)

    # ── Room suggestions ──
    if "check_room_capacity" in tool_results:
        r = tool_results["check_room_capacity"]
        status = r.get("status", "")
        if status in ("OVER_CAPACITY", "NEAR_CAPACITY"):
            overflow = attendees - r.get("room_capacity", 0)
            current_room = r.get("room", "")
            # Find all rooms big enough
            alternatives = [
                (name, info["capacity"])
                for name, info in ROOM_DATABASE.items()
                if info["capacity"] >= attendees and name != current_room
            ]
            alternatives.sort(key=lambda x: x[1])  # smallest suitable first
            if alternatives:
                alt_list = ", ".join(
                    f"`{name}` (cap: {cap})" for name, cap in alternatives[:3]
                )
                suggestions.append({
                    "area": "🏫 Venue",
                    "issue": f"`{current_room}` is {'over' if status=='OVER_CAPACITY' else 'near'} capacity "
                             f"({r.get('room_capacity',0)} seats, {attendees} expected)",
                    "fix": f"Switch to a larger room → {alt_list}",
                })
            else:
                suggestions.append({
                    "area": "🏫 Venue",
                    "issue": f"`{current_room}` cannot fit {attendees} attendees.",
                    "fix": f"Reduce attendees to {r.get('room_capacity',0)} OR arrange an outdoor venue.",
                })

        if not r.get("has_projector"):
            suggestions.append({
                "area": "🏫 Venue",
                "issue": f"`{r.get('room', '')}` has no built-in projector.",
                "fix": "Bring a portable projector from inventory (4 available).",
            })

    # ── Equipment shortage suggestions ──
    if "check_resources" in tool_results:
        r = tool_results["check_resources"]
        for item in r.get("shortages", []):
            shortage = item["shortage"]
            name = item["item"]
            in_stock = item["in_stock"]
            suggestions.append({
                "area": "🔧 Equipment",
                "issue": f"Only {in_stock} `{name}` in stock, {item['required']} needed (short by {shortage}).",
                "fix": (
                    f"Option A: Rent {shortage} extra `{name}` from external vendor.\n"
                    f"Option B: Reduce requirement — limit participants to {in_stock} for `{name}`-heavy activities.\n"
                    f"Option C: Split the event into batches of {in_stock}."
                ),
            })

    # ── Staffing shortage suggestions ──
    if "check_staffing" in tool_results:
        r = tool_results["check_staffing"]
        for item in r.get("shortages", []):
            shortage = item["shortage"]
            role = item["role"]
            suggestions.append({
                "area": "👥 Staffing",
                "issue": f"Only {item['available']} `{role}` available, {item['needed']} needed (short by {shortage}).",
                "fix": (
                    f"Option A: Recruit {shortage} more `{role.replace('_',' ')}` before the event.\n"
                    f"Option B: Cross-train existing staff to cover `{role.replace('_',' ')}` duties.\n"
                    f"Option C: Reduce the number of `{role.replace('_',' ')}` tasks."
                ),
            })

    # ── Accessibility suggestions ──
    if "check_accessibility" in tool_results:
        r = tool_results["check_accessibility"]
        fix_map = {
            "sign_language_interpreter": "Hire a certified sign language interpreter (contact local disability services).",
            "hearing_loop": "Rent a portable hearing loop system for the event duration.",
            "braille_materials": "Print event materials in Braille at least 1 week before the event.",
            "screen_reader_compatible_materials": "Convert all presentation materials to screen-reader-friendly formats (PDF/DOCX).",
        }
        for item in r.get("not_met", []):
            feature = item["feature"]
            suggestions.append({
                "area": "♿ Accessibility",
                "issue": f"`{feature.replace('_',' ').title()}` is NOT available.",
                "fix": fix_map.get(
                    feature,
                    f"Arrange `{feature.replace('_',' ')}` before the event day.",
                ),
            })

    # ── Budget suggestions ──
    if "calculate_budget" in tool_results:
        r = tool_results["calculate_budget"]
        total = r.get("total_cost", 0)
        if total > 20000:
            suggestions.append({
                "area": "💰 Budget",
                "issue": f"Total estimated cost ₹{total:,.0f} may be high.",
                "fix": (
                    "Option A: Reduce refreshment cost by choosing in-house catering.\n"
                    "Option B: Use digital certificates instead of printed ones (saves ₹"
                    f"{30 * event_data.get('expected_attendees', 0):,}).\n"
                    "Option C: Reduce banner count or use reusable banners."
                ),
            })

    return suggestions


# ──────────────────────────
# Tool registry for app.py
# ──────────────────────────

TOOL_REGISTRY = {
    "calculate_budget": calculate_budget,
    "check_resources": check_resources,
    "check_room_capacity": check_room_capacity,
    "check_staffing": check_staffing,
    "check_accessibility": check_accessibility,
}

