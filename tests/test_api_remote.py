"""Tests for the remote use of multi-omics digital object (modo) API
"""

from modos.api import MODO
from modos.io import build_modo_from_file

import modos_schema.datamodel as model
import pytest

## Instantiate multiple MODOs


@pytest.mark.slow
def test_multi_modos(setup):
    minio_endpoint = setup["minio"].get_config()["endpoint"]
    minio_creds = {"secret": "minioadmin", "key": "minioadmin"}
    for _ in range(3):
        MODO(
            "test/ex",
            s3_endpoint=f"http://{minio_endpoint}",
            s3_kwargs=minio_creds,
        )


## Add element


@pytest.mark.slow
def test_add_element(assay, remote_modo):
    remote_modo.add_element(assay)
    assert "assay/test_assay" in remote_modo.metadata.keys()


@pytest.mark.slow
def test_add_data(data_entity, remote_modo):
    remote_modo.add_element(data_entity, data_file="data/ex/demo1.cram")
    assert "demo1.cram" in [fi.name for fi in remote_modo.list_files()]
    assert "demo1.cram.crai" in [fi.name for fi in remote_modo.list_files()]


## Remove element


@pytest.mark.slow
def test_remove_element(sample, remote_modo):
    remote_modo.add_element(sample)
    assert "sample/test_sample" in remote_modo.list_samples()
    remote_modo.remove_element("sample/test_sample")
    assert "sample/test_sample" not in remote_modo.list_samples()


## Remove modo


@pytest.mark.slow
def test_remove_modo(setup):
    # NOTE: We build a new modo to prevent remote_modo from being deleted
    # in following tests.
    minio_client = setup["minio"].get_client()
    minio_endpoint = setup["minio"].get_config()["endpoint"]
    minio_creds = {"secret": "minioadmin", "key": "minioadmin"}
    modo = MODO(
        "test/remove_ex",
        s3_endpoint=f"http://{minio_endpoint}",
        s3_kwargs=minio_creds,
    )
    objects = minio_client.list_objects("test")
    assert "remove_ex/" in [o.object_name for o in objects]
    modo.remove_object()
    objects = minio_client.list_objects("test")
    assert "remove_ex/" not in [o.object_name for o in objects]


## Update element


@pytest.mark.slow
def test_update_element(sample, remote_modo):
    remote_modo.add_element(sample)
    test_sample = model.Sample(
        id="sample/test_sample", description="A fake sample for test purposes"
    )
    remote_modo.update_element("sample/test_sample", test_sample)
    assert (
        remote_modo.metadata["sample/test_sample"].get("description")
        == "A fake sample for test purposes"
    )
