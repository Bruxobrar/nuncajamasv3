"""
Base engine contract used by SCAD-style generators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from models.parameters import LampParameters


class BaseLampEngine(ABC):
    @property
    @abstractmethod
    def engine_name(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_styles(self) -> List[str]:
        ...

    @abstractmethod
    def build(self, params: LampParameters) -> str:
        ...
