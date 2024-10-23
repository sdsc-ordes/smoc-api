"""Utilities to automatically find / recommend terminology codes from text."""
from dataclasses import dataclass
import requests
from typing import Optional, Protocol


SLOT_TERMINOLOGIES = {
    "cell_type": "https://purl.obolibrary.org/obo/cl.owl",
    "source_material": "https://purl.obolibrary.org/obo/uberon.owl",
    "taxon_id": "https://purl.obolibrary.org/obo/ncbitaxon/subsets/taxslim.owl",
}


@dataclass
class Code:
    label: str
    uri: str


class CodeMatcher(Protocol):
    endpoint: Optional[str]
    slot: str
    top: int

    def find_codes(self, query: str) -> list[Code]:
        ...


class LocalCodeMatcher(CodeMatcher):
    """Find ontology codes for a given text by running a local term matcher."""

    def __init__(self, slot: str, top: int = 50):
        self.endpoint = None
        self.slot = slot
        self.top = top

        try:
            from pyfuzon import TermMatcher

            self.matcher = TermMatcher.from_files([SLOT_TERMINOLOGIES[slot]])
        except ImportError:
            raise ValueError(
                """No endpoint provided and pyfuzon not installed,
                cannot do code matching."""
            )

    def find_codes(self, query: str) -> list[Code]:
        return self.matcher.top(query, self.top)


class RemoteCodeMatcher(CodeMatcher):
    """Find ontology codes for a given text relying on a remote term matcher."""

    def __init__(self, slot: str, endpoint: str, top: int = 50):
        self.endpoint = endpoint
        self.slot = slot
        self.top = top

    def find_codes(self, query: str) -> list[Code]:
        codes = requests.get(
            f"{self.endpoint}/top?collection={self.slot}&query={query}&top={self.top}"
        ).json()["codes"]
        return [Code(label=code["label"], uri=code["uri"]) for code in codes]


def get_slot_matcher(
    slot: str,
    endpoint: Optional[str] = None,
) -> CodeMatcher:
    """Instantiates a code matcher based on input slot name."""
    if endpoint:
        matcher = RemoteCodeMatcher(slot, endpoint)
    else:
        matcher = LocalCodeMatcher(slot)
    return matcher


def get_slot_matchers(
    endpoint: Optional[str] = None,
) -> dict[str, CodeMatcher]:
    """Instantiates a code matcher for each slot. If the endpoint is provided, remote matchers are used."""
    matchers = {}
    for slot in SLOT_TERMINOLOGIES.keys():
        matchers[slot] = get_slot_matcher(slot, endpoint)
    return matchers
