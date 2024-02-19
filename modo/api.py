from datetime import date
import json
from pathlib import Path
import shutil
from typing import Generator, List, Optional
import yaml

from linkml_runtime.dumpers import json_dumper
import rdflib
import modo_schema.datamodel as model
import zarr

from .introspection import get_haspart_property
from .rdf import attrs_to_graph
from .storage import add_metadata_group, init_zarr, list_zarr_items
from .file_utils import extract_metadata, extraction_formats
from .helpers import class_from_name, dict_to_instance, ElementType


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
    ['/ex/assay1/sample1']

    # List files in the archive
    >>> sorted([file.name for file in demo.list_files()])
    ['demo1.cram', 'reference.fa']

    """

    def __init__(
        self,
        path: Path,
        archive: Optional[zarr.Group] = None,
        id_: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        creation_date: date = date.today(),
        last_update_date: date = date.today(),
        has_assay: List = [],
        source_uri: Optional[str] = None,
    ):
        self.path: Path = Path(path)
        # User provided archive
        if archive is not None:
            self.archive = archive
        # Opening existing object
        elif (self.path / "data.zarr").exists():
            self.archive = zarr.open(str(self.path / "data.zarr"))
        # Creating from scratch
        else:
            self.archive = init_zarr(self.path)
        # Opened existing object
        try:
            next(self.archive.groups())[0]
        # Creating from scratch
        except StopIteration:
            if id_ is None:
                self.id_ = self.path.name
                fields = {
                    "@type": "MODO",
                    "id": self.id_,
                    "creation_date": str(creation_date),
                    "last_update_date": str(last_update_date),
                    "name": name,
                    "description": description,
                    "has_assay": has_assay,
                    "source_uri": source_uri,
                }
                for key, val in fields.items():
                    self.archive["/"].attrs[key] = val
            zarr.consolidate_metadata(self.archive.store)

    @property
    def metadata(self) -> dict:
        # Auto refresh metadata to match data before reading
        zarr.consolidate_metadata(self.archive.store)
        root = zarr.open_consolidated(self.archive.store)

        if isinstance(root, zarr.Array):
            raise ValueError("Root must be a group. Empty archive?")

        # Get flat dictionary with all attrs, easier to search
        group_attrs = dict()
        for subgroup in root.groups():
            for name, value in list_zarr_items(subgroup[1]):
                group_attrs[name] = dict(value.attrs)
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

    def list_files(self) -> Generator[Path, None, None]:
        """Lists files in the archive recursively (except for the zarr file)."""
        for path in self.path.glob("*"):
            if path.name.endswith(".zarr"):
                continue
            elif path.is_file():
                yield path
            for file in path.rglob("*"):
                yield file

    def list_arrays(self):
        """Lists arrays in the archive recursively."""
        return self.archive.tree()

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
                    str(val).removeprefix(f"file://{self.path.name}")
                )
        return samples

    def remove_element(self, element_id: str):
        """Remove an element from the archive, along with any files
        directly attached to it and links from other elements to it.
        """
        try:
            attrs = self.archive[element_id].attrs
        except KeyError as err:
            keys = []
            self.archive.visit(lambda k: keys.append(k))
            print(f"Element {element_id} not found in the archive.")
            print(f"Available elements are {keys}")
            raise err

        # Remove data file
        if "data_path" in attrs.keys():
            data_file = self.path / attrs["data_path"]
            if data_file.exists():
                data_file.unlink()

        # Remove links from other elements
        for elem, attrs in self.metadata.items():
            for key, value in attrs.items():
                if value == element_id:
                    del self.archive[elem].attrs[key]
                elif isinstance(value, list) and element_id in value:
                    self.archive[elem].attrs[key].remove(element_id)
        zarr.consolidate_metadata(self.archive.store)

    def add_element(
        self,
        element: model.DataEntity | model.Sample | model.Assay,
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

        # Copy data file to archive and update data_path in metadata
        if data_file is not None:
            data_path = Path(data_file)
            shutil.copy(data_file, self.path / element.data_path)

        # Inferred from type inferred from type
        type_name = ElementType.from_object(element).value
        type_group = self.archive[type_name]
        element_path = f"{type_name} / {element.id}"

        if part_of is not None:
            parent_type = getattr(
                model,
                self.metadata[part_of]["@type"],
            )
            partof_group = self.archive[part_of]
            has_prop = get_haspart_property(element.__class__.__name__)
            parent_slots = parent_type.__match_args__
            if has_prop not in parent_slots:
                raise ValueError(
                    f"Cannot make {element.id} part of {part_of}: {parent_type} does not have property {has_prop}"
                )
            # has_part is multivalued
            if has_prop not in self.archive[part_of].attrs:
                partof_group.attrs[has_prop] = []
            partof_group.attrs[has_prop] += [element_path]

        # Add element to metadata
        attrs = json.loads(json_dumper.dumps(element))
        add_metadata_group(type_group, attrs)
        zarr.consolidate_metadata(self.archive.store)

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
        attrs = self.archive[element_id].attrs
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
            elements = extract_metadata(inst)
            for ele in elements:
                # NOTE: Need to compare names here as ids differ
                if (
                    ele.name not in inst_names.keys()
                    and ele not in new_elements
                ):
                    new_elements.append(ele)
                    self.add_element(ele)
                elif ele.name in inst_names.keys():
                    self.update_element(inst_names[ele.name], ele)
                else:
                    continue
