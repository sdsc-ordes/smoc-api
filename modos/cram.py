"""Utilities to interact with genomic intervals in CRAM files."""

from pathlib import Path
from typing import Iterator, List, Optional

from pysam import (
    AlignedSegment,
    AlignmentFile,
    VariantRecord,
)
from urllib.parse import urlparse
import modos_schema.datamodel as model

import re
from .helpers.genomics import (
    GenomicFileSuffix,
    file_to_pysam_object,
    bytesio_to_iterator,
    iter_to_file,
)
from .helpers.region import Region
from io import BytesIO


def slice_genomics(
    path: str,
    region: Optional[Region] = None,
    reference_filename: Optional[str] = None,
    output_filename: Optional[str] = None,
) -> Optional[Iterator[AlignedSegment | VariantRecord]]:
    """Returns an iterable slice of the CRAM, VCF or BCF file,
    or saves it to a local file."""

    fileformat = GenomicFileSuffix.from_path(Path(path)).name

    infile = file_to_pysam_object(
        path=path, fileformat=fileformat, reference_filename=reference_filename
    )

    coords = region.to_tuple() if region else (None, None, None)
    gen_iter = infile.fetch(*coords)

    if output_filename:
        iter_to_file(
            gen_iter=gen_iter,
            infile=infile,
            output_filename=output_filename,
            reference_filename=reference_filename,
        )

    return gen_iter


def slice_remote_genomics(
    url: str,
    region: Optional[Region] = None,
    reference_filename: Optional[str] = None,
    output_filename: Optional[str] = None,
) -> Optional[Iterator[AlignedSegment | VariantRecord]]:
    """Stream or write to a local file a slice of a remote CRAM or VCF/BCF file"""

    parsed = urlparse(url)
    path = parsed.path
    in_fileformat = GenomicFileSuffix.from_path(Path(path)).name
    if in_fileformat not in ("CRAM", "VCF", "BCF") or path.endswith(".vcf"):
        raise ValueError(
            "Unsupported file type. Streaming/Saving remote genomic files support remote .cram, .vcf.gz, .bcf files."
        )
    # remove aditional extensions, e.g., .vcf.gz -> .vcf
    path_noext = str(
        Path(re.sub(r"\.vcf\.\w+$", ".vcf", path)).with_suffix("")
    )
    parsed = parsed._replace(path=path_noext)

    htsget_response_buffer = BytesIO()
    chrom, start, end = region.to_tuple() if region else (None, None, None)
    htsget.get(
        url=parsed.geturl(),
        output=htsget_response_buffer,  # sys.stdout.buffer,
        data_format=in_fileformat,
        reference_name=chrom,
        start=start,
        end=end,
    )

    htsget_response_buffer.seek(0)

    # To save remote slice to a local file without converting data type
    if output_filename:
        out_fileformat = GenomicFileSuffix.from_path(
            Path(output_filename)
        ).name
        if out_fileformat == in_fileformat:
            with open(output_filename, "wb") as output:
                for chunk in htsget_response_buffer:
                    output.write(chunk)
            return None
        else:
            raise ValueError(
                "Saving remote files does not support file format conversion. If needed, please use pysam or samtools to convert format of saved file."
            )

    genome__iter = bytesio_to_iterator(
        htsget_response_buffer,
        file_format=in_fileformat,
        region=region,
        reference_filename=reference_filename,
    )

    return genome__iter


def extract_cram_metadata(cram: AlignmentFile) -> List:
    """Extract metadata from the CRAM file header and
    convert specific attributes according to the modo schema."""
    cram_head = cram.header
    ref_list: List = []
    for refseq in cram_head.get("SQ"):
        refseq_mod = model.ReferenceSequence(
            id=create_sequence_id(refseq.get("SN"), refseq.get("M5")),
            name=refseq.get("SN"),
            sequence_md5=refseq.get("M5"),
            source_uri=refseq.get("UR"),
            description=refseq.get("DS"),
        )
        ref_list.append(refseq_mod)
    # NOTE: Could also extract species name, sample name, sequencer etc. here
    return ref_list


def validate_cram_files(cram_path: str):
    """Validate CRAM files using pysam.
    Checks if the file is sorted and has an index."""
    # NOTE: Not a priority
    # TODO:
    # Check if sorted
    # Check if index exists
    # Check if reference exists


# TODO: Add functions to edit CRAM files (liftover)


def create_sequence_id(name: str, sequence_md5: str) -> str:
    """Helper function to create a unique id from a sequence name and md5 hash"""
    return name + "_" + sequence_md5[:6]
