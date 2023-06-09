# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/pdf/05_app.ipynb.

# %% auto 0
__all__ = ['SegsPredictor', 'NERPredictor', 'EmsPredictor', 'pdf_pipeline', 'ner_pipeline', 'pdf_pipeline_params',
           'ner_pipeline_params']

# %% ../../nbs/pdf/05_app.ipynb 2
from ..imports import *
from ..utils import *
from .core import *
from .extract import *
from .ner import *
from .df import *
from .. import redis_kv_store


# %% ../../nbs/pdf/05_app.ipynb 4
class SegsPredictor:
    def __init__(
        self,
        model_name="HamzaFarhan/PDFSegs",
        thresh=0.6,
        write=False,
        device=None,
        **kwargs,
    ):
        device = default_device() if device is None else device
        self.thresh = thresh
        self.model = load_segs_model(model_name, device=device)
        self.write = write

    def __call__(self, df):
        msg.info(f"LEN SEGS DF: {len(df)}", spaced=True)
        df[["segs", "classes", "probs"]] = df.apply(
            lambda x: write_df_segs(
                x,
                self.model,
                thresh=self.thresh,
                write=self.write,
            ),
            axis=1,
            result_type="expand",
        )
        return df


class NERPredictor:
    def __init__(
        self,
        ner_roles=True,
        device=None,
        task_id=None,
        redis_host="127.0.0.1",
        redis_port=6379,
    ):
        device = default_device() if device is None else device
        # msg.info(f"NER DEVICE: {device}", spaced=True)
        self.tner = load_ner_model(device=device)
        self.jner = load_job_model(device=device)
        if ner_roles:
            self.work_ner_dict = {"company": "", "role": "", "date": ""}
        else:
            self.work_ner_dict = {"company": "", "date": ""}
        self.task_id = task_id
        self.kv_store = redis_kv_store.KeyValueStore(
            redis_host=redis_host, redis_port=redis_port
        )

    def __call__(self, df):
        msg.info(f"LEN NER DF: {len(df)}", spaced=True)
        df = df.apply(
            lambda x: write_df_ner(
                x,
                tner=self.tner,
                jner=self.jner,
                work_ner_dict=self.work_ner_dict,
            ),
            axis=1,
        )
        if self.task_id is not None and self.kv_store is not None:
            for _ in range(len(df)):
                update_task_progress(self.task_id, self.kv_store)
        return df


class EmsPredictor:
    def __init__(
        self,
        model_name="HamzaFarhan/PDFSegs",
        device="cpu",
        task_id=None,
        redis_host="127.0.0.1",
        redis_port=6379,
        **kwargs,
    ):
        device = default_device() if device is None else device
        self.model = load_ems_model(model_name, device=device)
        self.task_id = task_id
        self.kv_store = redis_kv_store.KeyValueStore(
            redis_host=redis_host, redis_port=redis_port
        )

    def __call__(self, df):
        msg.info(f"LEN EMS DF: {len(df)}", spaced=True)
        df = df.apply(lambda x: write_df_ems(x, self.model), axis=1)
        if self.task_id is not None and self.kv_store is not None:
            for _ in range(len(df)):
                update_task_progress(self.task_id, self.kv_store)
        return df


