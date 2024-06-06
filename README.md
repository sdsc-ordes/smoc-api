# modos-api

API system for using and serving Multi-Omics Digital Objects (MODOs).

## Context

### Motivation

Provide a digital object and system to process, store and serve multi-omics data with their metadata such that:
* Traceability and reproducibility is ensured by rich metadata
* The different omics layers are processed and distributed together
* Common operations such as liftover can be automated easily and ensure that omics layers are kept in sync

### Architecture

The digital object is composed of a folder with:
* Genomic data files (CRAM, FASTA)
* A zarr archive for metadata and array-based database

The metadata links the different files using the [modos-schema](https://sdsc-ordes.github.io/modos-schema).

## Installation

The development version of the library can be installed from github using pip:

```sh
pip install git+https://github.com/sdsc-ordes/modos-api.git@main
```

## Usage

The user facing API is in `modos.api`. It allows to interact with existing digital objects:

```py
from modos.api import MODO

ex = MODO('./example-digital-object')
ex.list_files()
ex.list_samples()
```


## Development

The development environment can be set up as follows:

```sh
git clone https://github.com/sdsc-ordes/modos-api && cd modos-api
make install
```

This will install dependencies and create the python virtual environment using [poetry](https://python-poetry.org/) and setup pre-commit hooks with [pre-commit](https://pre-commit.com/).

The tests can be run with `make test`, it will execute pytest with the doctest module.

## Implementation details

* To allow faster horizontal traversal of digital objects in the catalogue (e.g. for listing), the metadata should be exported in a central database/knowledge-graph on the server side.
* Metadata can be either embedded in the array file, or stored in a separate file
* Each digital object needs a unique identifier
* The paths of individual files in the digital object must be referenced in a consistent way.
  + Absolute paths are a no-go (machine/system dependent)
  + Relative paths in the digital object could work, but need to be OS-independent


## Status and limitations

* Focusing on data retrieval, remote object creation not yet implemented
* The htsget protocol supports streaming CRAM files, but it is currently only implemented for BAM in major genome browsers (igv.js, jbrowse)

## Credits

This project was developed by [SDSC](https://datascience.ch) as part of the [SMOC](http://smoc.ethz.ch) (Swiss Multi-Omics Consortium) and funded by the [PHRT](https://www.sfa-phrt.ch) ETH initiative (Personalized Health and Related technologies).

<img src="http://smoc.ethz.ch/images/smoc_mint.svg" width=100 /> <img src="https://www.sfa-phrt.ch/wp-content/uploads/2022/07/PHRT_Logo_transparent_50px.png" width=200 />
