"""Functions related to server storage handling"""

from pydantic import HttpUrl, validate_call
import requests
from typing import Mapping, Optional


@validate_call
def list_endpoints(url: HttpUrl) -> dict[str, HttpUrl]:
    """List all available endpoints on a remote modo server"""
    return requests.get(url=f"{url}/endpoints").json()


@validate_call
def list_remote_items(remote_url: HttpUrl) -> list[HttpUrl]:
    return requests.get(url=f"{remote_url}/list").json()


@validate_call
def get_metadata_from_remote(
    remote_url: HttpUrl, modo_id: Optional[str] = None
) -> Mapping:
    """Function to access metadata from one specific or all modos on a remote server

    Parameters
    ----------
    server_url
        Url to the remote modo server
    id
        id of the modo to retrieve metadata from. Will return all if not specified (default).
    """
    meta = requests.get(url=f"{remote_url}/meta").json()
    if modo_id is not None:
        try:
            return meta[modo_id]
        except KeyError as e:
            raise ValueError(
                f"Could not find metadata for modo with id: {modo_id}"
            ) from e
    else:
        return meta


@validate_call
def get_s3_path(
    remote_url: HttpUrl, query: str, exact_match: bool = False
) -> list:
    """Request public S3 path of a specific modo or all modos matching the query string
    Parameters
    ----------
    remote_url
        Url to the remote modo server
    query
        query string to specify the modo of interest
    exact_match
        if True only modos with exactly that id will be returned, otherwise (default) all matching modos
    """
    return requests.get(
        url=f"{remote_url}/get",
        params={"query": query, "exact_match": exact_match},
    ).json()
