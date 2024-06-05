from enum import Enum
from pathlib import Path
import re
import shutil
from typing import Any, Mapping, Optional, Iterator
from urllib.parse import urlparse
import zarr

import modos_schema.datamodel as model

from .introspection import get_haspart_property, get_slot_range, load_schema

from io import BytesIO
import tempfile
from pysam import (
    AlignedSegment,
    AlignmentFile,
    VariantFile,
    VariantRecord,
)


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


def copy_file_to_archive(
    data_file: Optional[str],
    base_path: Path,
    archive_path: Optional[Path],
    remote_store: Optional[zarr.storage.FSStore] = None,
):
    if data_file is not None:
        data_path = Path(data_file)
        if remote_store:
            remote_store.put(data_path, base_path / Path(archive_path).parent)
        else:
            shutil.copy(data_path, base_path / archive_path)


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
                f"{type_name}/{id}" for id in getattr(element, has_part)
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
    REFERENCE_SEQUENCE = "sequence"

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

    @classmethod
    def from_model_name(cls, obj):
        """Return the element type from an object."""
        if obj == "Sample":
            return ElementType.SAMPLE
        elif obj == "Assay":
            return ElementType.ASSAY
        elif obj == "DataEntity":
            return ElementType.DATA_ENTITY
        elif obj == "ReferenceGenome":
            return ElementType.REFERENCE_GENOME
        elif obj == "ReferenceSequence":
            return ElementType.REFERENCE_SEQUENCE
        else:
            raise ValueError(f"Unknown object type: {obj}")


def is_uri(text: str):
    """Checks if input is a valid URI."""
    try:
        result = urlparse(text)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


def parse_region(
    region: Optional[str] = None,
) -> tuple[str, Optional[int], Optional[int]]:
    """Parses an input UCSC-format region string into
    (reference_name, start, end).

    Examples
    --------
    >>> parse_region('chr1:10-320')
    ('chr1', 10, 320)
    >>> parse_region('chr-1ba:10-320')
    ('chr-1ba', 10, 320)
    >>> parse_region('chr1:-320')
    ('chr1', None, 320)
    >>> parse_region('chr1:10-')
    ('chr1', 10, None)
    >>> parse_region('chr1:10')
    ('chr1', 10, None)
    >>> parse_region('chr1')
    ('chr1', None, None)
    >>> parse_region('*')
    ('*', None, None)
    >>> parse_region('')
    (None, None, None)
    """

    if not region:
        reference_name, start, end = None, None, None
    else:
        matches = re.match(r"^([^:]+)(:([0-9]+)?(-[0-9]*)?)?$", region.strip())
        if not matches:
            raise ValueError(
                f"Invalid region format: {region}. Expected 'chr:start-end' (start/end optional)"
            )

        reference_name, _, start, end = matches.groups()
        if start:
            start = int(start)
        if end:
            end = end.replace("-", "")
            end = None if end == "" else int(end)

    return (reference_name, start, end)


def get_fileformat(path: str) -> Optional[str]:
    """Return the file format"""
    pattern = re.compile(r"\S+\.vcf(\.\w+)?")
    if path.endswith(("fasta", "fa")):
        file_format = "FASTA"
    elif path.endswith(("fastq", "fq")):
        file_format = "FASTQ"
    elif path.endswith(".cram"):
        file_format = "CRAM"
    elif path.endswith(".bam"):
        file_format = "BAM"
    elif path.endswith(".sam"):
        file_format = "SAM"
    elif pattern.match(path):  # .vcf/.vcf.gz (or other compression)
        file_format = "VCF"
    elif path.endswith(".bcf"):
        file_format = "BCF"
    else:
        file_format = None
    return file_format


def file_to_pysam_object(
    path: str, fileformat: str, reference_filename: Optional[str] = None
):
    """Create a pysam AlignmentFile of VariantFile"""
    if fileformat == "CRAM":
        pysam_file = AlignmentFile(
            path, "rc", reference_filename=reference_filename
        )
    elif fileformat in ("VCF", "BCF"):
        pysam_file = VariantFile(path, "rb")
    else:
        raise ValueError(
            "Unsupported input file type. Supported files: CRAM, VCF, BCF"
        )
    return pysam_file


def bytesio_to_iterator(
    bytesio_buffer: BytesIO,
    file_format: str,
    reference_filename: Optional[str] = None,
) -> Iterator[AlignedSegment | VariantRecord]:
    """Takes a BytesIO buffer and returns a pysam
    AlignedSegment or VariantRecord iterator"""
    # Create a temporary file to write the bytesio data
    with tempfile.NamedTemporaryFile() as temp_file:
        # Write the contents of the BytesIO buffer to the temporary file
        temp_file.write(bytesio_buffer.getvalue())

        # Seek to the beginning of the temporary file
        temp_file.seek(0)

        # Open the temporary file as a pysam.AlignmentFile/VarianFile object
        pysam_file = file_to_pysam_object(
            path=temp_file.name,
            fileformat=file_format,
            reference_filename=reference_filename,
        )

        with pysam_file as in_file:
            # Iterate over the alignments in the file
            for line in in_file:
                yield line


def iter_to_file(
    gen_iter: Iterator[AlignedSegment | VariantRecord],
    infile,  # [AlignmentFile | VariantFile]
    output_filename: str,
    reference_filename: Optional[str] = None,
):
    out_fileformat = get_fileformat(output_filename)
    if out_fileformat in ("CRAM", "BAM", "SAM"):
        write_mode = (
            "wc"
            if out_fileformat == "CRAM"
            else ("wb" if out_fileformat == "BAM" else "w")
        )
        output = AlignmentFile(
            output_filename,
            mode=write_mode,
            template=infile,
            reference_filename=reference_filename,
        )
    elif out_fileformat in ("VCF", "BCF"):
        write_mode = "w" if out_fileformat == "VCF" else "wb"
        output = VariantFile(
            output_filename, mode=write_mode, header=infile.header
        )
    else:
        raise ValueError(
            "Unsupported output file type. Supported files: .cram, .bam, .sam, .vcf, .vcf.gz, .bcf."
        )

    for read in gen_iter:
        output.write(read)
    output.close()
