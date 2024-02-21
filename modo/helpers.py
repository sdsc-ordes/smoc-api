from enum import Enum
import re
from urllib.parse import urlparse
from typing import Mapping, Any

import modo_schema.datamodel as model

from .introspection import load_schema


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


class ElementType(str, Enum):
    """Enumeration of element types."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"
    REFERENCE_GENOME = "reference"

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
        else:
            raise ValueError(f"Unknown element type: {self}")


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
