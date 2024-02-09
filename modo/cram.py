"""Utilities to interact with genomic intervals in CRAM files."""
import re
from typing import Any, Iterator

import smoc_schema.datamodel as model
from pysam import (
    AlignedSegment,
    AlignmentFile,
    AlignmentHeader,
)
from rdflib import Graph

# MODO.slice(data: str, coords: str) will call slice(), which in turn will
# call the right slicing function depending on the data format/type that
# is being sliced (e.g., if it is a CRAM file, it will call slice_cram())


def parse_region(region: str) -> tuple[str, int, int]:
    """Parses an input UCSC-format region string into
    (chrom, start, end).

    Examples
    --------
    >>> parse_region('chr1:10-320')
    ('chr1', 10, 320)
    >>> parse_region('chr-1ba:32-0100')
    ('chr-1ba', 32, 100)
    """

    if not re.match(r"[^:]+:[0-9]+-[0-9]+", region):
        raise ValueError(
            f"Invalid region format: {region}. Expected chr:start-end"
        )

    chrom, coords = region.split(":")
    start, end = coords.split("-")

    return (chrom, int(start), int(end))


def slice_cram(cram_path: AlignmentFile, coords: str):  # -> AlignmentFile:
    """Return a slice of the CRAM File as an iterator object.

    Usage:
    -----
    >>> x = slice("data/ex1/demo1.cram", "chr1:100-200")
    >>> for read in x:
            print(read)
    """

    # split up coordinate string "chr:start-end" into its three elements
    coords = coords.replace("-", ":")
    loc, start, stop = coords.split(":")
    start = int(start)
    stop = int(stop)

    cramfile = AlignmentFile(cram_path, "rc")  # need to add pointer to
    # reference file from metadata

    iter = cramfile.fetch(loc, start, stop)

    return iter


def slice_array():  # to be defined after we get more knowledge of how the
    return None  # data looks like


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
