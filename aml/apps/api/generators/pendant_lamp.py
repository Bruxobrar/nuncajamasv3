"""
Pendant Lamp Engine – generates hanging / ceiling-mount lamp models.

Geometry overview
-----------------
::

      ┌────────────────────┐
      │   ceiling mount    │
      │       disc         │
      └────────┬───────────┘
               │  cord
               │
          ┌────┴────┐
          │  shade  │  (hollow frustum / cone)
          └─────────┘
               │  lamp socket
              ─┴─
               ●  bulb (sphere)

The shade is modelled as a ``difference()`` between two cylinders (outer and
inner) producing a hollow frustum whose opening angle tracks the *style* parameter.
"""

from __future__ import annotations

import textwrap
from typing import List

from engines.base_engine import BaseLampEngine
from models.parameters import LampParameters


class PendantLampEngine(BaseLampEngine):
    """Engine for pendant / hanging lamps."""

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def engine_name(self) -> str:
        return "Pendant Lamp Engine"

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
        "modern":       dict(flare=0.60, neck_r=8,  foot_r=12, facets=64),
        "industrial":   dict(flare=0.40, neck_r=10, foot_r=14, facets=8),
        "minimalist":   dict(flare=0.30, neck_r=6,  foot_r=8,  facets=64),
        "scandinavian": dict(flare=0.50, neck_r=7,  foot_r=10, facets=64),
        "vintage":      dict(flare=0.70, neck_r=9,  foot_r=12, facets=32),
        "art_deco":     dict(flare=0.80, neck_r=11, foot_r=16, facets=12),
        "rustic":       dict(flare=0.55, neck_r=10, foot_r=14, facets=16),
        "futuristic":   dict(flare=0.20, neck_r=6,  foot_r=8,  facets=6),
    }

    def _style(self, params: LampParameters) -> dict:
        return self._STYLE_PROFILES.get(params.style, self._STYLE_PROFILES["modern"])

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, params: LampParameters) -> str:
        sp = self._style(params)

        shade_h    = params.height_mm * 0.45
        shade_r_top = params.width_mm * 0.10
        shade_r_bot = params.width_mm * 0.50 * sp["flare"]
        thickness  = params.shade_thickness_mm
        cord_h     = params.cord_length_mm
        mount_r    = params.base_diameter_mm * 0.30
        mount_h    = params.height_mm * 0.05
        socket_h   = params.height_mm * 0.08
        socket_r   = shade_r_top * 0.9
        bulb_r     = socket_r * 0.8
        neck_r     = sp["neck_r"]
        foot_r     = sp["foot_r"]
        fn         = sp["facets"]

        scad = self._file_header(params)
        scad += textwrap.dedent(
            f"""
            // --- Parameters ---
            shade_h     = {shade_h:.2f};
            shade_r_top = {shade_r_top:.2f};
            shade_r_bot = {shade_r_bot:.2f};
            thickness   = {thickness:.2f};
            cord_h      = {cord_h:.2f};
            mount_r     = {mount_r:.2f};
            mount_h     = {mount_h:.2f};
            socket_h    = {socket_h:.2f};
            socket_r    = {socket_r:.2f};
            bulb_r      = {bulb_r:.2f};
            neck_r      = {neck_r:.2f};
            foot_r      = {foot_r:.2f};
            fn          = {fn};

            // --- Ceiling Mount ---
            color("{params.color}")
            translate([0, 0, cord_h + shade_h + mount_h])
                cylinder(h=mount_h, r1=mount_r, r2=mount_r, center=false, $fn=fn);

            // --- Hanging Cord ---
            color("darkgray")
            translate([0, 0, shade_h])
                cylinder(h=cord_h, r1=neck_r/4, r2=neck_r/4, center=false, $fn=fn);

            // --- Shade (hollow frustum) ---
            color("{params.color}")
            difference() {{
                cylinder(h=shade_h, r1=shade_r_bot, r2=shade_r_top, center=false, $fn=fn);
                translate([0, 0, thickness])
                    cylinder(h=shade_h, r1=shade_r_bot - thickness,
                             r2=shade_r_top - thickness, center=false, $fn=fn);
            }}

            // --- Socket ---
            color("silver")
            translate([0, 0, -socket_h])
                cylinder(h=socket_h, r1=socket_r, r2=socket_r * 0.7, center=false, $fn=fn);

            // --- Bulb ---
            color("lightyellow", 0.6)
            translate([0, 0, -socket_h - bulb_r])
                sphere(r=bulb_r, $fn=fn);
            """
        )
        return scad
