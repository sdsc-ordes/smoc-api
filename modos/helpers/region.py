import math
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass
class Region:
    """Genomic region consisting of a chromosome (aka reference) name
    and a 0-indexed half-open coordinate interval.
    Note that the end may not be specified, in which it will be set to math.inf.
    """

    chrom: str
    start: int
    end: int | float

    def __post_init__(self):
        if self.start < 0:
            raise ValueError("Start must be non-negative")
        if self.end < self.start:
            raise ValueError("End must be greater than or equal to start")

    def to_htsget_query(self):
        """Serializes the region into an htsget URL query.

        Example
        -------
        >>> Region(chrom="chr1", start=0, end=100).to_htsget_query()
        "referenceName=chr1&start=0&end=100"
        """
        query = f"referenceName={self.chrom}&start={self.start}"
        if self.end != math.inf:
            query += f"&end={self.end}"
        return query

    @classmethod
    def from_htsget_query(cls, url: str):
        """Instantiate from an htsget URL query

        Example
        -------
        >>> Region.from_htsget_query(
          "http://localhost/htsget/reads/ex/demo1?format=CRAM&referenceName=chr1&start=0
        )
        Region(chrom="chr1", start=0, end=math.inf)
        """
        query = parse_qs(urlparse(url).query)
        try:
            chrom = query["referenceName"][0]
        except KeyError:
            raise KeyError("referenceName is missing")
        start = int(query.get("start", [0])[0])
        end = float(query.get("end", [math.inf])[0])

        return Region(chrom, start, end)

    @classmethod
    def from_ucsc(cls, ucsc: str):
        """Instantiate from a UCSC-formatted region string.

        Example
        -------
        >>> Region.from_ucsc("chr1:0-100")
        Region(chrom="chr1", start=0, end=100)
        >>> parse_region('chr-1ba:10-320')
        Region(chrom='chr-1ba', start=10, end=320)
        >>> parse_region('chr1:-320')
        Region(chrom='chr1', start=0, end=320)
        >>> parse_region('chr1:10-')
        Region(chrom='chr1', start=10, end=math.inf)
        >>> parse_region('chr1:10')
        Region(chrom='chr1', start=10, end=math.inf)
        >>> parse_region('*')
        Region(chrom='*', start=0, end=math.inf)
        >>> parse_region('')
        Region(chrom='', start=0, end=math.inf)

        Note
        ----
        For more information about the UCSC coordinate system,
        see: http://genomewiki.ucsc.edu/index.php/Coordinate_Transforms
        """
        try:
            chrom, interval = ucsc.split(":")
        except ValueError:
            # no : separator -> only chrom specified
            return cls(ucsc, 0, math.inf)
        try:
            start, end = interval.split("-")
        except ValueError:
            # no - separator -> only start specified
            return cls(chrom, int(interval), math.inf)

        # Allow empty strings for start and end
        start = 0 if start == "" else int(start)
        end = math.inf if end == "" else int(end)
        return cls(chrom, start, end)
