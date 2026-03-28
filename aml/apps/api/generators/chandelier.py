r"""
Chandelier Engine – generates multi-arm ceiling chandelier models.

Geometry overview
-----------------
::

      ┌────────────────────┐
      │   ceiling canopy   │
      └────────┬───────────┘
               │  center rod
         ┌─────┴─────┐
         │  hub disc  │
         └───┬──┬──┬──┘
            /   |   \
           /    |    \       ← arms radiate outward at equal angular spacing
          /     |     \
         S      S      S    S = individual pendant shade + bulb

The number of arms and the shade style follow the *num_arms* and *style* parameters.
"""

from __future__ import annotations

import math
import textwrap
from typing import List

from engines.base_engine import BaseLampEngine
from models.parameters import LampParameters


class ChandelierEngine(BaseLampEngine):
    """Engine for multi-arm chandeliers."""

    @property
    def engine_name(self) -> str:
        return "Chandelier Engine"

    @property
    def supported_styles(self) -> List[str]:
        return [
            "modern",
            "industrial",
            "minimalist",
            "vintage",
            "art_deco",
            "rustic",
            "futuristic",
        ]

    # ------------------------------------------------------------------
    # Style-driven tweaks
    # ------------------------------------------------------------------

    _STYLE_PROFILES = {
        "modern":      dict(shade_flare=0.50, arm_r=5,  fn=64),
        "industrial":  dict(shade_flare=0.35, arm_r=8,  fn=8),
        "minimalist":  dict(shade_flare=0.30, arm_r=4,  fn=64),
        "vintage":     dict(shade_flare=0.75, arm_r=6,  fn=32),
        "art_deco":    dict(shade_flare=0.80, arm_r=7,  fn=12),
        "rustic":      dict(shade_flare=0.65, arm_r=7,  fn=16),
        "futuristic":  dict(shade_flare=0.20, arm_r=5,  fn=6),
    }

    #: Minimum number of arms the chandelier engine will produce regardless of
    #: the value supplied in :attr:`~models.parameters.LampParameters.num_arms`.
    MIN_ARMS: int = 2

    def _style(self, params: LampParameters) -> dict:
        return self._STYLE_PROFILES.get(params.style, self._STYLE_PROFILES["modern"])

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, params: LampParameters) -> str:
        sp       = self._style(params)
        w        = params.width_mm
        h        = params.height_mm
        t        = params.shade_thickness_mm
        n_arms   = max(self.MIN_ARMS, params.num_arms)

        canopy_r    = params.base_diameter_mm * 0.35
        canopy_h    = h * 0.06
        rod_r       = sp["arm_r"] * 0.6
        rod_h       = params.cord_length_mm * 0.5
        hub_r       = canopy_r * 0.70
        hub_h       = h * 0.04
        arm_r       = sp["arm_r"]
        arm_len     = w * 0.40
        pendant_h   = h * 0.18
        shade_r_top = w * 0.05
        shade_r_bot = w * 0.18 * sp["shade_flare"]
        bulb_r      = shade_r_top * 0.8
        fn          = sp["fn"]

        # Per-arm angular step
        angle_step = 360.0 / n_arms

        scad = self._file_header(params)
        scad += textwrap.dedent(
            f"""
            // --- Parameters ---
            canopy_r    = {canopy_r:.2f};
            canopy_h    = {canopy_h:.2f};
            rod_r       = {rod_r:.2f};
            rod_h       = {rod_h:.2f};
            hub_r       = {hub_r:.2f};
            hub_h       = {hub_h:.2f};
            arm_r       = {arm_r:.2f};
            arm_len     = {arm_len:.2f};
            pendant_h   = {pendant_h:.2f};
            shade_r_top = {shade_r_top:.2f};
            shade_r_bot = {shade_r_bot:.2f};
            bulb_r      = {bulb_r:.2f};
            thickness   = {t:.2f};
            fn          = {fn};
            n_arms      = {n_arms};
            angle_step  = {angle_step:.4f};

            // --- Ceiling Canopy ---
            color("{params.color}")
            translate([0, 0, rod_h + hub_h])
                cylinder(h=canopy_h, r1=canopy_r, r2=canopy_r * 0.8, center=false, $fn=fn);

            // --- Central Rod ---
            color("silver")
            translate([0, 0, hub_h])
                cylinder(h=rod_h, r1=rod_r, r2=rod_r, center=false, $fn=fn);

            // --- Hub disc ---
            color("{params.color}")
            cylinder(h=hub_h, r1=hub_r, r2=hub_r, center=false, $fn=fn);
            """
        )

        # Generate each arm + pendant dynamically
        for i in range(n_arms):
            angle_deg = i * angle_step
            angle_rad = math.radians(angle_deg)
            ax = math.cos(angle_rad) * arm_len
            ay = math.sin(angle_rad) * arm_len

            scad += textwrap.dedent(
                f"""
                // --- Arm {i + 1} (angle={angle_deg:.1f}°) ---
                color("{params.color}")
                rotate([0, 0, {angle_deg:.2f}])
                translate([0, 0, hub_h / 2])
                    rotate([0, 90, 0])
                    cylinder(h=arm_len, r1=arm_r, r2=arm_r * 0.7, center=false, $fn=fn);

                // Pendant shade for arm {i + 1}
                color("{params.color}")
                translate([{ax:.2f}, {ay:.2f}, -(pendant_h)])
                difference() {{
                    cylinder(h=pendant_h, r1=shade_r_bot, r2=shade_r_top, center=false, $fn=fn);
                    translate([0, 0, thickness])
                        cylinder(h=pendant_h, r1=shade_r_bot - thickness,
                                 r2=shade_r_top - thickness, center=false, $fn=fn);
                }}

                // Bulb for arm {i + 1}
                color("lightyellow", 0.6)
                translate([{ax:.2f}, {ay:.2f}, -(pendant_h + bulb_r)])
                    sphere(r=bulb_r, $fn=fn);
                """
            )

        return scad
