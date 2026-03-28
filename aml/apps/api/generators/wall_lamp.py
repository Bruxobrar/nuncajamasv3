"""
Wall Lamp Engine – generates wall-mounted / sconce lamp models.

Geometry overview
-----------------
::

    ████████████████████  wall plate (flat backboard)
         │
         │  arm (horizontal or angled bracket)
         │
    ┌────┴────┐
    │  shade  │  (half-bowl or cylindrical shade facing outward)
    └─────────┘

The backboard always lies flat against the wall (the XY plane in OpenSCAD).
The arm projects along the +Y axis and terminates at the shade.
"""

from __future__ import annotations

import textwrap
from typing import List

from engines.base_engine import BaseLampEngine
from models.parameters import LampParameters


class WallLampEngine(BaseLampEngine):
    """Engine for wall-mounted sconce lamps."""

    @property
    def engine_name(self) -> str:
        return "Wall Lamp Engine"

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
    # Style-driven tweaks
    # ------------------------------------------------------------------

    _STYLE_PROFILES = {
        "modern":       dict(shade_r_factor=0.45, arm_angle=0,  plate_fn=64, shade_fn=64),
        "industrial":   dict(shade_r_factor=0.35, arm_angle=15, plate_fn=4,  shade_fn=8),
        "minimalist":   dict(shade_r_factor=0.30, arm_angle=0,  plate_fn=64, shade_fn=64),
        "scandinavian": dict(shade_r_factor=0.40, arm_angle=5,  plate_fn=32, shade_fn=32),
        "vintage":      dict(shade_r_factor=0.55, arm_angle=20, plate_fn=32, shade_fn=48),
        "art_deco":     dict(shade_r_factor=0.60, arm_angle=10, plate_fn=8,  shade_fn=12),
        "rustic":       dict(shade_r_factor=0.50, arm_angle=10, plate_fn=16, shade_fn=16),
        "futuristic":   dict(shade_r_factor=0.25, arm_angle=0,  plate_fn=6,  shade_fn=6),
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

        plate_w    = w * 0.30
        plate_h    = h * 0.35
        plate_d    = w * 0.04
        arm_r      = w * 0.025
        arm_len    = w * 0.45
        shade_r    = w * sp["shade_r_factor"]
        shade_h    = h * 0.30
        shade_top  = w * 0.08
        arm_angle  = sp["arm_angle"]
        plate_fn   = sp["plate_fn"]
        shade_fn   = sp["shade_fn"]

        scad = self._file_header(params)
        scad += textwrap.dedent(
            f"""
            // --- Parameters ---
            plate_w  = {plate_w:.2f};
            plate_h  = {plate_h:.2f};
            plate_d  = {plate_d:.2f};
            arm_r    = {arm_r:.2f};
            arm_len  = {arm_len:.2f};
            shade_r  = {shade_r:.2f};
            shade_h  = {shade_h:.2f};
            shade_top = {shade_top:.2f};
            arm_angle = {arm_angle};
            thickness = {t:.2f};
            plate_fn = {plate_fn};
            shade_fn = {shade_fn};

            // --- Wall plate (backboard) ---
            color("{params.color}")
            translate([-plate_w/2, 0, -plate_h/2])
                cube([plate_w, plate_d, plate_h]);

            // --- Arm ---
            color("silver")
            rotate([arm_angle, 0, 0])
            translate([0, plate_d, 0])
                rotate([90, 0, 0])
                rotate([0, 0, 0])
                cylinder(h=arm_len, r1=arm_r, r2=arm_r * 0.8, center=false, $fn=plate_fn);

            // --- Shade (hollow cone, opens downward) ---
            color("{params.color}")
            rotate([arm_angle, 0, 0])
            translate([0, plate_d + arm_len, -shade_h])
            difference() {{
                cylinder(h=shade_h, r1=shade_r, r2=shade_top, center=false, $fn=shade_fn);
                translate([0, 0, thickness])
                    cylinder(h=shade_h, r1=shade_r - thickness,
                             r2=shade_top - thickness, center=false, $fn=shade_fn);
            }}
            """
        )
        return scad
