"""Utilities to interact with genomic intervals in CRAM files."""
from pathlib import Path
from pysam import AlignmentFile, AlignmentHeader
from rdflib import Graph


def slice(cram_path: AlignmentFile, coords: str) -> AlignmentFile:
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
    
    cramfile = AlignmentFile(cram_path,"rc")  # need to add pointer to 
                                              # reference file from metadata
    
    iter = cramfile.fetch(loc, start, stop)
    
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
