"""Utilities to manage data files associated with model instances"""

from pysam import AlignmentFile
from modos_schema.datamodel import DataEntity
from typing import List
from pathlib import Path

from .cram import extract_cram_metadata

extraction_formats = ["CRAM"]


def extract_metadata(instance, base_path: Path) -> List:
    """Extract metadata from files associated to a model instance"""
    if not isinstance(instance, DataEntity):
        raise ValueError(f"{instance} is not a DataEntity, cannot extract")
    match str(instance.data_format):
        case "CRAM":
            cramfile = AlignmentFile(base_path / instance.data_path, mode="rc")
            return extract_cram_metadata(cramfile)
        case _:
            raise ValueError(
                f"Unsupported data format: {instance.data_format}"
            )
