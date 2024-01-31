"""Utilities to interact with genomic intervals in CRAM files."""
from pathlib import Path
from pysam import AlignmentFile, AlignmentHeader
from rdflib import Graph
from Typing import List


def slice(cram_path: AlignmentFile, coords: str) -> AlignmentFile:
    """Return a slice of the CRAM File.

    Examples
    --------
    >>> slice("data/ex1/demo1.cram", "chr1:100-200")
    """
    # https://htsget.readthedocs.io/en/stable/index.html
    ...


def extract_metadata(cram: AlignmentFile) -> Graph:
    """Extract metadata from the CRAM file header and
    convert specific attributes to an RDF graph according
    to the modo schema."""
    # metadata related to ReferenceSequences
    cram_head = cram.header
    refseq_list: List = []
    species = set()
    for refseq in cram_head.get("SQ"):
        refseq_dict = {
            "name": refseq.get("SN"),
            "sequence_md5": refseq.get("M5"),
            "source_uri": refseq.get("UR"),
            "description": refseq.get("DS"),
        }
        refseq_list.append(refseq_dict)
        species.add(refseq.get("SP"))
    # metadata related to RefrenceGenome
    source_uri = cram.reference_filename
    # could use taxonkid (https://bioinf.shenwei.me/taxonkit/usage/#name2taxid)
    # but maybe to much overhead?
    species = list(species)
    # Metadata related to or sample object
    sample_names = list(set([seq.get("SM") for seq in cram_head.get("RG")]))


def validate_cram_files(cram_path: str):
    """Validate CRAM files using pysam.
    Checks if the file is sorted and has an index."""
    # NOTE: Not a priority
    # TODO:
    # Check if sorted
    # Check if index exists
    # Check if reference exists


# TODO: Add functions to edit CRAM files (liftover)
