from enum import Enum
from pathlib import Path
from typing import Optional

import rdflib
import zarr


# Below is an enum of omics types (genomics, transcriptomics, proteomics, metabolomics)
class OmicsType(Enum):
    GENOMICS = "smoc:Genomics"
    TRANSCRIPTOMICS = "smoc:Transcriptomics"
    PROTEOMICS = "smoc:Proteomics"
    METABOLOMICS = "smoc:Metabolomics"


class MODO:
    """Multi-Omics Digital Object
    A digital archive containing several multi-omics data and records

    Examples
    --------
    >>> from modo import MODO
    >>> modo = MODO("path/to/digital_object")
    >>> modo.list_samples()
    ["Bob", "Alice"]
    >>> modo.list_files()
    ["demo1.cram", "demo2.cram"]
    >>> modo.query("SELECT *")
    >>>
    SELECT ?path
    WHERE {
        [] rdf:type smoc:CRAMFile ;
            smoc:hasLocation ?path .
            smoc:hasSample ex:Bob .
    }
    """

    def __init__(self, path: Path):
        # self.zarr: zarr.hierarchy.Group = zarr.open(path)
        self.path: Path = path
        # TODO: Use metadata embedded in zarr file
        # so that individual arrays / groups can
        # have their own metadata
        self.metadata = rdflib.Graph().parse(Path(path / "metadata.ttl"))

    def list_samples(self):
        return self.metadata.query(
            """
            SELECT ?sample
            WHERE {
                ?sample rdf:type smoc:BioSample .
            }
            """
        )

    def list_files(self):
        return self.path.rglob("*")

    def query(self, query: str):
        """Use SPARQL to query the metadata graph"""
        return self.metadata.query(query)
