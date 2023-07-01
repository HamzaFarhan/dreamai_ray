# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/parallel/00_parallelizer.ipynb.

# %% auto 0
__all__ = ['PoolActor', 'DataParallelizer', 'IndexCreatorPoolActor', 'SearchIndexPoolActor']

# %% ../../nbs/parallel/00_parallelizer.ipynb 2
from ..imports import *
from ..utils import *
from ..mapper import *
from ..index.core import *
from ray.util import ActorPool


# %% ../../nbs/parallel/00_parallelizer.ipynb 4
class PoolActor:
    def __init__(self, num_gpus=0.2, num_cpus=0.5) -> None:
        self.num_gpus = num_gpus
        self.num_cpus = num_cpus

    def get_stats(self):
        pass

    def reset_stats(self):
        pass

    def action(self, data=None):
        pass


@ray.remote
class DataParallelizer:
    def __init__(
        self,
        actor: PoolActor,
        iterator,
        num_actors=2,
        num_cpus=1,
        num_gpus=0.2,
        combiner=None,
        set_actor_options=False,
        verbose=True,
    ) -> None:
        if actor is None:
            raise Exception("Actor not provided to Data Parallelizer.")
        if iterator is None:
            raise Exception("Iterator not provided to Data Parallelizer.")
        if combiner is not None:
            self.combiner = combiner
        t1 = time()
        msg.info(
            f"CONSTRUCTOR CALLED: NUM_CPUS={num_cpus}, NUM_ACTORS={num_actors}, NUM_GPUS={num_gpus}.",
            spaced=True,
            show=verbose,
        )
        if set_actor_options:
            msg.info(
                f"SETTING ACTOR OPTIONS for {num_actors} ACTORS: NUM_CPUS={num_cpus}, NUM_GPUS={num_gpus}.",
                spaced=True,
                show=verbose,
            )
            self.actors_list = [
                actor.options(num_gpus=num_gpus, num_cpus=num_cpus).remote(
                    num_cpus=num_cpus, num_gpus=num_gpus
                )
                for _ in range(num_actors)
            ]

        else:
            msg.info(
                f"ACTOR PARAMS WITHOUT OPTIONS for {num_actors} ACTORS: NUM_CPUS={num_cpus}, NUM_GPUS={num_gpus}.",
                spaced=True,
                show=verbose,
            )
            self.actors_list = [
                actor.remote(num_cpus=num_cpus, num_gpus=num_gpus)
                for _ in range(num_actors)
            ]
        self.pool = ActorPool(self.actors_list)
        t2 = time()
        msg.good(
            f"ACTOR POOL CREATED in {t2-t1:.2f} seconds.", spaced=True, show=verbose
        )
        self.iterator = iterator
        self.verbose = verbose
        self.num_actors = num_actors

    def do_parallel(self, data_dict=None):
        try:
            data_dict["num_blocks"] = self.num_actors
            data_list = self.iterator(**data_dict)
            if data_list is None:
                raise Exception("Unable to get iterator.")
        except Exception as e:
            raise Exception(f"Get iterator failed with error {e}.")
        t1 = time()
        pool = self.pool
        data_list_out = list(
            pool.map(lambda processor, item: processor.action.remote(item), data_list)
        )
        t2 = time()
        msg.info(
            f"Time elapsed processing data = {t2-t1:.2f}.",
            spaced=True,
            show=self.verbose,
        )
        msg.info(
            f"Final data length = {len(data_list_out)}.", spaced=True, show=self.verbose
        )
        t1 = time()
        ret = self.combiner(data_list_out, data_dict)
        t2 = time()
        msg.info(
            f"Time elapsed combining data = {t2-t1:.2f}.",
            spaced=True,
            show=self.verbose,
        )
        return {"result": ret}


@ray.remote
class IndexCreatorPoolActor(PoolActor):
    def action(self, data):
        return create_index_(data)


@ray.remote
class SearchIndexPoolActor(PoolActor):
    def action(self, data):
        return search_index_(data)
