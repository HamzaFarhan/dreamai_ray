# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/00_utils.ipynb.

# %% auto 0
__all__ = ['IndexData', 'MatchData']

# %% ../../nbs/api/00_utils.ipynb 2
from ..imports import *
from ..utils import *
from ..index.core import *
from pydantic import BaseModel, Field

# %% ../../nbs/api/00_utils.ipynb 4
class IndexData(BaseModel):
    ems_folder: str = Field(
        title="The folder containing the embeddings.",
        description="It must be a directory. Can be local or remote.",
        regex=".*\/$",
        example="gs://gcsfuse-talentnet-dev/ems_1/",
    )
    index_folder: str = Field(
        title="The folder to write the indexes to.",
        description="It must be a directory. Can be local or remote.",
        regex=".*\/$",
        example="gs://gcsfuse-talentnet-dev/indexes_1/",
    )
    # index_dim: int = Field(title="The dimension of the index.", default=768)
    # block_size: int = Field(title="The number of embeddings per index.", default=4)


class MatchData(BaseModel):
    ems: str = Field(
        title="The embedding to search.",
        description="It must be a json file. Not a directory.",
        regex=".*\.json",
        example="gs://gcsfuse-talentnet-dev/job_ems/job-088a1057-6742-4799-ac88-bd0aa059f958_13.json",
    )
    index_folder: str = Field(
        title="The remote folder containing the indexes.",
        regex=".*\/$",
        example="gs://gcsfuse-talentnet-dev/indexes_1/",
    )
    # local_index_folder: str = Field(
    #     title="The local folder to download the indexes to.",
    #     description="If `index_folder` is a local folder, this field is ignored.",
    #     regex=".*\/$",
    #     example="/media/hamza/data2/faiss_data/indexes_1/",
    # )
    k: int = Field(title="The number of nearest neighbors to return.", default=2)