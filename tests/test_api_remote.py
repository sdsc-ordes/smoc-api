"""Tests for the remote use of multi-omics digital object (modo) API
"""

from modo.api import MODO
from modo.io import build_modo_from_file

import modo_schema.datamodel as model
import pytest

## Add element


@pytest.mark.slow
def test_add_element(assay, remote_modo):
    remote_modo.add_element(assay)
    assert "/assay/test_assay" in remote_modo.metadata.keys()


@pytest.mark.slow
def test_add_data(data_entity, remote_modo):
    remote_modo.add_element(data_entity, data_file="data/ex/demo1.cram")
    assert "demo1.cram" in [fi.name for fi in remote_modo.list_files()]


## Remove element


@pytest.mark.slow
def test_remove_element(sample, remote_modo):
    remote_modo.add_element(sample)
    assert "/sample/test_sample" in remote_modo.list_samples()
    remote_modo.remove_element("sample/test_sample")
    assert "/sample/test_sample" not in remote_modo.list_samples()


## Update element


@pytest.mark.slow
def test_update_element(sample, remote_modo):
    remote_modo.add_element(sample)
    test_sample = model.Sample(
        id="sample/test_sample", description="A fake sample for test purposes"
    )
    remote_modo.update_element("sample/test_sample", test_sample)
    assert (
        remote_modo.metadata["/sample/test_sample"].get("description")
        == "A fake sample for test purposes"
    )
