# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/00_app.ipynb.

# %% auto 0
__all__ = ['app', 'IndexData', 'MatchData', 'read_root', 'create', 'match_ems']

# %% ../../nbs/api/00_app.ipynb 2
from ..imports import *
from ..utils import *
from ..index.core import *

# %% ../../nbs/api/00_app.ipynb 4
from time import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, FilePath, DirectoryPath

app = FastAPI()


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
    index_dim: int = Field(title="The dimension of the index.", default=768)
    block_size: int = Field(title="The number of embeddings per index.", default=4)


class MatchData(BaseModel):
    ems: str = Field(
        title="The embedding to search.",
        description="It must be a json file. Not a directory.",
        regex=".*\.json",
        example="gs://gcsfuse-talentnet-dev/ems_1/resumes-4e2cdbeb-1e20-45ff-bded-a0a510350167_10.json",
    )
    index_folder: str = Field(
        title="The remote folder containing the indexes.",
        regex=".*\/$",
        example="gs://gcsfuse-talentnet-dev/indexes_1/",
    )
    local_index_folder: str = Field(
        title="The local folder to download the indexes to.",
        description="If `index_folder` is a local folder, this field is ignored.",
        regex=".*\/$",
        example="/media/hamza/data2/faiss_data/indexes_1/",
    )
    k: int = Field(title="The number of nearest neighbors to return.", default=2)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/index/create")
def create(index_data: IndexData):
    t1 = time()
    df = create_indexes(
        ems_folder=index_data.ems_folder,
        index_folder=index_data.index_folder,
        index_dim=index_data.index_dim,
        block_size=index_data.block_size,
    )
    t2 = time()
    msg.good(f"Time taken: {t2-t1:.2f} seconds.", spaced=True)
    return {'index_folder': index_data.index_folder}


@app.post("/index/matching")
def match_ems(match_data: MatchData):
    t1 = time()
    res, _ = search_indexes(
        ems=match_data.ems,
        index_folder=match_data.index_folder,
        local_index_folder=match_data.local_index_folder,
        k=match_data.k,
    )
    t2 = time()
    msg.good(f"Time taken: {t2-t1:.2f} seconds.", spaced=True)
    return res
