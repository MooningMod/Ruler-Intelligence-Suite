from typing import TYPE_CHECKING

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QFont, QPainter

from tech_effects import apply_techs_to_unit

if TYPE_CHECKING:
    from overlay_ins_menu import OverlayINS


# -------------------------------------------------------------------------
# UNIT LIST 
# -------------------------------------------------------------------------
def draw_unit_list(ov: "OverlayINS", p: QPainter) -> None:
    p.setClipRect(ov.unit_list_rect)
    start = ov.unit_scroll_offset
    rows = ov.unit_list_rect.height() // ov.line_height
    y = ov.unit_list_rect.top()

    p.setFont(QFont("Consolas", 9))
    for i in range(start, min(len(ov.filtered_units), start + rows + 1)):
        u = ov.filtered_units[i]
        r = QRect(ov.unit_list_rect.left(), y, ov.unit_list_rect.width(), ov.line_height)

        if u == ov.selected_unit_b:
            p.fillRect(r, QColor(0, 100, 255, 80))
        if u == ov.selected_unit_c:
            p.fillRect(r, QColor(255, 160, 0, 80))
        if u == ov.selected_unit_d:
            p.fillRect(r, QColor(80, 200, 130, 80))

        p.setPen(QColor(150, 150, 150))
        p.drawText(r.left() + 4, r.bottom() - 4, str(u.id))
        p.setPen(Qt.white)
        p.drawText(r.left() + 55, r.bottom() - 4, u.name[:60])
        y += ov.line_height

    p.setClipping(False)


