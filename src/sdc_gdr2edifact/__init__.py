"""sdc-gdr2edifact: Governed Data Records as UN/EDIFACT D.24A interchanges, through sdc-mapper.

    from sdc_mapper import Engine, load_mapping
    from sdc_gdr2edifact import EDIFACTMapper, mapping_path
    mapper = EDIFACTMapper("/path/to/d24a.zip")       # the directory as downloaded from UNECE; or $SDC_EDIFACT_DIRECTORY
    result = Engine().map_record(xml, mapper, load_mapping(mapping_path("cacl4njrwanj15g3p3so8t6h")))

One mapping file per model, in `mappings/`. Registered with sdc-mapper as the target `edifact`.
"""
from pathlib import Path

__version__ = "4.0.1"

MAPPINGS = Path(__file__).with_name("mappings")


def mapping_path(ct_id: str) -> Path:
    """The mapping file this package publishes for a model, by the model's identifier."""
    found = sorted(MAPPINGS.glob(f"*-{ct_id}.yaml"))
    if not found:
        raise FileNotFoundError(f"sdc-gdr2edifact has no mapping for model {ct_id}")
    return found[-1]


from .directory import Directory, DirectoryNotFound  # noqa: E402
from .mapper import EDIFACTMapper  # noqa: E402

__all__ = ["EDIFACTMapper", "Directory", "DirectoryNotFound", "mapping_path", "MAPPINGS", "__version__"]
