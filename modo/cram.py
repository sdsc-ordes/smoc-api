"""Utilities to interact with genomic intervals in CRAM files."""
from pathlib import Path
from pysam import AlignmentFile, AlignmentHeader
from rdflib import Graph


def slice(cram_path: AlignmentFile, coords: str) -> AlignmentFile:
    """Return a slice of the CRAM File.

    Examples
    --------
    >>> slice(my_cram, "chr1:100-200")
    """
    ...


def extract_metadata(AlignmentHeader) -> Graph:
    ...


# TODO: Add functions to edit CRAM files (liftover)
