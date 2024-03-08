"""This is the webserver to serve MODO objects.
It connects to an S3 bucket (catalog) containing
MODOs (folders).

The role of this server is to provide a list of
available modos, as well as their metadata.

"""
import difflib
import os
import s3fs

from fastapi import FastAPI
from modo.api import MODO


S3_LOCAL_URL = os.environ["S3_LOCAL_URL"]
S3_PUBLIC_URL = os.environ["S3_PUBLIC_URL"]
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
        meta.update(MODO(path=modo, s3_endpoint=S3_LOCAL_URL).metadata)

    return meta


@app.get("/get")
def get_s3_path(query: str, exact_match: bool = False):
    """Receive the S3 path of all modos matching the query"""
    modos = minio.ls(BUCKET)
    if exact_match:
        res = [
            modo for modo in modos if query in modo.removeprefix(BUCKET)
        ]
    else:
        res = [
            modo
            for modo in modos
            if difflib.SequenceMatcher(
                None, query, modo.removeprefix(BUCKET)
            ).quick_ratio()
            >= 0.7
        ]
    return [
        {
            f"{S3_PUBLIC_URL}/{modo}": {
                "s3_endpoint": S3_PUBLIC_URL,
                "modo_path": modo,
            }
        }
        for modo in res
    ]
