"""This is the webserver to serve MODO objects.
It connects to an S3 bucket (catalog) containing
MODOs (folders).

The role of this server is to provide a list of
available modos, as well as their metadata.

"""

import os

from fastapi import FastAPI
from modo.api import MODO
import s3fs
import zarr


S3_PUBLIC_URL = os.environ["S3_PUBLIC_URL"]
S3_LOCAL_URL = os.environ["S3_LOCAL_URL"]
BUCKET = os.environ["S3_BUCKET"]
HTSGET_PUBLIC_URL = os.environ["HTSGET_PUBLIC_URL"]
HTSGET_LOCAL_URL = os.environ["HTSGET_LOCAL_URL"]

app = FastAPI()
minio = s3fs.S3FileSystem(anon=True, endpoint_url=S3_LOCAL_URL)


@app.get("/")
def index():
    return {
        "Message": "Welcome to the modo server",
        "Catalog bucket": f"{S3_PUBLIC_URL}/{BUCKET}",
        "htsget": HTSGET_PUBLIC_URL,
    }


@app.get("/list")
def list_modos() -> list[str]:
    """List MODO entries in bucket."""
    modos = minio.ls(BUCKET)
    # NOTE: modo contains bucket name
    return [f"{S3_PUBLIC_URL}/{modo}" for modo in modos]


@app.get("/meta")
def gather_metadata():
    """Generate metadata KG from all MODOs."""
    meta = {}

    for modo in minio.ls(BUCKET):
        store = s3fs.S3Map(root=f"{modo}/data.zarr", s3=minio, check=False)
        archive = zarr.open(
            store=store,
        )
        meta = MODO(path=f"{S3_LOCAL_URL}/{modo}", archive=archive).metadata

    return meta
