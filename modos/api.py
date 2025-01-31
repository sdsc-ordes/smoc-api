from __future__ import annotations
from datetime import date
import json
import os
from pathlib import Path
import sys
from typing import Any, List, Optional, Union, Iterator
import yaml

from linkml_runtime.dumpers import json_dumper
import rdflib
import modos_schema.datamodel as model
import numcodecs
from pydantic import HttpUrl
from pysam import AlignedSegment, VariantRecord
import zarr.hierarchy
import zarr


from modos.rdf import attrs_to_graph
from modos.storage import (
    add_metadata_group,
    list_zarr_items,
    LocalStorage,
    S3Storage,
)
from modos.helpers.schema import (
    class_from_name,
    dict_to_instance,
    ElementType,
    set_data_path,
    set_haspart_relationship,
    UserElementType,
    update_haspart_id,
    generate_data_checksum,
)
from modos.genomics.formats import GenomicFileSuffix, read_pysam
from modos.genomics.htsget import HtsgetConnection
from modos.genomics.region import Region
from modos.io import extract_metadata, parse_attributes
from modos.remote import EndpointManager, is_s3_path


class MODO:
    """Multi-Omics Digital Object
    A digital archive containing several multi-omics data and records
    connected by zarr-backed metadata.

    Parameters
    ----------
    path
        Path to the archive directory.
    id
        MODO identifier.
        Defaults to the directory name.
    name
        Human-readable name.
    description
        Human readable description.
    creation_date
        When the MODO was created.
    last_update_date
        When the MODO was last updated.
    has_assay
        Existing assay identifiers to attach to MODO.
    source_uri
        URI of the source data.
    endpoint
        URL to the modos server.
    s3_kwargs
        Keyword arguments for the S3 storage.
    services
        Optional dictionary of service endpoints.

    Attributes
    ----------
    storage: Storage
        Storage backend for the archive.
    endpoint: EndpointManager
        Server endpoint manager.

    Examples
    --------
    >>> demo = MODO("data/ex")

    # List identifiers of samples in the archive
    >>> demo.list_samples()
    ['sample/sample1']

    # List files in the archive
    >>> files = [str(x) for x in demo.list_files()]
    >>> assert 'data/ex/demo1.cram' in files
    >>> assert 'data/ex/reference.fa' in files
    """

    def __init__(
        self,
        path: Union[Path, str],
        id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        creation_date: date = date.today(),
        last_update_date: date = date.today(),
        has_assay: List = [],
        source_uri: Optional[str] = None,
        endpoint: Optional[HttpUrl] = None,
        s3_kwargs: Optional[dict[str, Any]] = None,
        services: Optional[dict[str, HttpUrl]] = None,
    ):
        self.endpoint = EndpointManager(endpoint, services or {})

        if is_s3_path(str(path)):
            if not self.endpoint.s3:
                raise ValueError("S3 path requires an endpoint.")
            print(
                f"INFO: Using remote endpoint {endpoint} for {path}.",
                file=sys.stderr,
            )
            self.storage = S3Storage(str(path), self.endpoint.s3, s3_kwargs)
        else:
            # log to stderr
            print(f"INFO: Using local storage for {path}.", file=sys.stderr)
            self.storage = LocalStorage(Path(path))
        # Opening existing object
        if self.storage.empty():
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
                group_attrs[f"{group_type}/{name}"] = dict(value.attrs)
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

    def show_contents(self, element: Optional[str] = None) -> str:
        """Produces a YAML document of the object's contents.

        Parameters
        ----------
        element:
            Element, or group of elements (e.g. data or data/element_id) to show.
            If not provided, shows the metadata of the entire MODO.

        """
        meta = self.metadata

        if element in meta:
            data = meta[element]
        elif element in {g[0] for g in self.zarr.groups()}:
            data = {k: meta[k] for k in meta if k.startswith(element)}
        else:
            data = meta
        # Pretty print metadata contents as yaml

        return yaml.dump(data, sort_keys=False)

    def list_files(self) -> List[Path]:
        """Lists files in the archive recursively (except for the zarr file)."""
        return [fi for fi in self.storage.list()]

    def list_arrays(
        self, element: Optional[str] = None
    ) -> zarr.hierarchy.TreeViewer:
        """Views arrays in the archive recursively.

        Parameters
        ----------
        element:
            Element, or group of elements (e.g. data or data/element_id) to show.
            If not provided, shows the metadata of the entire MODO.
        """
        root = zarr.convenience.open_consolidated(self.zarr.store)
        return root[element or "/"].tree()

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

    def update_date(self, date: date = date.today()):
        """update last_update_date attribute"""
        self.zarr.attrs.update(last_update_date=str(date))

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

        self.update_date()
        zarr.consolidate_metadata(self.zarr.store)

    def remove_object(self):
        """Remove the complete modo object"""
        for fi in self.list_files():
            self.storage.remove(fi)
        self.zarr.store.rmdir()
        # NOTE: Locally remove the empty directory (does not affect remote).
        if self.path.exists():
            os.rmdir(self.path)
        print(f"INFO: Permanently deleted {self.path}.")

    def add_element(
        self,
        element: (
            model.DataEntity
            | model.Sample
            | model.Assay
            | model.ReferenceGenome
        ),
        source_file: Optional[Path] = None,
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
        source_file
            File to associate with the element.
        part_of
            Id of the parent element. It must be scoped to the type.
            For example "sample/foo".
        """

        self._add_any_element(
            element, source_file, part_of, allowed_elements=UserElementType
        )

    def _add_any_element(
        self,
        element: (
            model.DataEntity
            | model.Sample
            | model.Assay
            | model.ReferenceSequence
            | model.ReferenceGenome
        ),
        source_file: Optional[Path] = None,
        part_of: Optional[str] = None,
        allowed_elements: type = ElementType,
    ):
        """Add an element of any type to the storage. This is meant to be called internally to add elements automatically."""
        # Check that ID does not exist in modo
        if element.id in [Path(id).name for id in self.metadata.keys()]:
            raise ValueError(
                f"Please specify a unique ID. Element with ID {element.id} already exist."
            )

        # Copy data file to storage
        if source_file:
            source_path = Path(source_file)
            target_path = Path(element._get("data_path"))
            self.storage.put(source_path, target_path)

            # Add data_checksum attribute
            if isinstance(element, model.DataEntity):
                setattr(
                    element,
                    "data_checksum",
                    generate_data_checksum(source_file),
                )

            # Genomic files have an associated index file
            try:
                ft = GenomicFileSuffix.from_path(source_path)
                source_ix = source_path.with_suffix(
                    source_path.suffix + ft.get_index_suffix()
                )
                target_ix = target_path.with_suffix(
                    source_path.suffix + ft.get_index_suffix()
                )
                self.storage.put(source_ix, target_ix)
            except ValueError:
                pass

        # Infer type
        type_name = allowed_elements.from_object(element).value
        type_group = self.zarr[type_name]
        element_path = f"{type_name}/{element.id}"

        if part_of is not None:
            partof_group = self.zarr[part_of]
            set_haspart_relationship(
                element.__class__.__name__, element_path, partof_group
            )

        # Update haspart relationship
        element = update_haspart_id(element)

        # Add element to metadata
        attrs = json.loads(json_dumper.dumps(element))
        add_metadata_group(type_group, attrs)
        self.update_date()
        zarr.consolidate_metadata(self.zarr.store)

    def update_element(
        self,
        element_id: str,
        new: model.DataEntity | model.Sample | model.Assay | model.MODO,
        source_file: Optional[Path] = None,
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

        if isinstance(new, model.DataEntity):
            new_path = Path(new._get("data_path"))
            old_path = Path(attr_dict.get("data_path"))

            if new_path != old_path:
                self.storage.move(old_path, new_path)
            if source_file:
                source_checksum = generate_data_checksum(source_file)
                if source_checksum != attr_dict.get("data_checksum"):
                    self.storage.put(source_file, new_path)
                    new["data_checksum"] = source_checksum

        new = update_haspart_id(new)
        new = json.loads(json_dumper.dumps(new))

        # in the zarr store, empty properties are not stored
        # in the linkml model, they present as empty lists/None.
        new_items = {
            field: value
            for field, value in new.items()
            if (field, value) not in attrs.items()
            and field != "id"
            and value is not None
            and value != []
        }
        if not len(new_items):
            return
        attrs.update(**new_items)
        self.update_date()

        if source_file:

            pass

    def enrich_metadata(self):
        """Enrich MODO metadata in place using content from associated data files."""

        # TODO: match using id instead of names -> safer
        # NOTE: will require handling type prefix.
        inst_names = {
            inst["name"]: id
            for id, inst in self.metadata.items()
            if "name" in inst
        }
        for id, entity in self.metadata.items():
            if entity.get("@type") != "DataEntity":
                continue
            try:
                data_inst = dict_to_instance(entity | {"id": id})
                extracted = extract_metadata(data_inst, self.path)
            # skip entities whose format does not support enrich
            except NotImplementedError:
                continue

            new_elements = []
            for ele in extracted.elements:
                if ele.name in inst_names:
                    self.update_element(inst_names[ele.name], ele)
                elif ele not in new_elements:
                    new_elements.append(ele)
                    self._add_any_element(ele)
                else:
                    continue

            # Add arrays if the parent is not an array already.
            parent = self.zarr[id]
            if extracted.arrays is None or not isinstance(
                parent, zarr.hierarchy.Group
            ):
                continue

            # Nest arrays directly in parent group
            for name, arr in extracted.arrays.items():
                parent.create_dataset(
                    name, data=arr, object_codec=numcodecs.VLenUTF8()
                )

    def stream_genomics(
        self,
        file_path: str,
        region: Optional[str] = None,
        reference_filename: Optional[str] = None,
    ) -> Iterator[AlignedSegment | VariantRecord]:
        """Slices both local and remote CRAM, VCF (.vcf.gz), and BCF
        files returning an iterator over records."""

        _region = Region.from_ucsc(region) if region else None
        # check requested genomics file exists in MODO
        if Path(file_path) not in self.list_files():
            raise ValueError(f"{file_path} not found in {self.path}.")

        if self.endpoint.s3 and self.endpoint.htsget:
            con = HtsgetConnection(
                self.endpoint.htsget,
                Path(*Path(file_path).parts[1:]),
                region=_region,
            )
            stream = con.to_pysam(reference_filename=reference_filename)
        else:
            stream = read_pysam(
                Path(file_path),
                reference_filename=reference_filename,
                region=_region,
            )

        return stream

    @classmethod
    def from_file(
        cls,
        config_path: Path,
        object_path: str,
        endpoint: Optional[HttpUrl] = None,
        s3_kwargs: Optional[dict] = None,
        services: Optional[dict[str, HttpUrl]] = None,
        no_remove: bool = False,
    ) -> MODO:
        """build a modo from a yaml or json file"""
        element_list = parse_attributes(Path(config_path))

        # checks
        modo_count = sum(
            [ele["element"].get("@type") == "MODO" for ele in element_list]
        )
        if modo_count > 1:
            raise ValueError(
                f"There can not be more than one modo. Found {modo_count}"
            )
        ids = [ele["element"].get("id") for ele in element_list]
        if len(ids) > len(set(ids)):
            dup = {x for x in ids if ids.count(x) > 1}
            raise ValueError(
                f"Please specify unique IDs. Element(s) with ID(s) {dup} already exist."
            )

        instance_list = []
        modo_dict = {}
        for element in element_list:
            metadata = element["element"]
            args = element.get("args", {})
            if metadata.get("@type") == "MODO":
                del metadata["@type"]
                modo_dict["meta"] = metadata
                modo_dict["args"] = args
            else:
                metadata = set_data_path(metadata, args.get("source_file"))
                inst = dict_to_instance(metadata)
                instance_list.append((inst, args))

        modo = cls(
            path=object_path,
            endpoint=endpoint,
            services=services,
            s3_kwargs=s3_kwargs or {"anon": True},
            **modo_dict.get("meta", {}),
            **modo_dict.get("args", {}),
        )

        modo_ids = {Path(id).name: id for id in modo.metadata.keys()}
        for inst, args in instance_list:
            if inst.id in modo_ids.keys():
                modo.update_element(modo_ids[inst.id], inst, **args)
            else:
                modo.add_element(inst, **args)
        if no_remove:
            return modo
        modo_id = modo_id = modo.zarr["/"].attrs["id"]
        old_ids = [
            id for id in modo_ids.keys() if id not in ids and id != modo_id
        ]
        for old_id in old_ids:
            modo.remove_element(modo_ids[old_id])
        return modo
