"""Common fixtures for testing"""

import pytest
import modo_schema.datamodel as model
import shutil

from modo.io import build_modo_from_file


## A test MODO
@pytest.fixture
def test_modo(tmp_path):
    modo = build_modo_from_file("data/ex_config.yaml", tmp_path)
    # TODO: This should be automatically copied. Remove when issue is solved!
    shutil.copyfile(
        "data/ex/demo1.cram.crai", str(tmp_path) + "/demo1.cram.crai"
    )
    return modo


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
def data_json(DataEntity):
    data_json = DataEntity._as_json_obj()
    data_json.update({"data_format": "CRAM"})
    return str(data_json).replace("'", '"')


@pytest.fixture
def Assay():
    return model.Assay(
        id="test_assay", name="test_assay", omics_type="GENOMICS"
    )


@pytest.fixture
def assay_json(Assay):
    assay_json = Assay._as_json_obj()
    assay_json.update({"omics_type": "GENOMICS"})
    return str(assay_json).replace("'", '"')


@pytest.fixture
def Sample():
    return model.Sample(
        id="test_sample",
        name="test_sample",
        cell_type="Leukocytes",
        taxon_id="9606",
    )
