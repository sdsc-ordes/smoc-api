# Quickstart

MODO can be used as commandline tool or python module.

First install modo using pip or use docker to run modo within a container:

::::{tab-set}

:::{tab-item} pip
:sync: pip
```{code-block} console
pip install git+https://github.com/sdsc-ordes/modo-api.git@main#egg=modo
```
:::

:::{tab-item} docker
:sync: docker
```{code-block} console
docker pull ghcr.io/sdsc-ordes/modo-api:latest
```
:::

::::

Next, you can use the modo-cli to build a new multiomics digital object (__modo__) with the id `ex`:

:::{note}
You will be prompted to complete further modo metadata information.
This command will generate the modo object in the current working directory. Use a relative path, if you want to store your object at a specific location, e.g. `modo create data/ex`
:::

::::{tab-set}

:::{tab-item} pip
:sync: pip
```{code-block} console
modo create ex
```
:::

:::{tab-item} docker
:sync: docker
```{code-block} console
docker run -e ghcr.io/sdsc-ordes/modo-api:latest create ex
```
:::

::::

To check further commands e.g. to add omics elements or interact use:

::::{tab-set}

:::{tab-item} pip
:sync: pip
```{code-block} console
modo --help
```
:::

:::{tab-item} docker
:sync: docker
```{code-block} console
docker run -e ghcr.io/sdsc-ordes/modo-api:latest --help
```
:::

::::
