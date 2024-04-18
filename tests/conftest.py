"""Common fixtures for testing"""

import pytest
import modo_schema.datamodel as model
import shutil

from tempfile import TemporaryDirectory
from modo.api import MODO
from modo.io import build_modo_from_file


## A test MODO
@pytest.fixture
def test_modo(tmp_path):
    return build_modo_from_file("data/ex_config.yaml", tmp_path)


## different schema entities
@pytest.fixture
def DataEntity():
    return model.DataEntity(
        id="test_data",
        name="test_data",
        data_path="demo1.cram",
        data_format="CRAM",
    )


@pytest.fixture
def Assay():
    return model.Assay(
        id="test_assay", name="test_assay", omics_type="GENOMICS"
    )


@pytest.fixture
def Sample():
    return model.Sample(
        id="test_sample",
        name="test_sample",
        cell_type="Leukocytes",
        taxon_id="9606",
    )
