"""This is the webserver to serve MODO objects.
It connects to an S3 bucket (catalog) containing
MODOs (folders).

The role of this server is to provide a list of
available modos, as well as their metadata.

"""

import os

from fastapi import FastAPI
from modo.api import MODO
<<<<<<< HEAD
=======
import rdflib
import re
>>>>>>> d2468b5 (feat: Add get?query to modo server)
import s3fs
import zarr


S3_LOCAL_URL = os.environ["S3_LOCAL_URL"]
BUCKET = os.environ["S3_BUCKET"]
HTSGET_LOCAL_URL = os.environ["HTSGET_LOCAL_URL"]

app = FastAPI()
minio = s3fs.S3FileSystem(anon=True, endpoint_url=S3_LOCAL_URL)


@app.get("/list")
def list_modos() -> list[str]:
    """List MODO entries in bucket."""
    modos = minio.ls(BUCKET)
    # NOTE: modo contains bucket name
    return [modo for modo in modos]


@app.get("/meta")
def gather_metadata():
    """Generate metadata KG from all MODOs."""
    meta = {}

    for modo in minio.ls(BUCKET):
        store = s3fs.S3Map(root=f"{modo}/data.zarr", s3=minio, check=False)
        archive = zarr.open(
            store=store,
        )
        # TODO: Fix id_ to id once restructure/herarchy is accepted!
        meta.update(MODO(path=f"{S3_LOCAL_URL}/{modo}", archive=archive).metadata)

    return meta


@app.get("/get")
def get_s3_path(query: str, exact_match: bool = False):
    """Receive the S3 path of all modos matching the query"""
    modos = minio.ls(BUCKET)
    if not exact_match:
        res = [modo for modo in modos if query in modo]
    else:
        # NOTE: Is there a better/more roboust way than regexpr?
        res = [
            modo
            for modo in modos
            if re.search("/" + query + r"$", modo) is not None
        ]
    return [f"{S3_URL}/{modo}" for modo in res]
