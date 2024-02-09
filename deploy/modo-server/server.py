import os
from typing import Union

from fastapi import FastAPI
import modo
from modo.api import MODO
import rdflib


S3 = os.environ["S3_ENDPOINT"]

app = FastAPI()


@app.get("/")
def index():
    return {
        "S3 endpoint": f"{S3}",
    }


def gather_metadata() -> rdflib.Graph:
    """Generate metadata KG from all MODOs."""
    # Loop on MODOs
    # Instantiate MODO()
    # Retrieve rdflib.Graph
    # Graph union


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/list")
def list_modos():
    """List MODO entries in bucket."""
    ...


@app.get("/slice")
def slice_cram(file: str, region: str):
    """Forward request to htsget."""
    ...
