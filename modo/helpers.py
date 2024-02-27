from enum import Enum
import re
from urllib.parse import urlparse
from typing import Mapping, Any
import zarr

import modo_schema.datamodel as model

from .introspection import get_haspart_property, load_schema


def class_from_name(name: str):
    class_names = list(load_schema().all_classes().keys())
    if name not in class_names:
        raise ValueError(f"Unknown class name: {name}")
    return getattr(model, name)


def dict_to_instance(element: Mapping[str, Any]) -> Any:
    elem_type = element.get("@type")
    target_class = class_from_name(elem_type)
    return target_class(
        **{k: v for k, v in element.items() if k not in "@type"}
    )


def set_part_of_relationship(
    element: model.DataEntity
    | model.Sample
    | model.Assay
    | model.ReferenceGenome
    | model.ReferenceSequence,
    element_path: str,
    partof_group: zarr.hierarchy.Group,
):
    """Add element to the hasPart attribute of a parent zarr group"""
    parent_type = getattr(
        model,
        partof_group.attrs.get("@type"),
    )

    has_prop = get_haspart_property(element.__class__.__name__)
    parent_slots = parent_type.__match_args__
    if has_prop not in parent_slots:
        raise ValueError(
            f"Cannot make {element.id} part of {partof_group.name}: {parent_type} does not have property {has_prop}"
        )
    # has_part is multivalued
    if has_prop not in partof_group.attrs:
        partof_group.attrs[has_prop] = []
    partof_group.attrs[has_prop] += [element_path]


class UserElementType(str, Enum):
    """Enumeration of element types exposed to the user."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"

    def get_target_class(
        self,
    ) -> type:
        """Return the target class for the element type."""
        if self == UserElementType.SAMPLE:
            return model.Sample
        elif self == UserElementType.ASSAY:
            return model.Assay
        elif self == UserElementType.DATA_ENTITY:
            return model.DataEntity
        elif self == UserElementType.REFERENCE_GENOME:
            return model.ReferenceGenome
        else:
            raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        if isinstance(obj, model.Sample):
            return UserElementType.SAMPLE
        elif isinstance(obj, model.Assay):
            return UserElementType.ASSAY
        elif isinstance(obj, model.DataEntity):
            return UserElementType.DATA_ENTITY
        elif isinstance(obj, model.ReferenceGenome):
            return UserElementType.REFERENCE_GENOME
        else:
            raise ValueError(f"Unknown object type: {type(obj)}")


class ElementType(str, Enum):
    """Enumeration of all element types."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"
    REFERENCE_SEQUENCE = "reference"

    def get_target_class(
        self,
    ) -> type:
        """Return the target class for the element type."""
        if self == ElementType.SAMPLE:
            return model.Sample
        elif self == ElementType.ASSAY:
            return model.Assay
        elif self == ElementType.DATA_ENTITY:
            return model.DataEntity
        elif self == ElementType.REFERENCE_GENOME:
            return model.ReferenceGenome
        elif self == ElementType.REFERENCE_SEQUENCE:
            return model.ReferenceSequence
        else:
            raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        if isinstance(obj, model.Sample):
            return ElementType.SAMPLE
        elif isinstance(obj, model.Assay):
            return ElementType.ASSAY
        elif isinstance(obj, model.DataEntity):
            return ElementType.DATA_ENTITY
        elif isinstance(obj, model.ReferenceGenome):
            return ElementType.REFERENCE_GENOME
        elif isinstance(obj, model.ReferenceSequence):
            return ElementType.REFERENCE_SEQUENCE
        else:
            raise ValueError(f"Unknown object type: {type(obj)}")


def is_uri(text: str):
    """Checks if input is a valid URI."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


def parse_region(region: str) -> tuple[str, int, int]:
    """Parses an input UCSC-format region string into
    (chrom, start, end).

    Examples
    --------
    >>> parse_region('chr1:10-320')
    ('chr1', 10, 320)
    >>> parse_region('chr-1ba:32-0100')
    ('chr-1ba', 32, 100)
    """

    if not re.match(r"[^:]+:[0-9]+-[0-9]+", region):
        raise ValueError(
            f"Invalid region format: {region}. Expected chr:start-end"
        )

    chrom, coords = region.split(":")
    start, end = coords.split("-")

    return (chrom, int(start), int(end))