def pdf_pipeline(params):
    try:
        task_id = params["task_id"]
        data_path = params["data_path"]
        segs_folder = params["segs_folder"]
        ems_folder = params["ems_folder"]
        segs_params = params["segs_params"]
        ems_params = params["ems_params"]
        num_blocks = params["num_blocks"]
        blocks_per_window = params["blocks_per_window"]
        redis_host = params.get("redis_host", "127.0.0.1")
        redis_port = params.get("redis_port", 6379)
        do_segs = params.get("do_segs", True)
        do_ner = params.get("do_ner", False)
        if do_segs:
            segs_params["fn_constructor_kwargs"]["write"] = True
    except Exception as e:
        raise Exception(f"Error in params: {e}.\nParams: {params}")
    try:
        kv_store = redis_kv_store.KeyValueStore(redis_host=redis_host, redis_port=redis_port)
        ems_params["fn_constructor_kwargs"]["task_id"] = task_id
    except Exception as e:
        raise Exception(f"Error in connecting to redis: {e}.\nParams: {params}")

    try:
        # segs_folder = Path(task_id) / Path(segs_folder).name
        # ems_folder = Path(task_id) / Path(ems_folder).name
        task_folder = Path(f"/tmp/{task_id}")
        os.makedirs(task_folder, exist_ok=True)
        local_segs_folder = get_local_path(segs_folder, task_folder)
        local_ems_folder = get_local_path(ems_folder, task_folder)
        df = create_pdf_df(
            data_path, segs_folder=local_segs_folder, ems_folder=local_ems_folder
        )
        init_task_progress(task_id, kv_store, len(df))
        ds = rd.from_modin(df)
        if num_blocks is not None:
            num_blocks = min(num_blocks, len(df))
            ds = ds.repartition(num_blocks)
            if blocks_per_window is not None:
                ds = ds.window(blocks_per_window=blocks_per_window)
    except Exception as e:
        raise Exception(f"Error in create_pdf_df: {e}.")
    try:
        ds = ds.map_batches(extract_df_text, batch_size=params["segs_params"]["batch_size"])
    except Exception as e:
        raise Exception(f"Error in extract_df_text: {e}.")

    if do_segs:
        try:
            ds = ds.map_batches(
                SegsPredictor,
                **segs_params,
            )
        except Exception as e:
            raise Exception(f"Error in SegsPredictor: {e}.\nseg_params: {segs_params}")
    try:
        ds = ds.map_batches(
            EmsPredictor,
            **ems_params,
        )
    except Exception as e:
        raise Exception(f"Error in EmsPredictor: {e}.\nems_params: {ems_params}")
    ds = str(write_ds(ds, task_folder / "pdf_preds.parquet"))
    if is_bucket(segs_folder):
        # bucket = Path(segs_folder).parent
        bucket_up(local_segs_folder, segs_folder, only_new=False)
    if is_bucket(ems_folder):
        # bucket = Path(ems_folder).parent
        bucket_move(local_ems_folder, ems_folder)
    shutil.rmtree(ds)
    if not do_ner:
        shutil.rmtree(task_folder)
    return {"pipeline_result": "SUCCESS"}


def ner_pipeline(params):
    try:
        task_id_ner = params["task_id_ner"]
        task_id = params["task_id"]
        data_path = params["data_path"]
        segs_folder = params["segs_folder"]
        ner_params = params["ner_params"]
        num_blocks = params["num_blocks"]
        redis_host = params.get("redis_host", "127.0.0.1")
        redis_port = params.get("redis_port", 6379)
    except Exception as e:
        raise Exception(f"Error in params: {e}.\nParams: {params}")
    try:
        kv_store = redis_kv_store.KeyValueStore(redis_host=redis_host, redis_port=redis_port)
        ner_params["fn_constructor_kwargs"]["task_id"] = task_id_ner
    except Exception as e:
        raise Exception(f"Error in connecting to redis: {e}.\nParams: {params}")
    try:
        task_folder = Path(f"/tmp/{task_id}")
        os.makedirs(task_folder, exist_ok=True)
        local_segs_folder = get_local_path(segs_folder, task_folder)
        # msg.info(f"Local_segs_folder: {local_segs_folder}", spaced=True)
        df = create_ner_df(data_path, segs_folder=local_segs_folder)
        init_task_progress(task_id_ner, kv_store, len(df))
        ds = rd.from_modin(df)
        if num_blocks is not None:
            num_blocks = min(num_blocks, len(df))
            ds = ds.repartition(num_blocks)
    except Exception as e:
        raise Exception(f"Error in create_ner_df: {e}.")

    try:
        ds = ds.map_batches(
            NERPredictor,
            **ner_params,
        )
    except Exception as e:
        raise Exception(f"Error in NERPredictor: {e}.\nner_params: {ner_params}")
    ds = str(write_ds(ds, task_folder / "ner_preds.parquet"))
    if is_bucket(segs_folder):
        bucket_up(local_segs_folder, segs_folder, only_new=True)
    shutil.rmtree(task_folder)
    return {"ner_pipeline_result": "SUCCESS"}


