"""Utilities to manage data files associated with model instances"""

from pysam import AlignmentFile
from smoc_schema.datamodel import DataEntity
from typing import List

from .cram import extract_cram_metadata

extraction_formats = ["CRAM"]


def extract_metadata(instance) -> List:
    """Extract metadata from files associated to a model instance"""
    if not isinstance(instance, DataEntity):
        raise ValueError(f"{instance} is not a DataEntity, cannot extract")
    match str(instance.data_format):
        case "CRAM":
            reference = (
                instance.has_reference
                if len(instance.has_reference) == 1
                else None
            )
            cramfile = AlignmentFile(
                instance.data_path, mode="rc", reference_filename=reference
            )
            return extract_cram_metadata(cramfile)
        case _:
            raise ValueError(
                f"Unsupported data format: {instance.data_format}"
            )
