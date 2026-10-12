"""
Data Ingestion & Immutable Reader Module for Phase 3 Analysis Engine.
Guarantees raw input data immutability by creating isolated copies for analysis.
"""

import copy
import json
from typing import Any, Dict
from ..models.schema import MasterIPORecord
from ..io.json_ingestor import JSONIngestor


class IPODataReader:
    """Reads and wraps IPO datasets while guaranteeing raw data immutability."""

    def __init__(self, raw_record: MasterIPORecord):
        # Deep copy ensures original raw input data cannot be mutated by analysis steps
        self._raw_record = copy.deepcopy(raw_record)

    @property
    def raw_record(self) -> MasterIPORecord:
        """Returns a deep copy of the underlying raw MasterIPORecord."""
        return copy.deepcopy(self._raw_record)

    @classmethod
    def from_json_file(cls, filepath: str) -> "IPODataReader":
        """Loads IPO record from JSON file into an immutable reader."""
        record = JSONIngestor.from_json_file(filepath)
        return cls(record)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPODataReader":
        """Loads IPO record from dictionary into an immutable reader."""
        record = JSONIngestor.from_dict(data)
        return cls(record)
