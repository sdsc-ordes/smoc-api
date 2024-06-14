from datetime import date
import json
from pathlib import Path
from typing import List, Optional, Union, Iterator
import yaml

from linkml_runtime.dumpers import json_dumper
import rdflib
import modos_schema.datamodel as model
import zarr.hierarchy
import zarr
import re

from pysam import AlignedSegment, VariantRecord

from .rdf import attrs_to_graph
from .storage import (
    add_metadata_group,
    list_zarr_items,
    LocalStorage,
    S3Storage,
)
from .file_utils import extract_metadata, extraction_formats
from .helpers import (
    class_from_name,
    dict_to_instance,
    ElementType,
    set_haspart_relationship,
    UserElementType,
    GenomicFileFormat,
)
from .cram import slice_genomics, slice_remote_genomics


class MODO:
    """Multi-Omics Digital Object
    A digital archive containing several multi-omics data and records.
    The archive contains:
    * A zarr file, array-based data and metadata pointing to arrays and data files
    * CRAM files, with genomic-alignments data

    Examples
    --------
    >>> demo = MODO("data/ex")

    # List identifiers of samples in the archive
    >>> demo.list_samples()
    ['/sample/sample1']

    # List files in the archive
    >>> files = sorted(demo.list_files())
    >>> assert Path('data/ex/demo1.cram') in files
    >>> assert Path('data/ex/reference1.fa') in files

    """

    def __init__(
        self,
        path: Union[Path, str],
        s3_endpoint: Optional[str] = None,
        s3_kwargs: Optional[dict] = None,
        htsget_endpoint: Optional[str] = None,
        id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        creation_date: date = date.today(),
        last_update_date: date = date.today(),
        has_assay: List = [],
        source_uri: Optional[str] = None,
    ):
        self.htsget_endpoint = htsget_endpoint

        if s3_endpoint and not htsget_endpoint:
            htsget_endpoint = re.sub(r"s3$", "htsget", s3_endpoint)

        if s3_endpoint:
            self.storage = S3Storage(path, s3_endpoint, s3_kwargs)
        else:
            self.storage = LocalStorage(path)
        # Opening existing object
        if not "id" in self.zarr.attrs.keys():
            self.id = id or self.path.name
            fields = {
                "@type": "MODO",
                "id": self.id,
                "creation_date": str(creation_date),
                "last_update_date": str(last_update_date),
                "name": name,
                "description": description,
                "has_assay": has_assay,
                "source_uri": source_uri,
            }
            for key, val in fields.items():
                if val:
                    self.zarr["/"].attrs[key] = val
            zarr.consolidate_metadata(self.zarr.store)

    @property
    def zarr(self) -> zarr.hierarchy.Group:
        return self.storage.zarr

    @property
    def path(self) -> Path:
        return self.storage.path

    @property
    def metadata(self) -> dict:
        # Auto refresh metadata to match data before reading
        zarr.consolidate_metadata(self.zarr.store)
        root = zarr.convenience.open_consolidated(self.zarr.store)

        if isinstance(root, zarr.core.Array):
            raise ValueError("Root must be a group. Empty archive?")

        # Get flat dictionary with all attrs, easier to search
        group_attrs = dict()
        # Document object itself
        root_id = root["/"].attrs["id"]
        group_attrs[root_id] = dict(root["/"].attrs)
        for subgroup in root.groups():
            group_type = subgroup[0]
            for name, value in list_zarr_items(subgroup[1]):
                group_attrs[f"/{group_type}/{name}"] = dict(value.attrs)
        return group_attrs

    def knowledge_graph(
        self, uri_prefix: Optional[str] = None
    ) -> rdflib.Graph:
        """Return an RDF graph of the metadata. All identifiers
        are converted to valid URIs if needed."""
        if uri_prefix is None:
            uri_prefix = f"file://{self.path.name}/"
        kg = attrs_to_graph(self.metadata, uri_prefix=uri_prefix)
        return kg

    def show_contents(self):
        """human-readable print of the object's contents"""
        meta = self.metadata
        # Pretty print metadata contents as yaml

        return yaml.dump(meta, sort_keys=False)

    def list_files(self) -> List[Path]:
        """Lists files in the archive recursively (except for the zarr file)."""
        return [fi for fi in self.storage.list()]

    def list_arrays(self):
        """Lists arrays in the archive recursively."""
        root = zarr.convenience.open_consolidated(self.zarr.store)
        return root.tree()

    def query(self, query: str):
        """Use SPARQL to query the metadata graph"""
        return self.knowledge_graph().query(query)

    def list_samples(self):
        """Lists samples in the archive."""
        res = self.query("SELECT ?s WHERE { ?s a modos:Sample }")
        samples = []
        for row in res:
            for val in row:
                samples.append(
                    str(val).removeprefix(f"file://{self.path.name}/")
                )
        return samples

    def remove_element(self, element_id: str):
        """Remove an element from the archive, along with any files
        directly attached to it and links from other elements to it.
        """
        try:
            attrs = self.zarr[element_id].attrs
        except KeyError as err:
            keys = []
            self.zarr.visit(lambda k: keys.append(k))
            print(f"Element {element_id} not found in the archive.")
            print(f"Available elements are {keys}")
            raise err

        # Remove data file
        if "data_path" in attrs.keys():
            data_file = self.path / attrs["data_path"]
            self.storage.remove(data_file)

        # Remove element group
        del self.zarr[element_id]

        # Remove links from other elements
        for elem, attrs in self.metadata.items():
            for key, value in attrs.items():
                if value == element_id:
                    del self.zarr[elem].attrs[key]
                elif isinstance(value, list) and element_id in value:
                    self.zarr[elem].attrs[key] = value.remove(element_id)

        zarr.consolidate_metadata(self.zarr.store)

    def add_element(
        self,
        element: (
            model.DataEntity
            | model.Sample
            | model.Assay
            | model.ReferenceGenome
        ),
        data_file: Optional[Path] = None,
        part_of: Optional[str] = None,
    ):
        """Add an element to the archive.
        If a data file is provided, it will be added to the archive.
        If the element is part of another element, the parent metadata
        will be updated.

        Parameters
        ----------
        element
            Element to add to the archive.
        data_file
            File to associate with the element.
        part_of
            Id of the parent element. It must be scoped to the type.
            For example "sample/foo".
        """
        # Check that ID does not exist in modo
        if element.id in [Path(id).name for id in self.metadata.keys()]:
            raise ValueError(
                f"Please specify a unique ID. Element with ID {element.id} already exist."
            )

        # Copy data file to storage and update data_path in metadata
        if data_file:
            self.storage.put(data_file, Path(element._get("data_path")))

        # Inferred from type
        type_name = UserElementType.from_object(element).value
        type_group = self.zarr[type_name]
        element_path = f"{type_name}/{element.id}"

        if part_of is not None:
            partof_group = self.zarr[part_of]
            set_haspart_relationship(
                element.__class__.__name__, element_path, partof_group
            )

        # Add element to metadata
        attrs = json.loads(json_dumper.dumps(element))
        add_metadata_group(type_group, attrs)
        zarr.consolidate_metadata(self.zarr.store)

    def _add_any_element(
        self,
        element: (
            model.DataEntity
            | model.Sample
            | model.Assay
            | model.ReferenceSequence
            | model.ReferenceGenome
        ),
        data_file: Optional[Path] = None,
        part_of: Optional[str] = None,
    ):
        """Add an element of any type to the storage."""
        # Check that ID does not exist in modo
        if element.id in [Path(id).name for id in self.metadata.keys()]:
            raise ValueError(
                f"Please specify a unique ID. Element with ID {element.id} already exist."
            )

        # Copy data file to storage and update data_path in metadata
        if data_file:
            self.storage.put(data_file, Path(element._get("data_path")))

        # Inferred from type inferred from type
        type_name = ElementType.from_object(element).value
        type_group = self.zarr[type_name]
        element_path = f"{type_name}/{element.id}"

        if part_of is not None:
            partof_group = self.zarr[part_of]
            set_haspart_relationship(
                element.__class__.__name__, element_path, partof_group
            )

        # Add element to metadata
        attrs = json.loads(json_dumper.dumps(element))
        add_metadata_group(type_group, attrs)
        zarr.consolidate_metadata(self.zarr.store)

    def update_element(
        self,
        element_id: str,
        new: model.DataEntity | model.Sample | model.Assay | model.MODO,
    ):
        """Update element metadata in place by adding new values from model object.

        Parameters
        -----------------
        element_id
            Full id path in the zarr store.
        new
            Element containing the enriched metadata.
        """
        attrs = self.zarr[element_id].attrs
        attr_dict = attrs.asdict()
        if not isinstance(new, class_from_name(attr_dict.get("@type"))):
            raise ValueError(
                f"Class {attr_dict['@type']} of {element_id} does not match {new.class_name}."
            )
        # in the zarr store, empty properties are not stored
        # in the linkml model, they present as empty lists/None.
        new_items = {
            field: value
            for field, value in new._items()
            if field not in attrs.keys()
            and field != "id"
            and value is not None
            and value != []
        }
        attrs.update(**new_items)

    def enrich_metadata(self):
        """Add metadata and corresponding elements extracted from object associated data to the MODO object"""
        new_elements = []
        instances = [
            dict_to_instance(entity | {"id": id})
            for id, entity in self.metadata.items()
            if entity.get("@type") == "DataEntity"
            and entity.get("data_format") in extraction_formats
        ]
        inst_names = {inst.name: inst.id for inst in instances}
        for inst in instances:
            elements = extract_metadata(inst, self.path)
            for ele in elements:
                # NOTE: Need to compare names here as ids differ
                if (
                    ele.name not in inst_names.keys()
                    and ele not in new_elements
                ):
                    new_elements.append(ele)
                    self._add_any_element(ele)
                elif ele.name in inst_names.keys():
                    self.update_element(inst_names[ele.name], ele)
                else:
                    continue

    def stream_genomics(
        self,
        file_path: str,
        region: Optional[str] = None,
        reference_filename: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> Optional[Iterator[AlignedSegment | VariantRecord]]:
        """Slices both local and remote CRAM, VCF (.vcf.gz), and BCF
        files returning an iterator or saving to local file."""

        # check requested genomics file exists in MODO
        if Path(file_path) not in self.list_files():
            raise ValueError(f"{file_path} not found in {self.path}.")


        if self.htsget_endpoint:
            match GenomicFileFormat.from_filepath(Path(file_path)).name:
                case "CRAM":
                    endpoint_type = "/reads/"
                case "VCF" | "BCF":
                    endpoint_type = "/variants/"

            # http://domain/s3 + bucket/modo/file.cram --> http://domain/htsget/reads/modo/file.cram
            # or               + bucket/modo/file.vcf.gz --> http://domain/htsget/variants/modo/file.vcf.gz
            url = (
                self.htsget_endpoint
                + endpoint_type  # /reads/ or /variants/
                + str(Path(*Path(file_path).parts[1:]))
            )

            gen_iter = slice_remote_genomics(
                url=url,
                region=region,
                reference_filename=reference_filename,
                output_filename=output_filename,
            )
        else:
            # assuming user did not change directory, filepath should be the
            # relative path to the file.
            # for the time being, we do not check the validity of the supplied reference_filename, or
            # the reference given in the CRAM header (used if reference not supplied by user).

            gen_iter = slice_genomics(
                path=file_path,
                region=region,
                reference_filename=reference_filename,
                output_filename=output_filename,
            )

        return gen_iter
