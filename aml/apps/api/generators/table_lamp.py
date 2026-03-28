"""
Table Lamp Engine – generates desk / bedside table lamp models.

Geometry overview
-----------------
::

        ┌──────────────┐
        │    shade     │  (tapered hollow cylinder)
        └──────┬───────┘
               │  neck (slender cylinder)
        ┌──────┴───────┐
        │     body     │  (decorative body, style-dependent)
        └──────┬───────┘
        ════════════════  base (flat disc or stepped pedestal)

The body shape varies per style:
* modern / minimalist → slender straight column
* vintage / art_deco  → curved vase-like body (approximated via scaled cylinders)
* industrial          → angular box body
* scandinavian / rustic → wider wooden body
"""

from __future__ import annotations

import textwrap
from typing import List

from engines.base_engine import BaseLampEngine
from models.parameters import LampParameters


class TableLampEngine(BaseLampEngine):
    """Engine for table / desk / bedside lamps."""

    @property
    def engine_name(self) -> str:
        return "Table Lamp Engine"

    @property
    def supported_styles(self) -> List[str]:
        return [
            "modern",
            "industrial",
            "minimalist",
            "scandinavian",
            "vintage",
            "art_deco",
            "rustic",
            "futuristic",
        ]

    # ------------------------------------------------------------------
    # Style-driven geometry tweaks
    # ------------------------------------------------------------------

    _STYLE_PROFILES = {
        "modern":       dict(shade_flare=0.55, body_r=0.08, body_taper=0.6, fn=64),
        "industrial":   dict(shade_flare=0.40, body_r=0.10, body_taper=1.0, fn=8),
        "minimalist":   dict(shade_flare=0.35, body_r=0.05, body_taper=0.5, fn=64),
        "scandinavian": dict(shade_flare=0.50, body_r=0.12, body_taper=0.7, fn=32),
        "vintage":      dict(shade_flare=0.70, body_r=0.15, body_taper=0.5, fn=48),
        "art_deco":     dict(shade_flare=0.75, body_r=0.14, body_taper=0.4, fn=12),
        "rustic":       dict(shade_flare=0.60, body_r=0.16, body_taper=0.6, fn=16),
        "futuristic":   dict(shade_flare=0.25, body_r=0.07, body_taper=0.3, fn=6),
    }

    def _style(self, params: LampParameters) -> dict:
        return self._STYLE_PROFILES.get(params.style, self._STYLE_PROFILES["modern"])

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, params: LampParameters) -> str:
        sp = self._style(params)
        w  = params.width_mm
        h  = params.height_mm
        t  = params.shade_thickness_mm

        shade_h    = h * 0.35
        shade_r_top = w * 0.12
        shade_r_bot = w * 0.50 * sp["shade_flare"]
        body_h     = h * 0.40
        body_r_bot = w * sp["body_r"] * 1.6
        body_r_top = w * sp["body_r"] * sp["body_taper"]
        neck_h     = h * 0.08
        neck_r     = w * 0.03
        base_h     = h * 0.06
        base_r     = params.base_diameter_mm * 0.50
        fn         = sp["fn"]

        scad = self._file_header(params)
        scad += textwrap.dedent(
            f"""
            // --- Parameters ---
            shade_h    = {shade_h:.2f};
            shade_r_top = {shade_r_top:.2f};
            shade_r_bot = {shade_r_bot:.2f};
            body_h     = {body_h:.2f};
            body_r_bot = {body_r_bot:.2f};
            body_r_top = {body_r_top:.2f};
            neck_h     = {neck_h:.2f};
            neck_r     = {neck_r:.2f};
            base_h     = {base_h:.2f};
            base_r     = {base_r:.2f};
            thickness  = {t:.2f};
            fn         = {fn};

            // --- Shade ---
            color("{params.color}")
            translate([0, 0, body_h + neck_h])
            difference() {{
                cylinder(h=shade_h, r1=shade_r_bot, r2=shade_r_top, center=false, $fn=fn);
                translate([0, 0, thickness])
                    cylinder(h=shade_h, r1=shade_r_bot - thickness,
                             r2=shade_r_top - thickness, center=false, $fn=fn);
            }}

            // --- Neck ---
            color("silver")
            translate([0, 0, body_h])
                cylinder(h=neck_h, r1=neck_r*1.2, r2=neck_r, center=false, $fn=fn);

            // --- Body ---
            color("{params.color}")
            translate([0, 0, base_h])
                cylinder(h=body_h, r1=body_r_bot, r2=body_r_top, center=false, $fn=fn);

            // --- Base ---
            color("{params.color}")
            cylinder(h=base_h, r1=base_r, r2=base_r * 0.85, center=false, $fn=fn);
            """
        )
        return scad
