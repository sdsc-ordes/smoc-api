"""Tests for the multi-omics digital object (modo) API
"""
import shutil
from tempfile import TemporaryDirectory

from modo.api import MODO


def test_read_modo():
    MODO("data/ex")


def test_init_modo():
    tmp = TemporaryDirectory()
    MODO(tmp.name)
    shutil.rmtree(tmp.name)
