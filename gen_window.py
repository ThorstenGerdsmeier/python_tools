#!/usr/bin/env python3
"""
Generate an SVG window (rectangular or arched).

Parameters (all in millimeters):
- width_mm: overall window width
- height_mm: overall window height (includes arch if arch_height_mm > 0)
- frame_width_mm: thickness of the outer frame
- num_vertical_bars: number of vertical sash bars (>= 0)
- num_horizontal_bars: number of horizontal sash bars (>= 0)
- sash_bar_width_mm: width of (non-center) sash bars
- arch_height_mm: height of the arch (0 for rectangular window). The arch
  is a symmetric elliptical arc spanning the full width with rise = arch_height_mm.
- center_vertical_bar_width_mm: if num_vertical_bars is odd, the center bar
  can be wider; if None, it uses sash_bar_width_mm.

Notes:
- Vertical and horizontal bars are equally distributed by CENTERLINES across the
  glazing area (the inner area inside the frame). If the vertical count is odd,
  a bar is centered; you may give it a different width via center_vertical_bar_width_mm.
- Bars are drawn as rectangles and clipped to the glazing shape, so on arched
  windows the bars naturally follow the arch boundary.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class WindowSpec:
    width_mm: float
    height_mm: float
    frame_width_mm: float
    num_vertical_bars: int
    num_horizontal_bars: int
    sash_bar_width_mm: float
    arch_height_mm: float = 0.0
    center_vertical_bar_width_mm: Optional[float] = None

    # Colors (override if you like)
    frame_color: str = "#c7c7c7"
    glass_color: str = "#e6f2ff"
    bar_color: str = "#c7c7c7"


def _path_arch(width: float, height: float, arch_h: float) -> str:
    """
    Outer path for an arched window. Coordinate system: (0,0) top-left, y downwards.
    Arch spans from (0, arch_h) to (width, arch_h) with an elliptical arc (rx=width/2, ry=arch_h).
    Then straight lines down to the bottom and back.
    """
    # If arch_h == 0, this shouldn't be called; use a rectangle instead.
    # Arc flags: large-arc-flag=0 (minor arc), sweep-flag=1 (left->right, convex upward)
    return (
        f"M 0,{arch_h} "
        f"A {width/2},{arch_h} 0 0 1 {width},{arch_h} "
        f"L {width},{height} "
        f"L 0,{height} Z"
    )


def _path_arch_inner(width: float, height: float, frame_w: float, arch_h: float) -> str:
    """
    Inner glazing path for an arched window, inset by frame width.
    """
    wi = max(0.0, width - 2 * frame_w)
    hi = max(0.0, height - 2 * frame_w)
    arch_inner = max(0.0, arch_h - frame_w)
    x0 = frame_w
    y0 = frame_w
    # Start at left springline of inner arch
    return (
        f"M {x0},{y0 + arch_inner} "
        f"A {wi/2},{arch_inner} 0 0 1 {x0 + wi},{y0 + arch_inner} "
        f"L {x0 + wi},{y0 + hi} "
        f"L {x0},{y0 + hi} Z"
    )


def generate_window_svg(spec: WindowSpec) -> str:
    W = float(spec.width_mm)
    H = float(spec.height_mm)
    FW = float(spec.frame_width_mm)
    NV = int(spec.num_vertical_bars)
    NH = int(spec.num_horizontal_bars)
    BW = float(spec.sash_bar_width_mm)
    AH = float(spec.arch_height_mm)
    CWB = float(spec.center_vertical_bar_width_mm) if spec.center_vertical_bar_width_mm else BW

    if W <= 0 or H <= 0:
        raise ValueError("Window width and height must be positive.")
    if FW < 0 or 2 * FW >= min(W, H):
        raise ValueError("Frame width must be non-negative and less than half the window size.")
    if AH < 0 or AH > H:
        raise ValueError("Arch height must be between 0 and the total height.")
    if NV < 0 or NH < 0:
        raise ValueError("Number of sash bars cannot be negative.")
    if BW < 0 or CWB < 0:
        raise ValueError("Sash bar widths must be non-negative.")

    # Inner glazing box bounds (used for equal spacing)
    inner_x = FW
    inner_y = FW
    inner_w = W - 2 * FW
    inner_h = H - 2 * FW

    # Build outer and inner shapes
    if AH > 0:
        outer_path = _path_arch(W, H, AH)
        inner_path = _path_arch_inner(W, H, FW, AH)
        # For clipping, reuse the inner path
        glazing_path_d = inner_path
    else:
        outer_path = None  # use <rect>
        inner_path = None  # use <rect>
        glazing_path_d = None

    # SVG header
    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
        "  <defs>"
    ]

    # Define clipPath for glazing area
    svg.append('    <clipPath id="glazingClip">')
    if AH > 0:
        svg.append(f'      <path d="{glazing_path_d}"/>')
    else:
        svg.append(f'      <rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}"/>')
    svg.append("    </clipPath>")
    svg.append("  </defs>")

    # Draw frame (outer shape filled frame color), then glaze fill, then bars
    if AH > 0:
        svg.append(f'  <path d="{outer_path}" fill="{spec.frame_color}" stroke="none"/>')
        svg.append(f'  <path d="{inner_path}" fill="{spec.glass_color}" stroke="none"/>')
    else:
        svg.append(f'  <rect x="0" y="0" width="{W}" height="{H}" fill="{spec.frame_color}" stroke="none"/>')
        svg.append(f'  <rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}" fill="{spec.glass_color}" stroke="none"/>')

    # Sash bars (use clipping so they don't spill outside the glazing shape)
    svg.append('  <g clip-path="url(#glazingClip)">')

    # Vertical bars: equally spaced by centerlines across inner_w
    if NV > 0 and inner_w > 0:
        x_gap = inner_w / (NV + 1)
        for i in range(NV):
            cx = inner_x + (i + 1) * x_gap
            w = CWB if (NV % 2 == 1 and i == NV // 2) else BW
            x = cx - w / 2
            svg.append(f'    <rect x="{x}" y="0" width="{w}" height="{H}" fill="{spec.bar_color}" stroke="none"/>')

    # Horizontal bars: equally spaced by centerlines across inner_h
    if NH > 0 and inner_h > 0:
        y_gap = inner_h / (NH + 1)
        for j in range(NH):
            cy = inner_y + (j + 1) * y_gap
            y = cy - BW / 2
            svg.append(f'    <rect x="0" y="{y}" width="{W}" height="{BW}" fill="{spec.bar_color}" stroke="none"/>')

    svg.append("  </g>")
    svg.append("</svg>")

    return "\n".join(svg)


# Example usage:
if __name__ == "__main__":
    # Rectangular window with 2 vertical, 1 horizontal bar
    rect_svg = generate_window_svg(WindowSpec(
        width_mm=800,
        height_mm=1200,
        frame_width_mm=60,
        num_vertical_bars=2,
        num_horizontal_bars=1,
        sash_bar_width_mm=30,
        arch_height_mm=0
    ))
    with open("window_rect.svg", "w", encoding="utf-8") as f:
        f.write(rect_svg)

    # Arched window with 3 vertical (center wider), 2 horizontal bars, 250 mm arch
    arch_svg = generate_window_svg(WindowSpec(
        width_mm=36,
        height_mm=36,
        frame_width_mm=3,
        num_vertical_bars=3,
        num_horizontal_bars=2,
        sash_bar_width_mm=2,
        arch_height_mm=18,
        center_vertical_bar_width_mm=2
    ))
    with open("window_arch.svg", "w", encoding="utf-8") as f:
        f.write(arch_svg)

    print("Wrote window_rect.svg and window_arch.svg")