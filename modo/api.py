from enum import Enum
from pathlib import Path
from typing import Generator, Optional

import rdflib
import zarr


class MODO:
    """Multi-Omics Digital Object
    A digital archive containing several multi-omics data and records.
    The archive contains:
    * A zarr file, with array-based data
    * A metadata file, with RDF metadata describing and pointing to the actual data
    * CRAM files, with genomic-interval data

    Examples
    --------
    >>> demo = MODO("data/ex1")

    # List identifiers of samples in the archive
    >>> demo.list_samples()
    ['http://example.org/bac1', 'http://example.org/bac2']

    # List files in the archive
    >>> [file.name for file in demo.list_files()]
    ['demo1.cram', 'demo2.cram', 'ecoli_ref.fa', 'metadata.ttl', 'archive.zarr']

    # Query the metadata graph to find the location of the
    # CRAM files for the sample bac1
    >>> bac1_files = demo.query('''
    ...   SELECT ?path
    ...   WHERE {
    ...   [] rdf:type smoc:CRAMFile ;
    ...     smoc:hasSample ex:bac1 ;
    ...     smoc:hasLocation ?path .
    ... }
    ... ''').serialize(format="csv").decode()
    """

    def __init__(self, path: Path):
        # self.zarr: zarr.hierarchy.Group = zarr.open(path)
        self.path: Path = Path(path)
        # TODO: Use metadata embedded in zarr file
        # so that individual arrays / groups can
        # have their own metadata
        self.metadata = rdflib.Graph().parse(self.path / "metadata.ttl")

    def list_samples(self) -> list[str]:
        samples = self.metadata.query(
            """
            SELECT ?sample
            WHERE {
                ?sample rdf:type smoc:BioSample .
            }
            """
        )
        return [str(res.sample) for res in samples]

    def list_files(self) -> Generator[Path, None, None]:
        return self.path.rglob("*")

    def query(self, query: str):
        """Use SPARQL to query the metadata graph"""
        return self.metadata.query(query)
