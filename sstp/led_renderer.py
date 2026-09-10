import cairo
import math
from typing import Dict, List, Tuple

# Segment definitions:
#   aaaa
#  f    b
#  f    b
#   gggg
#  e    c
#  e    c
#   dddd

DIGIT_MAP: Dict[str, List[str]] = {
    "0": ["a", "b", "c", "d", "e", "f"],
    "1": ["b", "c"],
    "2": ["a", "b", "g", "e", "d"],
    "3": ["a", "b", "g", "c", "d"],
    "4": ["f", "g", "b", "c"],
    "5": ["a", "f", "g", "c", "d"],
    "6": ["a", "f", "e", "d", "c", "g"],
    "7": ["a", "b", "c"],
    "8": ["a", "b", "c", "d", "e", "f", "g"],
    "9": ["a", "b", "c", "d", "f", "g"],
    "-": ["g"],
    " ": [],
}

DIGIT_CENTERS: List[float] = [351.0, 375.0, 399.0, 424.0]
DIGIT_CY: float = 600.0


def get_digit_segments(cx: float, cy: float) -> Dict[str, List[Tuple[float, float]]]:
    """Generates precise segment polygons for a slanted 7-segment digit."""
    y_top = cy - 11.8
    y_mid = cy
    y_bot = cy + 12.0

    def pt(lx: float, y: float) -> Tuple[float, float]:
        skew = (cy - y) * 0.14
        return (cx + lx + skew, y)

    w = 6.0
    t = 1.9

    return {
        "a": [
            pt(-w + 1.2, y_top),
            pt(w - 1.2, y_top),
            pt(w - 2.2, y_top + t),
            pt(-w + 2.2, y_top + t),
        ],
        "b": [
            pt(w, y_top + 1.2),
            pt(w, y_mid - 0.7),
            pt(w - t, y_mid - 1.2),
            pt(w - t, y_top + 2.0),
        ],
        "c": [
            pt(w, y_mid + 0.7),
            pt(w, y_bot - 1.2),
            pt(w - t, y_bot - 2.0),
            pt(w - t, y_mid + 1.2),
        ],
        "d": [
            pt(-w + 2.2, y_bot - t),
            pt(w - 2.2, y_bot - t),
            pt(w - 1.2, y_bot),
            pt(-w + 1.2, y_bot),
        ],
        "e": [
            pt(-w, y_mid + 0.7),
            pt(-w, y_bot - 1.2),
            pt(-w + t, y_bot - 2.0),
            pt(-w + t, y_mid + 1.2),
        ],
        "f": [
            pt(-w, y_top + 1.2),
            pt(-w, y_mid - 0.7),
            pt(-w + t, y_mid - 1.2),
            pt(-w + t, y_top + 2.0),
        ],
        "g": [
            pt(-w + 1.4, y_mid - t * 0.5),
            pt(w - 1.4, y_mid - t * 0.5),
            pt(w - 1.4, y_mid + t * 0.5),
            pt(-w + 1.4, y_mid + t * 0.5),
        ],
    }


def draw_polygon(cr: cairo.Context, pts: List[Tuple[float, float]]):
    cr.move_to(pts[0][0], pts[0][1])
    for p in pts[1:]:
        cr.line_to(p[0], p[1])
    cr.close_path()


def render_led_overlay(
    cr: cairo.Context,
    text: str,
    show_colon: bool = True,
    intensity: float = 1.0,
    active: bool = True,
):
    """Renders pixel-perfect glowing red 7-segment digits directly over the LED display."""
    if not active:
        return

    text = text.rjust(4, " ")[:4]
    glow_intensity = max(0.0, min(1.0, intensity))

    # Multi-pass rendering for realistic LED phosphor glow and bloom
    for i, char in enumerate(text):
        cx = DIGIT_CENTERS[i]
        segs = get_digit_segments(cx, DIGIT_CY)
        lit_names = DIGIT_MAP.get(char, [])

        for s_name in lit_names:
            pts = segs[s_name]

            # Pass 1: Wide diffuse red bloom
            cr.save()
            draw_polygon(cr, pts)
            cr.set_source_rgba(1.0, 0.05, 0.05, 0.18 * glow_intensity)
            cr.set_line_width(5.0)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.stroke()
            cr.restore()

            # Pass 2: Mid red glow
            cr.save()
            draw_polygon(cr, pts)
            cr.set_source_rgba(1.0, 0.12, 0.12, 0.45 * glow_intensity)
            cr.set_line_width(2.6)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.stroke()
            cr.restore()

            # Pass 3: Saturated vivid red segment fill
            cr.save()
            draw_polygon(cr, pts)
            cr.set_source_rgba(1.0, 0.18, 0.18, 0.95 * glow_intensity)
            cr.fill()
            cr.restore()

            # Pass 4: Hot white/pink inner core highlight
            cr.save()
            draw_polygon(cr, pts)
            cr.set_source_rgba(1.0, 0.88, 0.84, 0.78 * glow_intensity)
            cr.set_line_width(0.8)
            cr.stroke()
            cr.restore()

    # Blinking colon separator between MM and SS
    if show_colon:
        colon_x = 387.0
        for dy in [594.0, 606.0]:
            skew = (DIGIT_CY - dy) * 0.14
            dot_x = colon_x + skew

            # Diffuse glow
            cr.save()
            cr.arc(dot_x, dy, 2.4, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 0.08, 0.08, 0.4 * glow_intensity)
            cr.fill()
            cr.restore()

            # Core dot
            cr.save()
            cr.arc(dot_x, dy, 1.1, 0, 2 * math.pi)
            cr.set_source_rgba(1.0, 0.88, 0.84, 0.9 * glow_intensity)
            cr.fill()
            cr.restore()


def render_tube_glow(cr: cairo.Context, pulse_phase: float):
    """Renders soft, breathing vacuum tube glow on the right side of the machine."""
    pulse = 0.5 + 0.5 * math.sin(pulse_phase * 2.5)

    # Violet/purple mercury vapor glow inside vacuum tubes
    tube_centers = [(648.0, 193.0), (688.0, 186.0), (717.0, 209.0)]
    for tx, ty in tube_centers:
        cr.save()
        pattern = cairo.RadialGradient(tx, ty, 5.0, tx, ty, 35.0)
        pattern.add_color_stop_rgba(0.0, 0.75, 0.25, 1.0, 0.22 + 0.12 * pulse)
        pattern.add_color_stop_rgba(0.5, 0.55, 0.15, 0.9, 0.10 + 0.06 * pulse)
        pattern.add_color_stop_rgba(1.0, 0.40, 0.05, 0.7, 0.0)
        cr.set_source(pattern)
        cr.arc(tx, ty, 35.0, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

    # Warm amber filament glow
    filament_centers = [(648.0, 216.0), (688.0, 209.0)]
    for fx, fy in filament_centers:
        cr.save()
        pattern = cairo.RadialGradient(fx, fy, 2.0, fx, fy, 15.0)
        pattern.add_color_stop_rgba(0.0, 1.0, 0.7, 0.2, 0.35 + 0.15 * pulse)
        pattern.add_color_stop_rgba(1.0, 1.0, 0.4, 0.0, 0.0)
        cr.set_source(pattern)
        cr.arc(fx, fy, 15.0, 0, 2 * math.pi)
        cr.fill()
        cr.restore()
