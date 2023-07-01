# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/api/02_parallel_app.ipynb.

# %% auto 0
__all__ = ['app', 'dai_index', 'DreamAIIndex']

# %% ../../nbs/api/02_parallel_app.ipynb 2
from fastapi import FastAPI
from ..imports import *
from ..utils import *
from ..index.core import *
from ..parallel.parallelizer import *
from .utils import *


# %% ../../nbs/api/02_parallel_app.ipynb 4
app = FastAPI(title="DreamAI Parallel API", version="0.0.2")


@serve.deployment(num_replicas=2, ray_actor_options={"num_cpus": 6})
@serve.ingress(app)
class DreamAIIndex:
    def __init__(
        self,
        num_actors=2,
        num_cpus=1,
        num_gpus=0,
    ) -> None:
        try:
            self.num_actors = num_actors
            self.num_cpus = num_cpus
            self.num_gpus = num_gpus
            self.index_pool_mapper = DataParallelizer.remote(
                IndexCreatorPoolActor,
                create_indexes_iter,
                num_actors=num_actors,
                num_cpus=num_cpus,
                num_gpus=num_gpus,
                combiner=create_indexes_combine,
                verbose=True,
            )
            self.search_pool_mapper = DataParallelizer.remote(
                SearchIndexPoolActor,
                search_indexes_iter,
                num_actors=num_actors,
                num_cpus=num_cpus,
                num_gpus=num_gpus,
                combiner=search_indexes_combine,
                verbose=True,
            )

        except Exception as e:
            msg.fail(f"Mappers creation failed with error {e}", spaced=True)

    async def index_action(self, data_dict: dict):
        # t1 = time()
        res = ray.get(self.index_pool_mapper.do_parallel.remote(data_dict=data_dict))
        # t2 = time()
        # msg.good(f"Index Creation Time = {t2-t1:.2f}.", spaced=True, show=True)
        return res

    async def search_action(self, data_dict: dict):
        # t1 = time()
        res = ray.get(self.search_pool_mapper.do_parallel.remote(data_dict=data_dict))
        # t2 = time()
        # msg.good(f"Index Searching Time = {t2-t1:.2f}.", spaced=True, show=True)
        return res

    @serve.batch(max_batch_size=5, batch_wait_timeout_s=0.2)
    async def index_handle_batched(self, data_dict_list=None) -> list:
        if data_dict_list is None:
            raise Exception(f"Data dict list is None.")
        msg.info(f"BATCHES RECEIVED = {data_dict_list}", spaced=True)
        res = [self.index_action(data_dict) for data_dict in data_dict_list]
        return res

    @serve.batch(max_batch_size=5, batch_wait_timeout_s=0.2)
    async def search_handle_batched(self, data_dict_list=None) -> list:
        if data_dict_list is None:
            raise Exception(f"Data dict list is None.")
        msg.info(f"BATCHES RECEIVED = {data_dict_list}", spaced=True)
        res = [self.search_action(data_dict) for data_dict in data_dict_list]
        return res

    @app.post("/index/create")
    async def create(self, index_data: IndexData):
        data_dict = dict(
            ems_folder=index_data.ems_folder, index_folder=index_data.index_folder
        )
        t1 = time()
        res_ref = await self.index_handle_batched(data_dict)
        res = await res_ref
        t2 = time()
        msg.good(f"Index Creation Time = {t2-t1:.2f}.", spaced=True)
        return res

    @app.post("/index/update")
    async def update(self, index_data: IndexData):
        data_dict = dict(
            ems_folder=index_data.ems_folder, index_folder=index_data.index_folder
        )
        t1 = time()
        res_ref = await self.index_handle_batched(data_dict)
        res = await res_ref
        t2 = time()
        msg.good(f"Index Update Time = {t2-t1:.2f}.", spaced=True)
        return res

    @app.post("/index/matching")
    async def match_ems(self, match_data: MatchData):
        data_dict = dict(
            ems=match_data.ems, index_folder=match_data.index_folder, k=match_data.k
        )
        t1 = time()
        res_ref = await self.search_handle_batched(data_dict)
        res = await res_ref
        t2 = time()
        msg.good(f"Index Searching Time = {t2-t1:.2f}.", spaced=True)
        return res

# %% ../../nbs/api/02_parallel_app.ipynb 5
dai_index = DreamAIIndex.bind()