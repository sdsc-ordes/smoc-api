from enum import Enum
from urllib.parse import urlparse

import smoc_schema.datamodel as smoc

from .introspection import load_schema


def class_from_name(name: str):
    class_names = list(load_schema().all_classes().keys())
    if name not in class_names:
        raise ValueError(f"Unknown class name: {name}")
    return getattr(smoc, name)


class ElementType(str, Enum):
    """Enumeration of element types."""

    SAMPLE = "sample"
    ASSAY = "assay"
    DATA_ENTITY = "data"

    def get_target_class(
        self,
    ) -> type[smoc.Sample | smoc.Assay | smoc.DataEntity]:
        """Return the target class for the element type."""
        if self == ElementType.SAMPLE:
            return smoc.Sample
        elif self == ElementType.ASSAY:
            return smoc.Assay
        elif self == ElementType.DATA_ENTITY:
            return smoc.DataEntity
        else:
            raise ValueError(f"Unknown element type: {self}")


def is_uri(text: str):
    """Checks if input is a valid URI."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False
