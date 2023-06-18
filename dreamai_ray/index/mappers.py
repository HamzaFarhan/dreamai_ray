# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/index/02_mappers.ipynb.

# %% auto 0
__all__ = ['write_index_cb', 'reset_index_cb', 'CreateIndex']

# %% ../../nbs/index/02_mappers.ipynb 2
from ..imports import *
from ..utils import *
from ..mapper import *
from .utils import *
from .df import *


# %% ../../nbs/index/02_mappers.ipynb 4
from ..imports import noop


class write_index_cb(Callback):
    "A callback to write the index to disk."

    def __init__(self, verbose=False) -> None:
        self.verbose = verbose

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
    "A callback to reset the index."

    def __init__(self, verbose=True) -> None:
        self.verbose = verbose

    def after_batch(self, cls, **kwargs):
        cls.index.reset()
        if self.verbose and cls.verbose:
            msg.info(f"Index Size Post Reset: {cls.index.ntotal}")
        cls.udf_kwargs["index"] = cls.index
        cls.udf = partial(cls.udf, **cls.udf_kwargs)


class CreateIndex(Mapper):
    """
    Creates an index from embeddings.
    """

    def __init__(
        self,
        index_dim=3,  # The dimension of the index.
        index_folder="indexes",  # The folder to write the index to.
        ems_col="embedding",  # The column to use to create the index.
        udf=df_to_index,  # The function to use to create the index.
        cbs=[write_index_cb, reset_index_cb],  # The callbacks to use.
        verbose=True,  # Whether to print out information.
        udf_kwargs={},  # Additional kwargs to pass to the udf.
        **kwargs,
    ):
        self.index_folder = index_folder
        self.index = create_index(index_dim)
        udf_kwargs["index"] = self.index
        udf_kwargs["ems_col"] = ems_col
        udf_kwargs["verbose"] = verbose
        self.verbose = verbose
        super().__init__(**locals_to_params(locals()))
