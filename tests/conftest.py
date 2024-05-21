"""Common fixtures for testing"""

import modo_schema.datamodel as model
import pytest
import shutil

from modo.api import MODO
from modo.io import build_modo_from_file
from pathlib import Path
from testcontainers.minio import MinioContainer


## A test MODO
@pytest.fixture
def test_modo(tmp_path):
    modo = build_modo_from_file(Path("data", "ex_config.yaml"), tmp_path)
    # TODO: This should be automatically copied. Remove when issue is solved!
    shutil.copyfile(
        Path("data", "ex", "demo1.cram.crai"), tmp_path / "demo1.cram.crai"
    )
    return modo


## different schema entities
@pytest.fixture
def data_entity():
    return model.DataEntity(
        id="test_data",
        name="test_data",
        data_path="demo1.cram",
        data_format="CRAM",
    )


@pytest.fixture
def assay():
    return model.Assay(
        id="test_assay", name="test_assay", omics_type="GENOMICS"
    )


@pytest.fixture
def sample():
    return model.Sample(
        id="test_sample",
        name="test_sample",
        cell_type="Leukocytes",
        taxon_id="9606",
    )


## testcontainers minio

minio = MinioContainer()


@pytest.fixture(scope="module")
def setup(request):
    minio.start()

    def remove_container():
        minio.stop()

    request.addfinalizer(remove_container)
    client = minio.get_client()
    client.make_bucket("test")


@pytest.fixture()
def remote_modo(setup):
    endpoint = minio.get_config()["endpoint"]
    return MODO(
        "test/ex",
        s3_endpoint="http://" + endpoint,
        s3_kwargs={"secret": "minioadmin", "key": "minioadmin"},
    )
