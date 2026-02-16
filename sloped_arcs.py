from pathlib import Path

def arc_line_chain_with_X_svg(
    n: int,
    la: float,
    r: float,
    stroke: str = "black",
    stroke_width: float = 2.5,
    margin: float = 16.0,
    background: str = "white",
    linecap: str = "round",
    linejoin: str = "round",
    mirror: bool = False,  # 🔹 new option
) -> str:
    """
    Draw:
      - Vertical X of length la (first element)
      - Horizontal A of length la connected to X's bottom
      - Semicircle (open at bottom, radius r) connected to A's right end
      - Horizontal B of length la connected to semicircle's right end
      - Vertical C of length la (up) connected to B's right end
      - Repeat (semicircle -> B -> C) for n times

    Parameters:
      n       : number of repetitions of (semicircle, B, C)
      la      : length of A, B, C, X
      r       : semicircle radius
      mirror  : if True, mirror pattern horizontally across the left edge
    """
    assert n >= 1
    assert la > 0 and r > 0

    # Geometry
    y0 = margin + n * la + r
    baseline = y0 + la
    x = margin

    cmds = []
    cmds.append(f"M {x:.2f},{y0 - la:.2f}")  # top of X
    cmds.append(f"V {y0:.2f}")               # X down
    cmds.append(f"H {x + la:.2f}")           # A right
    x += la

    for _ in range(n):
        cmds.append(f"A {r:.2f},{r:.2f} 0 0 1 {x + 2*r:.2f},{y0:.2f}")  # semicircle
        x += 2 * r
        cmds.append(f"H {x + la:.2f}")  # B
        x += la
        y0 -= la
        cmds.append(f"V {y0:.2f}")  # C up

    width = x + margin
    height = baseline + margin
    d = " ".join(cmds)

    # 🔹 If mirror is True, use SVG transform
    transform = f'transform="translate({width}) scale(-1,1)"' if mirror else ""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="{width:.0f}" height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}">
  <rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="{background}"/>
  <path d="{d}" {transform} fill="none" stroke="{stroke}" stroke-width="{stroke_width}"
        stroke-linecap="{linecap}" stroke-linejoin="{linejoin}"/>
</svg>"""
    return svg


"""
from pathlib import Path

# Regular (left-to-right)
svg1 = arc_line_chain_with_X_svg(n=3, la=60, r=30)
Path("arc_line_chain_with_X_normal.svg").write_text(svg1, encoding="utf-8")

# Mirrored (right-to-left)
svg2 = arc_line_chain_with_X_svg(n=3, la=60, r=30, mirror=True)
Path("arc_line_chain_with_X_mirrored.svg").write_text(svg2, encoding="utf-8")
"""