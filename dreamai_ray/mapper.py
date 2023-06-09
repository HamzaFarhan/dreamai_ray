# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_mapper.ipynb.

# %% auto 0
__all__ = ['Callback', 'msg_bs_cb', 'cbs_before_batch', 'cbs_before_batch_rows', 'cbs_after_batch_rows', 'cbs_after_batch',
           'Mapper']

# %% ../nbs/01_mapper.ipynb 2
from .imports import *
from .utils import *

# %% ../nbs/01_mapper.ipynb 4
class Callback:
    def before_batch(self, **kwargs):
        pass

    def before_batch_rows(self, **kwargs):
        pass

    def after_batch_rows(self, **kwargs):
        pass

    def after_batch(self, **kwargs):
        pass


class msg_bs_cb(Callback):
    def before_batch(self, df, **kwargs):
        msg.info(f"DF BATCH SIZE: {len(df)}", spaced=True)


def cbs_before_batch(cbs, **kwargs):
    [cb.before_batch(**kwargs) for cb in cbs]


def cbs_before_batch_rows(cbs, df, **kwargs):
    [cb.before_batch_rows(**kwargs) for _ in range(len(df)) for cb in cbs]


def cbs_after_batch_rows(cbs, df, **kwargs):
    [cb.after_batch_rows(**kwargs) for _ in range(len(df)) for cb in cbs]


def cbs_after_batch(cbs, **kwargs):
    [cb.after_batch(**kwargs) for cb in cbs]


class Mapper:
    """
    A class to map a function to a dataframe. The function can be a UDF or a function that returns a dataframe.
    Parameters
    ----------
    udf: function
        A function that takes a dataframe as input and returns a dataframe as output.
    udf_kwargs: dict
        The keyword arguments to pass to the `udf`.
    cbs: list
        A list of `Callback`s to run before and after the mapping.
    """

    def __init__(
        self,
        udf=noop,
        udf_kwargs={},
        cbs=[msg_bs_cb()],
        **kwargs,
    ):
        udf = partial(udf, **udf_kwargs)
        store_attr(**locals_to_params(locals()))

    def map(self, df):
        return df.apply(self.udf, axis=1, result_type="expand")

    def __call__(self, df):
        cbs_before_batch(self.cbs, df=df)
        cbs_before_batch_rows(self.cbs, df=df)

        df = self.map(df)

        cbs_after_batch_rows(self.cbs, df=df)
        cbs_after_batch(self.cbs, df=df)

        return df

