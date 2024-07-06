"""Utilities to interact with genomic intervals in CRAM files."""

from pathlib import Path
from typing import Iterator, List, Optional

from pysam import (
    AlignedSegment,
    AlignmentFile,
    VariantRecord,
)
from urllib.parse import urlparse
import modos_schema.datamodel as model

import re
import htsget
from .formats import (
    GenomicFileSuffix,
)
from ..helpers.region import Region
from io import BytesIO


def slice_genomics(
    path: str,
    region: Optional[Region] = None,
    reference_filename: Optional[str] = None,
    output_filename: Optional[str] = None,
) -> Optional[Iterator[AlignedSegment | VariantRecord]]:
    """Returns an iterable slice of the CRAM, VCF or BCF file,
    or saves it to a local file."""

    ...


def slice_remote_genomics(
    url: str,
    region: Optional[Region] = None,
    reference_filename: Optional[str] = None,
    output_filename: Optional[str] = None,
) -> Optional[Iterator[AlignedSegment | VariantRecord]]:
    """Stream or write to a local file a slice of a remote CRAM or VCF/BCF file"""

    ...


def extract_cram_metadata(cram: AlignmentFile) -> List:
    """Extract metadata from the CRAM file header and
    convert specific attributes according to the modo schema."""
    cram_head = cram.header
    ref_list: List = []
    for refseq in cram_head.get("SQ"):
        refseq_mod = model.ReferenceSequence(
            id=create_sequence_id(refseq.get("SN"), refseq.get("M5")),
            name=refseq.get("SN"),
            sequence_md5=refseq.get("M5"),
            source_uri=refseq.get("UR"),
            description=refseq.get("DS"),
        )
        ref_list.append(refseq_mod)
    # NOTE: Could also extract species name, sample name, sequencer etc. here
    return ref_list


def validate_cram_files(cram_path: str):
    """Validate CRAM files using pysam.
    Checks if the file is sorted and has an index."""
    # NOTE: Not a priority
    # TODO:
    # Check if sorted
    # Check if index exists
    # Check if reference exists


# TODO: Add functions to edit CRAM files (liftover)


def create_sequence_id(name: str, sequence_md5: str) -> str:
    """Helper function to create a unique id from a sequence name and md5 hash"""
    return name + "_" + sequence_md5[:6]
