"""Module for extracting metabolomics metadata from mzTab-M 2.0 files."""
from pyteomics.mztab import MzTab
import modos_schema.datamodel as model


def load_mztab(path: str) -> MzTab:
    return MzTab(path)


def get_samples(mz: MzTab) -> list[model.Sample]:
    samples = []
    for _, sample in mz.samples.items():
        samples.append(
            model.Sample(
                id=sample["name"],
                description=sample["description"],
                taxon_id=sample.get("species", None),
                cell_type=sample.get("cell_type", None),
                source_material=sample.get("tissue", None),
            )
        )
    return samples


def get_assay(mz: MzTab) -> list[model.Assay]:
    assay = model.Assay(
        id=f"assay/{mz.id}",
        name=mz.title,
        description=mz.description,
        has_data=f"data/{mz.id}",
        has_sample=[sample["name"] for sample in mz.samples.values()],
        omics_type="METABOLOMICS",
        sample_processing=mz.sample_processing,
    )
    return assay
