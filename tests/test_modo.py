"""Tests for the multi-omics digital object (modo) API
"""
import shutil
from tempfile import TemporaryDirectory

from modo.api import MODO
from modo.io import build_modo_from_file


def test_read_modo():
    MODO("data/ex")


def test_init_modo():
    tmp = TemporaryDirectory()
    MODO(tmp.name)
    shutil.rmtree(tmp.name)


def test_init_modo_from_yaml():
    tmp = TemporaryDirectory()
    build_modo_from_file("data/ex_config.yaml", tmp.name)
    shutil.rmtree(tmp.name)
