#!/usr/bin/env python3
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

    frame_color: str = "#c7c7c7"
    glass_color: str = "#e6f2ff"
    bar_color: str = "#c7c7c7"

# --- path builders ------------------------------------------------------------

def _path_arch_outer(width: float, height: float, arch_h: float) -> str:
    # Arch spans full width with rise = arch_h
    return (
        f"M 0,{arch_h} "
        f"A {width/2},{arch_h} 0 0 1 {width},{arch_h} "
        f"L {width},{height} L 0,{height} Z"
    )

def _path_arch_inner(width: float, height: float, frame_w: float, arch_h: float) -> str:
    wi = max(0.0, width - 2 * frame_w)
    hi = max(0.0, height - 2 * frame_w)
    arch_inner = max(0.0, arch_h - frame_w)
    x0 = frame_w; y0 = frame_w
    return (
        f"M {x0},{y0 + arch_inner} "
        f"A {wi/2},{arch_inner} 0 0 1 {x0 + wi},{y0 + arch_inner} "
        f"L {x0 + wi},{y0 + hi} L {x0},{y0 + hi} Z"
    )

def _compound_frame_path_rect(W: float, H: float, FW: float) -> str:
    # outer rect then inner rect; evenodd fill turns inner into a hole
    return (
        f"M 0,0 L {W},0 L {W},{H} L 0,{H} Z "
        f"M {FW},{FW} L {W-FW},{FW} L {W-FW},{H-FW} L {FW},{H-FW} Z"
    )

def _compound_frame_path_arch(W: float, H: float, FW: float, AH: float) -> str:
    # Concatenate outer arch and inner arch paths; evenodd fill makes a hole
    outer = _path_arch_outer(W, H, AH)
    inner = _path_arch_inner(W, H, FW, AH)
    # Remove trailing 'Z' if present to safely concatenate with a space
    outer = outer.strip()
    inner = inner.strip()
    return f"{outer} {inner}"

# --- main generator -----------------------------------------------------------

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

    inner_x = FW
    inner_y = FW
    inner_w = W - 2 * FW
    inner_h = H - 2 * FW

    # Build glazing shape for clip + glass fill
    if AH > 0:
        glazing_path = _path_arch_inner(W, H, FW, AH)
        frame_path  = _compound_frame_path_arch(W, H, FW, AH)
    else:
        glazing_path = None
        frame_path  = _compound_frame_path_rect(W, H, FW)

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">',
        "  <defs>",
        '    <clipPath id="glazingClip">'
    ]
    if AH > 0:
        svg.append(f'      <path d="{glazing_path}"/>')
    else:
        svg.append(f'      <rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}"/>')
    svg += [
        "    </clipPath>",
        "  </defs>",
    ]

    # 1) GLASS (underneath)
    if AH > 0:
        svg.append(f'  <path d="{glazing_path}" fill="{spec.glass_color}" stroke="none"/>')
    else:
        svg.append(f'  <rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}" fill="{spec.glass_color}" stroke="none"/>')

    # 2) FRAME as compound path (outer minus inner)
    svg.append(f'  <path d="{frame_path}" fill="{spec.frame_color}" fill-rule="evenodd" stroke="none"/>')

    # 3) BARS (clipped to glazing)
    svg.append('  <g clip-path="url(#glazingClip)">')

    # Vertical bars (centerline spacing). If NV is odd, center bar gets CWB.
    if NV > 0 and inner_w > 0:
        x_gap = inner_w / (NV + 1)
        for i in range(NV):
            cx = inner_x + (i + 1) * x_gap
            w = CWB if (NV % 2 == 1 and i == NV // 2) else BW
            x = cx - w / 2
            svg.append(f'    <rect x="{x}" y="0" width="{w}" height="{H}" fill="{spec.bar_color}" stroke="none"/>')

    # Horizontal bars (centerline spacing)
    if NH > 0 and inner_h > 0:
        y_gap = inner_h / (NH + 1)
        for j in range(NH):
            cy = inner_y + (j + 1) * y_gap
            y = cy - BW / 2
            svg.append(f'    <rect x="0" y="{y}" width="{W}" height="{BW}" fill="{spec.bar_color}" stroke="none"/>')

    svg.append("  </g>")
    svg.append("</svg>")
    return "\n".join(svg)

# Example
if __name__ == "__main__":
    # Rectangular example
    rect_svg = generate_window_svg(WindowSpec(
        width_mm=800, height_mm=1200, frame_width_mm=60,
        num_vertical_bars=3, num_horizontal_bars=2,
        sash_bar_width_mm=30, arch_height_mm=0,
        center_vertical_bar_width_mm=50
    ))
    with open("window_rect.svg", "w", encoding="utf-8") as f:
        f.write(rect_svg)

    # Arched example
    arch_svg = generate_window_svg(WindowSpec(
        width_mm=1000, height_mm=1400, frame_width_mm=70,
        num_vertical_bars=3, num_horizontal_bars=2,
        sash_bar_width_mm=35, arch_height_mm=250,
        center_vertical_bar_width_mm=60
    ))
    with open("window_arch.svg", "w", encoding="utf-8") as f:
        f.write(arch_svg)

    print("Wrote window_rect.svg and window_arch.svg")