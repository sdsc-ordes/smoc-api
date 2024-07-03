from enum import Enum
from typing import Any, Mapping
from urllib.parse import urlparse
import zarr

import modos_schema.datamodel as model

from ..introspection import get_haspart_property, get_slot_range, load_schema


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


def is_full_id(element_id: str) -> bool:
    """Checks if an element_id contains the element type as prefix.

    Examples
    --------
    >>> is_full_id("sample1")
    False
    >>> is_full_id("data/test")
    True
    >>> is_full_id("/assay/test_assay")
    True
    """
    etypes = [elem.value + "/" for elem in ElementType]
    extended_etypes = etypes + ["/" + etype for etype in etypes]
    return element_id.startswith(tuple(extended_etypes))


def set_haspart_relationship(
    child_class: str,
    child_path: str,
    parent_group: zarr.hierarchy.Group,
):
    """Add element to the hasPart attribute of a parent zarr group"""
    parent_type = getattr(
        model,
        parent_group.attrs.get("@type"),
    )

    has_prop = get_haspart_property(child_class)
    parent_slots = parent_type.__match_args__
    if has_prop not in parent_slots:
        raise ValueError(
            f"Cannot make {child_path} part of {parent_group.name}: {parent_type} does not have property {has_prop}"
        )
    # has_part is multivalued
    if has_prop not in parent_group.attrs:
        parent_group.attrs[has_prop] = []
    parent_group.attrs[has_prop] += [child_path]


def update_haspart_id(
    element: model.DataEntity
    | model.Sample
    | model.Assay
    | model.ReferenceGenome
    | model.MODO,
):
    """update the id of the has_part property of an element to use the full id including its type"""
    haspart_names = load_schema().slot_children("has_part")
    haspart_list = [
        haspart for haspart in haspart_names if haspart in vars(element).keys()
    ]
    if len(haspart_list) > 0:
        for has_part in haspart_list:
            haspart_type = get_slot_range(has_part)
            type_name = ElementType.from_model_name(haspart_type).value
            updated_ids = [
                id if is_full_id(id) else f"{type_name}/{id}"
                for id in getattr(element, has_part)
            ]
            setattr(element, has_part, updated_ids)
    return element


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
        match self:
            case UserElementType.SAMPLE:
                return model.Sample
            case UserElementType.ASSAY:
                return model.Assay
            case UserElementType.DATA_ENTITY:
                return model.DataEntity
            case UserElementType.REFERENCE_GENOME:
                return model.ReferenceGenome
            case _:
                raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        match obj:
            case model.Sample():
                return UserElementType.SAMPLE
            case model.Assay():
                return UserElementType.ASSAY
            case model.DataEntity():
                return UserElementType.DATA_ENTITY
            case model.ReferenceGenome():
                return UserElementType.REFERENCE_GENOME
            case _:
                raise ValueError(f"Unknown object type: {type(obj)}")


class ElementType(str, Enum):
    """Enumeration of all element types."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"
    REFERENCE_SEQUENCE = "sequence"

    def get_target_class(
        self,
    ) -> type:
        """Return the target class for the element type."""
        match self:
            case ElementType.SAMPLE:
                return model.Sample
            case ElementType.ASSAY:
                return model.Assay
            case ElementType.DATA_ENTITY:
                return model.DataEntity
            case ElementType.REFERENCE_GENOME:
                return model.ReferenceGenome
            case ElementType.REFERENCE_SEQUENCE:
                return model.ReferenceSequence
            case _:
                raise ValueError(f"Unknown element type: {self}")

    @classmethod
    def from_object(cls, obj):
        """Return the element type from an object."""
        match obj:
            case model.Sample():
                return ElementType.SAMPLE
            case model.Assay():
                return ElementType.ASSAY
            case model.DataEntity():
                return ElementType.DATA_ENTITY
            case model.ReferenceGenome():
                return ElementType.REFERENCE_GENOME
            case model.ReferenceSequence():
                return ElementType.REFERENCE_SEQUENCE
            case _:
                raise ValueError(f"Unknown object type: {type(obj)}")

    @classmethod
    def from_model_name(cls, name: str):
        """Return the element type from an object name."""
        match name:
            case "Sample":
                return ElementType.SAMPLE
            case "Assay":
                return ElementType.ASSAY
            case "DataEntity":
                return ElementType.DATA_ENTITY
            case "ReferenceGenome":
                return ElementType.REFERENCE_GENOME
            case "ReferenceSequence":
                return ElementType.REFERENCE_SEQUENCE
            case _:
                raise ValueError(f"Unknown object type: {name}")


def is_uri(text: str):
    """Checks if input is a valid URI."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False
