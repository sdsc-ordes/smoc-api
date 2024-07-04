from enum import Enum
from pathlib import Path
from typing import Optional, Iterator

from io import BytesIO
import tempfile
from pysam import (
    AlignedSegment,
    AlignmentFile,
    VariantFile,
    VariantRecord,
)

from .region import Region


class GenomicFileSuffix(tuple, Enum):
    """Enumeration of all supported genomic file suffixes."""

    CRAM = (".cram",)
    FASTA = (".fasta", ".fa")
    FASTQ = (".fastq", ".fq")
    BAM = (".bam",)
    SAM = (".sam",)
    VCF = (".vcf", ".vcf.gz")
    BCF = (".bcf",)

    @classmethod
    def from_path(cls, path: Path):
        for genome_ft in cls:
            if "".join(path.suffixes) in genome_ft.value:
                return genome_ft
        supported = [fi_format for fi_format in cls]
        raise ValueError(
            f'Unsupported file format: {"".join(path.suffixes)}.\n'
            f"Supported formats:{supported}"
        )

    def get_index_suffix(self):
        """Return the supported index suffix related to a genomic filetype"""
        match self.name:
            case "BAM" | "SAM":
                return ".bai"
            case "BCF":
                return ".csi"
            case "CRAM":
                return ".crai"
            case "FASTA" | "FASTQ":
                return ".fai"
            case "VCF":
                return ".tbi"


def file_to_pysam_object(
    path: str, fileformat: str, reference_filename: Optional[str] = None
) -> VariantFile | AlignmentFile:
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
    region: Optional[Region],
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
        pysam_iter = file_to_pysam_object(
            path=temp_file.name,
            fileformat=file_format,
            reference_filename=reference_filename,
        )
        if file_format in ("VCF", "BCF"):
            get_chrom = lambda r: r.chrom
            get_start = lambda r: r.start
        else:
            get_chrom = lambda r: r.reference_name
            get_start = lambda r: r.reference_start

        for record in pysam_iter:
            if region is None:
                yield record
                continue
            record_region = Region(
                get_chrom(record), get_start(record), get_start(record)
            )
            if not record_region.overlaps(region):
                continue
            yield record


def iter_to_file(
    gen_iter: Iterator[AlignedSegment | VariantRecord],
    infile,  # [AlignmentFile | VariantFile]
    output_filename: str,
    reference_filename: Optional[str] = None,
):
    out_fileformat = GenomicFileSuffix.from_path(Path(output_filename)).name
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
