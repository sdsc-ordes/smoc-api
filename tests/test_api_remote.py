"""Tests for the remote use of multi-omics digital object (modo) API
"""

from modo.api import MODO
from modo.io import build_modo_from_file

import modo_schema.datamodel as model
import pysam
import re

## Add element


def test_add_element(Assay, remote_modo):
    remote_modo.add_element(Assay)
    assert "/assay/test_assay" in remote_modo.metadata.keys()


def test_add_data(DataEntity, remote_modo):
    remote_modo.add_element(DataEntity, data_file="data/ex/demo1.cram")
    assert "demo1.cram" in [fi.name for fi in remote_modo.list_files()]


## Remove element


def test_remove_element(Sample, remote_modo):
    remote_modo.add_element(Sample)
    assert "/sample/test_sample" in remote_modo.list_samples()
    remote_modo.remove_element("sample/test_sample")
    assert "/sample/test_sample" not in remote_modo.list_samples()


## Update element


def test_update_element(Sample, remote_modo):
    remote_modo.add_element(Sample)
    test_sample = model.Sample(
        id="sample/test_sample", description="A fake sample for test purposes"
    )
    remote_modo.update_element("sample/test_sample", test_sample)
    assert (
        remote_modo.metadata["/sample/test_sample"].get("description")
        == "A fake sample for test purposes"
    )
