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


def slice(data_name: str, data_path: str, coords: str):
    "Returns a slice of the requested region for the requested omics type"

    # get the data type (e.g., CRAM, array) of the requested data
    # data_type =    # Cyril, please add in the logic to get the data type
    # data_path =    # and the data_path from the metadata

    if data_type == "cram":
        return slice_cram(data_path, coords)
    elif data_type == "array":
        return slice_array(data_path, coords)  # To be added after we know
        # what this data looks like


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
