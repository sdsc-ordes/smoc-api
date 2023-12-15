from dataclasses import dataclass

from calamus import fields
from calamus.schema import JsonLDSchema
from rdflib import Graph
from rdflib.namespace import Namespace

SMOC = Namespace("http://smoc.ethz.ch/")
BIO = Namespace("http://bioschemas.org/")


@dataclass
class Reference(JsonLDSchema):
    location: str

    class Meta:
        rdf_type = SMOC.Reference


@dataclass
class CRAMFile(JsonLDSchema):
    location: str
    reference: Reference

    class Meta:
        rdf_type = SMOC.CRAMFile


@dataclass
class Organization(JsonLDSchema):
    name: str

    class Meta:
        rdf_type = SMOC.Organization


@dataclass
class Taxon(JsonLDSchema):
    taxid: int

    class Meta:
        rdf_type = SMOC.Taxon


@dataclass
class BioSample(JsonLDSchema):
    taxonomic_range: Taxon
    collector: Organization

    class Meta:
        rdf_type = BIO.BioSample
