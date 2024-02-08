from typing import Union

from fastapi import FastAPI
from modo.api import MODO
import rdflib


S3_BUCKET = "s3://foo/bar"


app = FastAPI()


def gather_metadata() -> rdflib.Graph:
    """Generate metadata KG from all MODOs."""
    # Loop on MODOs
    # Instantiate MODO()
    # Retrieve rdflib.Graph
    # Graph union


@app.get("/")
def read_root():
    return {"Hello": "World"}


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
