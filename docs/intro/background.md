# Background

## Multiomics - the (full) picture

Molecular mechanisims are highly regulated at various level. Different omic layers (genomics, transcriptomics, proteomics, metabolomics) interact and communicate with each other to establish specific phenotypes. Thus, it can be crucial to explore more than one of these layers to understand phenotypic pattern and their nuances, e.g. in the manifestation of genetic diseases. Recent advances in sequencing technologies enabled the parallel measurment of multiple omic layers from the same sample. Integrated analysis of these __multiomics__ data can help to unravel the underlying molceular mechanisms of regulation and their interactions.

## MultiOmics Digital Object (MODO)

### Features

:::{image} ../img/multiomics.png
   :align: right
   :width: 200
   :height: 200
   :alt: multiomics
:::

The main goal of `MODO` is to enable collaborative analysis and data sharing of multiomics data. Typically multiomics data are large in size, diverse in their formats and object to secure access. Thus remote storage with regulated access can be key to enable data sharing and integrated analysis.
Because of these requirements the `MODO-api` provides the following __key features__:

- queryable, linked metadata
- data and metadata synchronisation
- compression
- remote access
- streaming

### Object structure

Internally, `MODO` builds on the [zarr](https://zarr.readthedocs.io/en/stable/index.html) file storage format, that allows storage and access of chunked, compressed, N-dimensional __arrays__ alongside their __metadata__ in __hierachical groups__. All metadata can be consolidated and exported separately for querying or listing purposes. Genomics data are not stored as arrays, but can be added to the `zarr` archive in [CRAM](https://samtools.github.io/hts-specs/CRAMv3.pdf) format. CRAM is a reference-based compression format for alignment files:

:::{image} ../img/digital-object.png
   :align: center
   :width: 600
   :alt: digital-object
:::

### Remote storage

:::{image} ../img/smoc-server.png
   :align: right
   :width: 270
   :alt: smoc-server
:::

The `MODO-api` provides a server implementation to facilitate remote storage and access. This server consists of __3 main components__:
- a webserver exposing a REST api to interact with remote objects
- a htsget server to provide streaming access over network to CRAM files
- s3 bucket to allow remote random access

Detailed instructions about how to deployment can be found in the [MODO-api github project -> deploy](https://github.com/sdsc-ordes/modo-api/tree/main/deploy).