def pdf_pipeline_params(
    data_path="",
    segs_folder="pdf_segs",
    ems_folder="pdf_ems",
    segs_model="HamzaFarhan/PDFSegs",
    ems_model="HamzaFarhan/PDFSegs",
    num_gpus=1,
    num_blocks=None,
    batch_sizes=[8, 8, 8],
    workers=[[3, 4], [3, 4], [3, 4]],
    do_segs=True,
    do_ner=False,
    redis_host="127.0.0.1",
    redis_port=6379,
    **kwargs,
):
    if not is_list(batch_sizes):
        batch_sizes = [batch_sizes]
    if not is_list(workers[0]):
        workers = [workers]
    batch_sizes += [batch_sizes[0]] * (2 - len(batch_sizes))
    workers += [workers[0]] * (2 - len(workers))
    try:
        max_workers = workers[1][1]
        if do_segs:
            max_workers += workers[0][1]
            # if do_ner:
            # max_workers += workers[1][1]
        num_gpus = num_gpus / max_workers
    except Exception as e:
        raise Exception(f"Invalid workers: {e}")
    try:
        params = {
            "data_path": data_path,
            "segs_folder": segs_folder,
            "ems_folder": ems_folder,
            "num_blocks": num_blocks,
            "blocks_per_window": None,
            "do_segs": do_segs,
            "do_ner": do_ner,
            "redis_host": redis_host,
            "redis_port": redis_port,
            "segs_params": dict(
                fn_constructor_kwargs=dict(
                    model_name=segs_model,
                    device=None,
                ),
                batch_size=batch_sizes[0],
                compute=rd.ActorPoolStrategy(min_size=workers[0][0], max_size=workers[0][1]),
                num_gpus=num_gpus,
            ),
            "ems_params": dict(
                fn_constructor_kwargs=dict(
                    model_name=ems_model,
                    device=None,
                    redis_host=redis_host,
                    redis_port=redis_port,
                ),
                batch_size=batch_sizes[1],
                compute=rd.ActorPoolStrategy(min_size=workers[1][0], max_size=workers[1][1]),
                num_gpus=num_gpus,
            ),
        }
    except Exception as e:
        raise Exception(f"Invalid params: {e}.\nParams so far: {locals()}")
    return params


def ner_pipeline_params(
    data_path="",
    segs_folder="pdf_segs",
    num_gpus=1,
    num_blocks=None,
    ner_batch_size=8,
    ner_workers=[[3, 4]],
    redis_host="127.0.0.1",
    redis_port=6379,
    # do_ner=True,
    **kwargs,
):
    try:
        if is_list(ner_batch_size):
            ner_batch_size = ner_batch_size[0]
        if not is_list(ner_workers[0]):
            ner_workers = [ner_workers]
        min_workers, max_workers = ner_workers[0]
        num_gpus = num_gpus / max_workers
    except Exception as e:
        raise Exception(f"Invalid workers: {e}")
    try:
        params = {
            "data_path": data_path,
            "segs_folder": segs_folder,
            "num_blocks": num_blocks,
            "blocks_per_window": None,
            "redis_host": redis_host,
            "redis_port": redis_port,
            "ner_params": dict(
                fn_constructor_kwargs=dict(
                    device=None,
                    redis_host=redis_host,
                    redis_port=redis_port,
                ),
                batch_size=ner_batch_size,
                compute=rd.ActorPoolStrategy(min_size=min_workers, max_size=max_workers),
                num_gpus=num_gpus,
            ),
        }
    except Exception as e:
        raise Exception(f"Invalid params: {e}.\nParams so far: {locals()}")
    return params
