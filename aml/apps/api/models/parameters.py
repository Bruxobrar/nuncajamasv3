"""
Lamp parameter model used by class-based SCAD engines.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LampParameters:
    client_name: str = "atlas"
    style: str = "modern"
    material: str = "PLA"
    color: str = "#d8b28d"

    width_mm: float = 140.0
    height_mm: float = 180.0
    depth_mm: float = 120.0

    shade_thickness_mm: float = 2.0
    base_diameter_mm: float = 80.0
    cord_length_mm: float = 90.0
    num_arms: int = 4
