"""Utilities to interact with genomic intervals in CRAM files."""
from pathlib import Path
from pysam import AlignmentFile, AlignmentHeader
from rdflib import Graph


def slice(cram_path: AlignmentFile, coords: str) -> AlignmentFile:
    """Return a slice of the CRAM File.

    Examples
    --------
    >>> slice("data/ex1/demo1.cram", "chr1:100-200")
    """
    # https://htsget.readthedocs.io/en/stable/index.html
    ...


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
