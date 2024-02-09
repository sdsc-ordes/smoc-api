"""Utilities to interact with genomic intervals in CRAM files."""
import re
from typing import Iterator

import smoc_schema.datamodel as model
from pysam import (
    AlignedSegment,
    AlignmentFile,
    AlignmentHeader,
)
from rdflib import Graph

from .helpers import parse_region


def slice_cram(path: str, region: str) -> Iterator[AlignedSegment]:
    """Return an iterable slice of the CRAM file."""

    chrom, start, stop = parse_region(region)
    cramfile = AlignmentFile(path, "rc")

    iter = cramfile.fetch(chrom, start, stop)

    return iter


def extract_metadata(AlignmentHeader) -> Graph:
    """Extract metadata from the CRAM file header and
    convert specific attributes to an RDF graph according
    to the modo schema."""
    # NOTE: Not a priority
    ...


def validate_cram_files(cram_path: str):
    """Validate CRAM files using pysam.
    Checks if the file is sorted and has an index."""
    # NOTE: Not a priority
    # TODO:
    # Check if sorted
    # Check if index exists
    # Check if reference exists


# TODO: Add functions to edit CRAM files (liftover)