# -------------------------------------------------------------------------
# MAIN TABLE AREA (compare / tech impact)
# -------------------------------------------------------------------------
def draw_comparison_table(ov: "OverlayINS", p: QPainter, rect: QRect) -> None:
    y = rect.top() + 10
    label_w = 140
    rest_w = rect.width() - label_w
    col_w = rest_w // 3

    x_label = rect.left()
    x_b = x_label + label_w
    x_c = x_b + col_w
    x_d = x_c + col_w

    # Tabs
    tab_h = 18
    tab_w = 90
    tab_y = rect.top() + 4

    ov.tab_compare_rect = QRect(rect.left() + 6, tab_y, tab_w, tab_h)
    ov.tab_tech_rect = QRect(rect.left() + 6 + tab_w + 4, tab_y, tab_w, tab_h)

    p.setFont(QFont("Segoe UI", 8, QFont.Bold))

    # COMPARE tab
    p.setBrush(QColor(60, 60, 80) if ov.view_mode == "compare" else QColor(30, 30, 40))
    p.setPen(Qt.NoPen)
    p.drawRect(ov.tab_compare_rect)
    p.setPen(QColor(230, 230, 230))
    p.drawText(ov.tab_compare_rect, Qt.AlignCenter, "COMPARE")

    # TECH IMPACT tab
    p.setBrush(QColor(60, 60, 80) if ov.view_mode == "tech_impact" else QColor(30, 30, 40))
    p.setPen(Qt.NoPen)
    p.drawRect(ov.tab_tech_rect)
    p.setPen(QColor(230, 230, 230))
    p.drawText(ov.tab_tech_rect, Qt.AlignCenter, "TECH IMPACT")

    # Unit names B/C/D
    y = tab_y + tab_h + 4
    p.setFont(QFont("Segoe UI", 9, QFont.Bold))

    name_b = ov.selected_unit_b.name if ov.selected_unit_b else "Unit B (LMB)"
    name_c = ov.selected_unit_c.name if ov.selected_unit_c else "Unit C (RMB)"
    name_d = ov.selected_unit_d.name if ov.selected_unit_d else "Unit D (MMB)"

    p.setPen(QColor(120, 200, 255))
    p.drawText(QRect(x_b, y, col_w, 32), Qt.AlignCenter | Qt.TextWordWrap, name_b)
    p.setPen(QColor(255, 180, 90))
    p.drawText(QRect(x_c, y, col_w, 32), Qt.AlignCenter | Qt.TextWordWrap, name_c)
    p.setPen(QColor(150, 230, 170))
    p.drawText(QRect(x_d, y, col_w, 32), Qt.AlignCenter | Qt.TextWordWrap, name_d)

    # Control buttons
    controls_y = y + 32
    btn_h = 18
    btn_w = 90

    p.setFont(QFont("Segoe UI", 8, QFont.Bold))

    ov.btn_lock_rect = QRect(x_b + (col_w - btn_w) // 2, controls_y, btn_w, btn_h)
    p.setBrush(QColor(0, 120, 220) if ov.lock_b else QColor(40, 40, 40))
    p.drawRect(ov.btn_lock_rect)
    p.setPen(Qt.white)
    p.drawText(ov.btn_lock_rect, Qt.AlignCenter, "LOCK B")

    ov.btn_b_to_c_rect = QRect(x_c + (col_w - btn_w) // 2, controls_y, btn_w, btn_h)
    p.setBrush(QColor(40, 40, 40))
    p.drawRect(ov.btn_b_to_c_rect)
    p.drawText(ov.btn_b_to_c_rect, Qt.AlignCenter, "B → C")

    ov.btn_c_to_d_rect = QRect(x_d + (col_w - btn_w) // 2, controls_y, btn_w, btn_h)
    p.setBrush(QColor(40, 40, 40))
    p.drawRect(ov.btn_c_to_d_rect)
    p.drawText(ov.btn_c_to_d_rect, Qt.AlignCenter, "C → D")

    y = controls_y + btn_h + 4
    
    # 🔻 HOTFIX PERFORMANCE SEARCH
    if ov.focus_search and ov.view_mode == "compare":
        return

    # Tech list B/C/D
    ov.tech_checkbox_rects = {"b": {}, "c": {}, "d": {}}
    p.setFont(QFont("Consolas", 9))

    max_tech_rows = 0

    def draw_tech_column(unit, key: str, col_x: int):
        nonlocal max_tech_rows
        if not unit or not unit.tech_ids:
            return
        row_y = y
        for tid in unit.tech_ids:
            short = ov.tech_light.get(tid, {}).get("short_title", "") or f"Tech {tid}"

            box = QRect(col_x + 4, row_y, 12, 12)
            ov.tech_checkbox_rects[key][tid] = box

            p.setPen(QColor(200, 200, 200))
            p.setBrush(QColor(40, 40, 40))
            p.drawRect(box)

            if tid in ov.active_techs.get(key, set()):
                p.drawLine(box.left() + 2, box.center().y(), box.center().x(), box.bottom() - 2)
                p.drawLine(box.center().x(), box.bottom() - 2, box.right() - 2, box.top() + 2)

            p.setPen(QColor(200, 200, 200))
            p.drawText(
                QRect(box.right() + 4, row_y - 2, col_w - 20, 16),
                Qt.AlignLeft | Qt.AlignVCenter,
                short,
            )
            row_y += 16

        max_tech_rows = max(max_tech_rows, (row_y - y) // 16)

    draw_tech_column(ov.selected_unit_b, "b", x_b)
    draw_tech_column(ov.selected_unit_c, "c", x_c)
    draw_tech_column(ov.selected_unit_d, "d", x_d)

    y += max_tech_rows * 16 + 6

    # Separator
    p.setPen(QColor(70, 70, 80))
    p.drawLine(rect.left() + 4, y, rect.right() - 4, y)
    y += 4

    # TECH IMPACT MODE
    if ov.view_mode == "tech_impact":
        _draw_tech_impact_view(ov, p, rect, y)
        return

    _draw_compare_stats_table(ov, p, rect, x_label, x_b, x_c, x_d, col_w, y)


def _draw_compare_stats_table(
    ov: "OverlayINS",
    p: QPainter,
    rect: QRect,
    x_label: int,
    x_b: int,
    x_c: int,
    x_d: int,
    col_w: int,
    start_y: int,
) -> None:
    """
    Tabella di confronto B/C/D con valori tecnici modificati in verde.
    Ottimizzata, compatta, scrollabile.
    """

    label_w = 140
    row_h = 20

    # ---- Boolean fields ---------------------------------------
    bool_fields = {
        "nbc", "ecm", "indirect_fire", "ballistic_art",
        "no_eff_loss_move", "ftl", "survey", "river_xing",
        "airdrop", "air_tanker", "air_refuel", "amph",
        "bridge_build", "engineering", "stand_off",
        "move_fire_penalty", "no_land_cap", "has_production",
    }

    # ---- Helper formatting -------------------------------------
    def fmt(u, attr, rng_attr=None):
        if not u or not attr:
            return "-"

        v = getattr(u, attr, None)

        if attr in bool_fields:
            return "✔" if v else ""

        if isinstance(v, float):
            txt = f"{v:.2f}".rstrip("0").rstrip(".")
        else:
            txt = str(v)

        if rng_attr:
            r = getattr(u, rng_attr, 0)
            if r:
                txt += f" ({r} km)"

        return txt

    # ------ Apply tech effects ----------------------------------
    ub = apply_techs_to_unit(ov.selected_unit_b, ov.active_techs["b"], ov.tech_light)
    uc = apply_techs_to_unit(ov.selected_unit_c, ov.active_techs["c"], ov.tech_light)
    ud = apply_techs_to_unit(ov.selected_unit_d, ov.active_techs["d"], ov.tech_light)

    # ------- Rows definition ------------------------------------
    rows = [
        ("ID", "id", None),
        ("Region", "region", None),
        ("Year", "year", None),
        ("Class", "class_num", None),
        ("Strength", "strength", None),
        ("Personnel", "personnel", None),
        ("Cost (M)", "cost", None),
        ("Days", "days", None),
        ("Weight (t)", "weight", None),
        ("-", None, None),

        ("Speed (km/h)", "speed", None),
        ("Move Range (km)", "move_range", None),
        ("Fuel Cap (t)", "fuel", None),
        ("Combat Time", "combat_time", None),
        ("Supply (t)", "supply_t", None),
        ("Initiative", "initiative", None),
        ("Stealth", "stealth", None),
        ("-", None, None),

        ("Missile Cap", "missile_cap", None),
        ("Missile Size", "missile_size_max", None),
        ("Launch Types", "launch_types_str", None),
        ("Cargo Cap", "cargo_cap", None),
        ("Transport Cap", "transport_cap", None),
        ("Carrier Cap", "carrier_cap", None),
        ("-", None, None),

        ("Soft", "soft", "range_ground"),
        ("Hard", "hard", "range_ground"),
        ("Fort", "fort", "range_ground"),
        ("Close Attack", "close_combat", None),
        ("-", None, None),

        ("Air Low", "air_low", "range_air"),
        ("Air Mid", "air_mid", "range_air"),
        ("Air High", "air_high", "range_air"),
        ("Naval Surf", "naval_surf", "range_surf"),
        ("Naval Sub", "naval_sub", "range_sub"),
        ("-", None, None),

        ("Def Ground", "def_ground", None),
        ("Def Air", "def_air", None),
        ("Def Indirect", "def_indirect", None),
        ("Def Close", "def_close", None),
        ("-", None, None),

        ("NBC Prot", "nbc", None),
        ("ECM", "ecm", None),
        ("Indirect Fire", "indirect_fire", None),
        ("Ballistic Art", "ballistic_art", None),
        ("Stand-Off", "stand_off", None),
        ("Move Fire Pen.", "move_fire_penalty", None),
        ("No Eff Loss Move", "no_eff_loss_move", None),
        ("Amphibious", "amph", None),
        ("Airdrop", "airdrop", None),
        ("Survey", "survey", None),
        ("River Xing", "river_xing", None),
        ("Engineering", "engineering", None),
        ("Air Tanker", "air_tanker", None),
        ("Air Refuel", "air_refuel", None),
        ("No Land Cap", "no_land_cap", None),
        ("Has Production", "has_production", None),
    ]

    # ---- Scroll logic ------------------------------------------
    visible = rect.bottom() - start_y - 4
    max_rows = max(1, visible // row_h)

    ov.max_stats_scroll = max(0, len(rows) - max_rows)
    start_i = max(0, min(ov.stats_scroll_offset, ov.max_stats_scroll))
    end_i = min(len(rows), start_i + max_rows)

    # ---- Drawing -------------------------------------------------
    p.setFont(QFont("Consolas", 9))
    y = start_y

    for idx in range(start_i, end_i):
        label, attr, rng_attr = rows[idx]

        # separator line
        if label == "-":
            p.setPen(QColor(60, 60, 70))
            p.drawLine(rect.left() + 4, y + row_h // 2, rect.right() - 4, y + row_h // 2)
            y += row_h
            continue

        # label
        p.setPen(QColor(170, 170, 170))
        p.drawText(QRect(x_label + 6, y, label_w, row_h),
                   Qt.AlignLeft | Qt.AlignVCenter, label)

        # helper to draw a cell
        def draw_cell(base, mod, x, base_color):
            if not mod:
                p.setPen(base_color)
                p.drawText(QRect(x, y, col_w, row_h),
                           Qt.AlignCenter, "-")
                return

            txt = fmt(mod, attr, rng_attr)

            changed = False
            if base and attr:
                try:
                    changed = getattr(base, attr) != getattr(mod, attr)
                except Exception:
                    changed = False

            if changed:
                p.setPen(QColor(120, 255, 120))
            else:
                p.setPen(base_color)

            p.drawText(QRect(x, y, col_w, row_h),
                       Qt.AlignCenter, txt)

        # columns B / C / D
        draw_cell(ov.selected_unit_b, ub, x_b, QColor(130, 210, 255))
        draw_cell(ov.selected_unit_c, uc, x_c, QColor(255, 180, 110))
        draw_cell(ov.selected_unit_d, ud, x_d, QColor(150, 230, 170))

        y += row_h


# -------------------------------------------------------------------------
# TECH IMPACT VIEW
# -------------------------------------------------------------------------
def _draw_tech_impact_view(ov: "OverlayINS", p: QPainter, rect: QRect, start_y: int) -> None:
    tid = ov.selected_tech_for_impact
    p.setFont(QFont("Consolas", 10))
    y = start_y
    ov.techimpact_unit_rects = {}

    # 1. Header
    if tid:
        info = ov.tech_light.get(tid, {})
        title = info.get("short_title", f"Tech {tid}")
        header_text = f"{title} (ID {tid})"
        p.setPen(QColor(240, 240, 140))
    else:
        header_text = "Select a Tech"
        p.setPen(QColor(180, 180, 180))

    p.drawText(QRect(rect.left() + 8, y, rect.width() - 16, 20), Qt.AlignLeft, header_text)
    y += 24

    # 2. Search bar
    search_h = 20
    ov.tech_search_rect = QRect(rect.left() + 8, y, rect.width() - 16, search_h)
    p.setBrush(QColor(25, 25, 32))
    p.setPen(QColor(150, 150, 80) if ov.tech_search_focus else QColor(70, 70, 100))
    p.drawRect(ov.tech_search_rect)

    txt = ov.tech_search if ov.tech_search else "Search tech name or ID..."
    p.setPen(QColor(240, 240, 240))
    p.drawText(ov.tech_search_rect.adjusted(5, 0, 0, 0), Qt.AlignVCenter, txt)
    y += search_h + 4

    # 3. Filter tech search
    q = ov.tech_search.lower().strip()
    ov.tech_search_result_rects = []
    if q:
        results = []
        for t_id, tinfo in ov.tech_light.items():
            tname = tinfo.get("short_title", "").lower()
            if q in tname or q == str(t_id):
                results.append((t_id, tinfo.get("short_title", f"Tech {t_id}")))
        ov.tech_search_results = results[:ov.tech_search_max_display]
    else:
        ov.tech_search_results = []

    # 4. Display search results
    for t_id, label in ov.tech_search_results:
        r = QRect(rect.left() + 12, y, rect.width() - 24, 18)
        ov.tech_search_result_rects.append((r, t_id))
        p.setBrush(QColor(40, 40, 55))
        p.setPen(Qt.NoPen)
        p.drawRect(r)
        p.setPen(QColor(220, 220, 220))
        p.drawText(r.adjusted(4, 0, 0, 0), Qt.AlignVCenter, f"{t_id} – {label}")
        y += 18
    if ov.tech_search_results:
        y += 6

    if tid is None:
        p.setPen(QColor(200, 200, 200))
        p.drawText(
            QRect(rect.left() + 10, y + 10, rect.width() - 20, 40),
            Qt.AlignLeft | Qt.TextWordWrap,
            "Right-click a tech in the list above, or use the search box to view impacts.",
        )
        return

    # 5. Column widths (REVISED FOR RANGE + ATTACK)
    name_w  = 260
    soft_w  = 120
    hard_w  = 120
    def_w   = 140
    speed_w = 80
    spot_w  = 80
    range_w = 120
    atk_w   = 120

    # 6. Column positions
    x_name  = rect.left() + 8
    x_soft  = x_name + name_w
    x_hard  = x_soft + soft_w
    x_def   = x_hard + hard_w
    x_speed = x_def + def_w
    x_spot  = x_speed + speed_w
    x_range = x_spot + spot_w
    x_atk   = x_range + range_w

    # 7. Header row
    p.setPen(QColor(180, 180, 180))
    p.setFont(QFont("Consolas", 10, QFont.Bold))

    p.drawText(QRect(x_name,  y, name_w,   20), Qt.AlignLeft,  "Unit")
    p.drawText(QRect(x_soft,  y, soft_w,   20), Qt.AlignCenter, "Soft")
    p.drawText(QRect(x_hard,  y, hard_w,   20), Qt.AlignCenter, "Hard")
    p.drawText(QRect(x_def,   y, def_w,    20), Qt.AlignCenter, "Def")
    p.drawText(QRect(x_speed, y, speed_w,  20), Qt.AlignCenter, "Speed")
    p.drawText(QRect(x_spot,  y, spot_w,   20), Qt.AlignCenter, "Spot")
    p.drawText(QRect(x_range, y, range_w,  20), Qt.AlignCenter, "Range")
    p.drawText(QRect(x_atk,   y, atk_w,    20), Qt.AlignCenter, "Close Combat")
    y += 24

    # 8. Unit list
    units = [u for u in ov.units if tid in u.tech_ids]
    if not units:
        p.drawText(QRect(x_name, y, rect.width() - 16, 20), Qt.AlignLeft, "No units use this tech.")
        return

    visible_height = rect.bottom() - y - 4
    row_h = 18
    max_rows = max(1, visible_height // row_h)
    ov.techimpact_max_scroll = max(0, len(units) - max_rows)
    s = min(max(0, ov.techimpact_scroll_offset), ov.techimpact_max_scroll)
    visible = units[s:s + max_rows]

    p.setFont(QFont("Consolas", 10))

    def fmt_val(base, mod, attr):
        vb = getattr(base, attr, 0)
        vm = getattr(mod,  attr, vb)
        vb = f"{vb:.2f}".rstrip("0").rstrip(".") if isinstance(vb, float) else str(vb)
        vm = f"{vm:.2f}".rstrip("0").rstrip(".") if isinstance(vm, float) else str(vm)
        return vb, vm

    for u in visible:
        base = u
        mod  = apply_techs_to_unit(u, {tid}, ov.tech_light)

        # clickable row rect
        row_rect = QRect(x_name, y, rect.width() - 16, row_h)
        ov.techimpact_unit_rects[u.id] = row_rect

        # name
        p.setPen(QColor(220,220,220))
        p.drawText(QRect(x_name, y, name_w, row_h), Qt.AlignLeft, u.name[:35])

        # values
        for xpos, width, attr in [
            (x_soft,  soft_w,  "soft"),
            (x_hard,  hard_w,  "hard"),
            (x_def,   def_w,   "def_ground"),
            (x_speed, speed_w, "speed"),
            (x_spot,  spot_w,  "spot1"),
            (x_range, range_w, "range_ground"),
            (x_atk,   atk_w,   "close_combat"),
        ]:
            b, m = fmt_val(base, mod, attr)
            p.setPen(QColor(120,255,120) if b!=m else QColor(180,180,180))
            txt = f"{b}->{m}" if b!=m else b
            p.drawText(QRect(xpos, y, width, row_h), Qt.AlignCenter, txt)

        y += row_h
