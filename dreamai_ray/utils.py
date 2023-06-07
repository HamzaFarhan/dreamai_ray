# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_utils.ipynb.

# %% auto 0
__all__ = ['json_file', 'get_task_from_kv_store', 'init_task_progress', 'update_task_progress', 'is_bucket', 'gsutil_bucket',
           'gsutil_folder', 'bucket_move', 'bucket_copy', 'bucket_dl', 'get_local_path', 'lit_eval',
           'find_alternate_path', 'resolve_ds_path', 'write_ds', 'chain_models', 'is_preprocessor', 'chain_processors',
           'handle_processors', 'repartition_ds', 'transform_ds', 'group_df_on']

# %% ../nbs/00_utils.ipynb 2
from dreamai.core import *
from .imports import *


# %% ../nbs/00_utils.ipynb 4
def json_file(path, folder):
    path = Path(path)
    folder = Path(folder)
    os.makedirs(folder, exist_ok=True)
    return folder / f"{path.stem}.json"


def get_task_from_kv_store(task_id, kv_store):
    task = kv_store.get(task_id)
    if task is None:
        raise Exception(f"No task entry found for task_id {task_id}.")
    if type(task) != dict:
        raise Exception(f"Wrong type for task with task_id {task_id}.")
    if len(task) == 0:
        raise Exception(f"Empty dict for task_id {task_id}.")
    return task


def init_task_progress(task_id, kv_store, total):
    task = get_task_from_kv_store(task_id, kv_store)
    task["progress"] = f"processing..."
    task["total"] = total
    kv_store.insert(task_id, task)


def update_task_progress(task_id, kv_store, **kwargs):
    task = get_task_from_kv_store(task_id, kv_store)
    prog = task["progress"]
    total = task["total"]
    if prog == "processing...":
        task["progress"] = f"1/{total}"
    else:
        curr, total = prog.split("/")
        task["progress"] = f"{int(curr) + 1}/{total}"
    kv_store.insert(task_id, task)


def json_file(path, folder):
    path = Path(path)
    folder = Path(folder)
    os.makedirs(folder, exist_ok=True)
    return folder / f"{path.stem}.json"


def is_bucket(p):
    return str(p).startswith("gs://")


def gsutil_bucket(bucket):
    if not str(bucket).startswith("gs://"):
        bucket = "gs://" + str(bucket)
    return bucket


def gsutil_folder(folder):
    folder = str(folder)
    if folder[-1] != "/":
        folder += "/"
    folder += "*"
    return folder


def bucket_move(folder, bucket):
    gu = shutil.which("gsutil")
    bucket = gsutil_bucket(bucket)
    folder = gsutil_folder(folder)
    subprocess.run([gu, "-m", "mv", folder, bucket])


def bucket_copy(folder, bucket, only_new=True):
    gu = shutil.which("gsutil")
    bucket = gsutil_bucket(bucket)
    folder = gsutil_folder(folder)
    cmd = [gu, "-m", "cp", "-r"]
    if only_new:
        cmd.append("-n")
    subprocess.run(cmd + [folder, bucket])


def bucket_dl(bucket, folder):
    gu = shutil.which("gsutil")
    bucket = gsutil_bucket(bucket)
    subprocess.run([gu, "-m", "cp", "-r", bucket, str(folder)])


def get_local_path(folder, task_folder):
    if is_bucket(folder):
        return task_folder / Path(folder).name
    else:
        return Path(folder)


def lit_eval(x):
    try:
        return literal_eval(x)
    except:
        return x


def find_alternate_path(path):
    path = Path(path)
    idx = 0
    file_start = "/".join(path.parts[:-1])
    if file_start[:2] == "//":
        file_start = file_start[1:]
    file_start = Path(file_start)
    file_end = path.stem
    new_path = file_start / f"{file_end}{path.suffix}"
    while new_path.exists():
        new_path = file_start / f"{file_end}_{idx}{path.suffix}"
        idx += 1
    msg.info(f"{path} already exists. Using {new_path} instead.", spaced=True)
    return new_path


def resolve_ds_path(ds_path, append=False, overwrite=False):
    ds_path = Path(ds_path)
    if ds_path.is_dir():
        if append:
            msg.info(
                f"{ds_path} already exists. Appending because append=True.", spaced=True
            )
            return ds_path
        elif overwrite:
            msg.info(
                f"\n{ds_path} already exists. Overwriting because overwrite=True.\n",
                spaced=True,
            )
            shutil.rmtree(ds_path)
            return ds_path
        ds_path = find_alternate_path(ds_path)
    return ds_path


def write_ds(ds, ds_path, append=False, overwrite=False, **kwargs):
    ds_path = resolve_ds_path(ds_path, append, overwrite=overwrite)
    ds.write_parquet(ds_path, **kwargs)
    return ds_path


def chain_models(models):
    if not is_list(models):
        models = [models]
    return nn.Sequential(*models)


def is_preprocessor(x):
    return isinstance(x, rd.Preprocessor)


def chain_processors(processors):
    if not is_list(processors):
        processors = [processors]
    return Chain(*processors)


def handle_processors(processors, batch_size=None):
    if processors is None:
        return None
    if not is_list(processors):
        processors = [processors]
    if len(processors) == 0:
        return None

    def to_bm(p, bs):
        if not is_preprocessor(p) and callable(p):
            return BatchMapper(p, batch_size=bs, batch_format="pandas")
        elif is_preprocessor(p):
            return p

    return chain_processors([to_bm(p, batch_size) for p in processors if p is not None])


def repartition_ds(ds, num_blocks=2):
    if path_or_str(ds):
        ds = rd.read_parquet(ds)
    try:
        if num_blocks is not None and num_blocks > 0 and ds.num_blocks() != num_blocks:
            ds = ds.repartition(num_blocks)
    except:
        pass
    return ds


def transform_ds(ds, processors=[], num_blocks=2, batch_size=32, **kwargs):
    ds = repartition_ds(ds, num_blocks=num_blocks)
    pp = handle_processors(processors, batch_size=batch_size)
    if pp is None:
        return ds
    return pp.transform(ds)


def group_df_on(df, group_on="path", agg_on=["text"]):
    if not is_list(agg_on):
        agg_on = [agg_on]
    agg_dict = {k: lambda x: list(x) for k in agg_on}
    return df.groupby(group_on, as_index=False).agg(agg_dict).reset_index(drop=True)

