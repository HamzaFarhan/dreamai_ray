# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/index/02_core.ipynb.

# %% auto 0
__all__ = ['write_index_cb', 'reset_index_cb', 'IndexCreator', 'create_indexes', 'search_indexes']

# %% ../../nbs/index/02_core.ipynb 2
from ..imports import *
from ..utils import *
from ..mapper import *
from .utils import *
from .df import *


# %% ../../nbs/index/02_core.ipynb 4
class write_index_cb(Callback):
    "A `Callback` to write the index to disk."

    def after_batch(self, cls, **kwargs):
        cls.index = cls.udf_kwargs["index"]
        index_folder = cls.index_folder
        os.makedirs(index_folder, exist_ok=True)
        index_path = str(Path(index_folder) / f"{cls.block_counter}.faiss")
        if self.verbose and cls.verbose:
            msg.info(f"Writing Index to {index_path}")
            msg.info(f"Index Size: {cls.index.ntotal}")
        faiss.write_index(cls.index, index_path)


class reset_index_cb(Callback):
    "A `Callback` to reset the index."

    def after_batch(self, cls, **kwargs):
        cls.index.reset()
        if self.verbose and cls.verbose:
            msg.info(f"Index Size Post Reset: {cls.index.ntotal}")
        cls.udf_kwargs["index"] = cls.index
        cls.udf = partial(cls.udf, **cls.udf_kwargs)


class IndexCreator(Mapper):
    "Creates indexes from embeddings."

    def __init__(
        self,
        index_dim=3,  # The dimension of the index.
        index_folder="indexes",  # The folder to write the index to.
        ems_col="embedding",  # The column to use to create the index.
        udf=df_to_index,  # The function to use to create the index.
        cbs=[write_index_cb, reset_index_cb],  # The `Callback`s to use.
        verbose=True,  # Whether to print out information.
        udf_verbose=False,  # Whether to print out information in the udf.
        udf_kwargs={},  # Additional kwargs to pass to the udf.
        **kwargs,
    ):
        self.index_folder = index_folder
        self.index = create_index(index_dim)
        udf_kwargs["index"] = self.index
        udf_kwargs["ems_col"] = ems_col
        udf_kwargs["verbose"] = udf_verbose
        self.verbose = verbose
        super().__init__(**locals_to_params(locals()))


def create_indexes(
    ems_folder="embeddings",  # The folder containing the embeddings.
    ems_col="embedding",  # The column to use to create the index.
    block_size=25,  # The number of embeddings per index.
    index_dim=768,  # The dimension of the index.
    index_folder="indexes",  # The folder to write the index to.
    udf=df_to_index,  # The function to use to create the index.
    cbs=[write_index_cb, reset_index_cb],  # The `Callback`s to use.
    verbose=True,  # Whether to print out information.
    udf_verbose=False,  # Whether to print out information in the udf.
    udf_kwargs={},  # Additional kwargs to pass to the udf.
    **kwargs,
):
    "Function to create indexes from embeddings."

    m = IndexCreator(**locals_to_params(locals(), omit=["ems_folder", "block_size"]))
    em_files = sorted(
        get_files(ems_folder, extensions=[".json"]),
        key=lambda x: int(x.stem.split("_")[-1]),
    )
    # ems = [json.load(open(em_file))["embedding"] for em_file in em_files]
    df = pd.DataFrame({ems_col: em_files})
    if verbose:
        msg.info(f"Embeddings DF created of length: {len(df)}")
    for i in range(0, len(df), block_size):
        df_block = df.iloc[i : i + block_size]
        m(df_block)
    return df


def search_indexes(
    ems,  # The embedding to search. Can be pre-loaded or a path to a json file.
    index_folder="indexes",  # The folder containing the indexes.
    k=2,  # The number of nearest neighbors to return.
    verbose=True,  # Whether to print out information.
):
    "Function to search an embedding against indexes."

    indexes = sorted(get_files(index_folder), key=lambda x: int(x.stem.split(".")[0]))
    if not os.path.exists(index_folder) or len(indexes) == 0:
        raise Exception(
            f"No indexes found in '{index_folder}' folder. Please create indexes first."
        )
    qdf = pd.DataFrame(
        {
            "index": indexes,
            "embedding": [ems] * len(indexes),
        }
    )

    qdf = qdf.apply(lambda x: df_index_search(x, k=k, verbose=verbose), axis=1)
    # if verbose:
    # msg.info(f"First row of qdf: {qdf.iloc[0]}")
    res = index_heap(qdf, k=k, verbose=verbose)
    return res, qdf