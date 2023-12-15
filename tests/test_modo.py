"""Tests for the multi-omics digital object (modo) API
"""
from modo.api import MODO


def test_read_modo():
    MODO("data/ex1")
