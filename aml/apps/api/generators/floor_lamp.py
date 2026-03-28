"""
Floor Lamp Engine – generates standing / torchière floor lamp models.

Geometry overview
-----------------
::

        ┌──────────────┐
        │    shade     │   (large upward-opening shade or downward cone)
        └──────┬───────┘
               │  upper pole
        ┌──────┴───────┐
        │   joint cap  │
        └──────┬───────┘
               │  lower pole
        ════════════════  tripod / base (style-dependent)

Style variants
--------------
* modern / minimalist / scandinavian → single straight pole + disc base
* industrial → thick pipe, visible hardware details
* vintage / rustic → weighted pedestal base
* art_deco / futuristic → decorative swept stem
"""

from __future__ import annotations

import textwrap
from typing import List

from engines.base_engine import BaseLampEngine
from models.parameters import LampParameters


class FloorLampEngine(BaseLampEngine):
    """Engine for floor / standing lamps."""

    @property
    def engine_name(self) -> str:
        return "Floor Lamp Engine"

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
        "modern":       dict(shade_flare=0.50, pole_r=8,  base_r_factor=0.25, fn=64),
        "industrial":   dict(shade_flare=0.40, pole_r=12, base_r_factor=0.20, fn=8),
        "minimalist":   dict(shade_flare=0.30, pole_r=5,  base_r_factor=0.22, fn=64),
        "scandinavian": dict(shade_flare=0.55, pole_r=7,  base_r_factor=0.28, fn=48),
        "vintage":      dict(shade_flare=0.70, pole_r=9,  base_r_factor=0.30, fn=32),
        "art_deco":     dict(shade_flare=0.80, pole_r=11, base_r_factor=0.32, fn=12),
        "rustic":       dict(shade_flare=0.60, pole_r=10, base_r_factor=0.30, fn=16),
        "futuristic":   dict(shade_flare=0.20, pole_r=6,  base_r_factor=0.22, fn=6),
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

        shade_h      = h * 0.20
        shade_r_top  = w * 0.15
        shade_r_bot  = w * 0.50 * sp["shade_flare"]
        pole_h       = h * 0.70
        pole_r       = sp["pole_r"]
        joint_h      = h * 0.04
        joint_r      = pole_r * 1.8
        base_h       = h * 0.04
        base_r       = params.base_diameter_mm * sp["base_r_factor"] * 3
        fn           = sp["fn"]

        scad = self._file_header(params)
        scad += textwrap.dedent(
            f"""
            // --- Parameters ---
            shade_h     = {shade_h:.2f};
            shade_r_top = {shade_r_top:.2f};
            shade_r_bot = {shade_r_bot:.2f};
            pole_h      = {pole_h:.2f};
            pole_r      = {pole_r:.2f};
            joint_h     = {joint_h:.2f};
            joint_r     = {joint_r:.2f};
            base_h      = {base_h:.2f};
            base_r      = {base_r:.2f};
            thickness   = {t:.2f};
            fn          = {fn};

            // --- Shade (opens upward – torchière style) ---
            color("{params.color}")
            translate([0, 0, base_h + pole_h + joint_h])
            difference() {{
                cylinder(h=shade_h, r1=shade_r_top, r2=shade_r_bot, center=false, $fn=fn);
                translate([0, 0, thickness])
                    cylinder(h=shade_h, r1=shade_r_top - thickness,
                             r2=shade_r_bot - thickness, center=false, $fn=fn);
            }}

            // --- Joint cap ---
            color("silver")
            translate([0, 0, base_h + pole_h])
                cylinder(h=joint_h, r1=joint_r, r2=joint_r * 0.8, center=false, $fn=fn);

            // --- Pole ---
            color("{params.color}")
            translate([0, 0, base_h])
                cylinder(h=pole_h, r1=pole_r, r2=pole_r, center=false, $fn=fn);

            // --- Base ---
            color("{params.color}")
            cylinder(h=base_h, r1=base_r, r2=base_r * 0.80, center=false, $fn=fn);
            """
        )
        return scad
