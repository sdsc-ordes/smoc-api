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


def slice(data: model.DataEntity, region: str) -> Any:
    """Returns a slice of the input data for the requested region.

    Parameters
    ----------
    data
        A data object in any supported format.
    region
        The region string in UCSC format (i.e. chr:start-end).
    """

    match data.data_format:
        case "CRAM":
            return slice_cram(data.data_path, coords)
        case _:
            raise ValueError(f"Unsupported data format: {data.data_format}")


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
