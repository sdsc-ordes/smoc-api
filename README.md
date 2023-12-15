# SMOC-PoC

Initial system for creating and serving multi-omics digital objects.

## Context

### Motivation

Provide a digital object and system to process, store and serve multi-omics data with their metadata such that:
* Traceability and reproducibility is ensured by rich metadata
* The different omics layers are processed and distributed together
* Common operations such as liftover can be automated easily and ensure that omics layers are kept in sync

### Architecture

The digital object is composed of multiple files:
* CRAM files for alignment data, Zarr
* Zarr for array data
* RDF for metadata (either separate, or embedded in the array file).

The basic structure is as follows:

```mermaid

flowchart LR;

subgraph smoc[SMOC server]
    OBJ[Digital object metadata]
    CRAMG[Genomics CRAM]
    CRAMT[Transcriptomics CRAM]
    MATP[Proteomics matrix]
    MATM[Metabolomics matrix]
end;
subgraph UI[User interface]
    CAT[Catalogue]
    INS[Inspector]
end;

    OBJ -.-> CRAMG;
    OBJ -.-> CRAMT;
    OBJ -.-> MATP;
    OBJ -.-> MATM;
    OBJ -->|list objects| CAT
    OBJ -->|display metadata| INS
```

## Installation

The development version of the library can be installed from github using pip:

```sh
pip install git+https://github.com/sdsc-ordes/smoc-poc.git@main#egg=modo
```

## Usage

The user facing API is in `modo.api`. It allows to interact with existing digital objects:

```py
from modo.api import MODO

ex = MODO('./example-digital-object')
ex.list_files()
ex.list_samples()
```

Creating digital objects via the API is not yet supported.

## Development

The development environment can be set up as follows:

```sh
git clone https://github.com/sdsc-orders/smoc-poc && cd smoc-poc
make install
```

This will install dependencies and create the python virtual environment using [poetry](https://python-poetry.org/) and setup pre-commit hooks with [pre-commit](https://pre-commit.com/).

The tests can be run with `make test`, it will execute pytest with the doctest module.

## Implementation details

* To allow horizontal traversal of digital objects in the database (e.g. for listing), the metadata would need to be exported in a central database/knowledge-graph on the server side.
* Metadata can be either embedded in the array file, or stored in a separate file
* Each digital object needs a unique identifier
* The paths of individual files in the digital object must be referenced in a consistent way.
  + Absolute paths are a no-go (machine/system dependent)
  + Relative paths in the digital object could work, but need to be OS-independent
 

## Status and limitations

* Focusing on data retrieval, object creation not yet implemented
* The htsget protocol supports streaming CRAM files, but it is currently only implemented for BAM in major genome browsers (igv.js, jbrowse)
