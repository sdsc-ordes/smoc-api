"""Utilities to manage data files associated with model instances"""

from pysam import AlignmentFile
from smoc_schema.datamodel import DataEntity
from typing import Mapping, List

from .cram import extract_cram_metadata


def extract_metadata(instance) -> List:
    """Extract metadata from files associated to a model instance"""
    if (
        isinstance(instance, DataEntity)
        and str(instance.data_format) == "CRAM"
    ):
        reference = (
            instance.has_reference
            if len(instance.has_reference) == 1
            else None
        )
        cramfile = AlignmentFile(
            instance.data_path, mode="rc", reference_filename=reference
        )
        return extract_cram_metadata(cramfile)
    # elif isinstance(instance, DataEntity)
    # and instance.data_format in ["FASTQ", "FASTA"]:
    else:
        return []
