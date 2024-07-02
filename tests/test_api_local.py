"""Tests for the local use of multi-omics digital object (modo) API
"""

from modos.api import MODO
from modos.io import build_modo_from_file

import modos_schema.datamodel as model
import pysam
import re

## Initialize modo


def test_read_modo():
    MODO("data/ex")


def test_init_modo(tmp_path):
    MODO(tmp_path)


def test_init_modo_from_yaml(tmp_path):
    build_modo_from_file("data/ex_config.yaml", tmp_path)


## Add element


def test_add_element(assay, tmp_path):
    modo = MODO(tmp_path)
    modo.add_element(assay)
    assert "assay/test_assay" in modo.metadata.keys()


def test_add_data(data_entity, tmp_path):
    modo = MODO(tmp_path)
    modo.add_element(data_entity, data_file="data/ex/demo1.cram")
    assert "demo1.cram" in [fi.name for fi in modo.list_files()]
    assert "demo1.cram.crai" in [fi.name for fi in modo.list_files()]


def test_add_to_parent(sample, test_modo):
    test_modo.add_element(sample, part_of="assay/assay1")
    assert "sample/test_sample" in test_modo.metadata["assay/assay1"].get(
        "has_sample"
    )


## Remove element


def test_remove_element(test_modo):
    test_modo.remove_element("sample/sample1")
    assert "sample/sample1" not in test_modo.list_samples()


def test_remove_element_link_list(test_modo):
    assert ["sample/sample1"] in test_modo.metadata["assay/assay1"].values()
    test_modo.remove_element("sample/sample1")
    assert ["sample/sample1"] not in test_modo.metadata[
        "assay/assay1"
    ].values()


## Remove modos


def test_remove_modo(test_modo):
    modo_path = test_modo.path
    assert modo_path.exists()
    test_modo.remove_object()
    assert not modo_path.exists()


## Update element


def test_update_element(test_modo):
    sample1 = model.Sample(id="sample/sample1", cell_type="Leukocytes")
    test_modo.update_element("sample/sample1", sample1)
    assert (
        test_modo.metadata["sample/sample1"].get("cell_type") == "Leukocytes"
    )


## Enrich metadata


def test_enrich_metadata(test_modo):
    test_modo.enrich_metadata()
    assert "sequence/BA000007.3_bd7522" in test_modo.metadata.keys()


## Stream cram


def test_stream_genomics_no_region(test_modo):
    modo_files = [str(fi) for fi in test_modo.list_files()]
    file_path = list(filter(lambda x: re.search(r"cram$", x), modo_files))
    seq = test_modo.stream_genomics(file_path=file_path[0])
    assert isinstance(seq, pysam.libcalignmentfile.IteratorRowAllRefs)


def test_stream_genomics_region(test_modo):
    modo_files = [str(fi) for fi in test_modo.list_files()]
    file_path = list(filter(lambda x: re.search(r"cram$", x), modo_files))
    seq = test_modo.stream_genomics(
        file_path=file_path[0],
        region="BA000007.3",
        reference_filename="data/ex/reference1.fa",
    )
    assert isinstance(seq, pysam.libcalignmentfile.IteratorRowRegion)
