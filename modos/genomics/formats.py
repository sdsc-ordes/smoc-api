from enum import Enum
from pathlib import Path


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
