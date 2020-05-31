import os
import hashlib
from pathlib import Path
import random
import platform

import pytest
import cloudpickle as cp

from .utils import multiply
from ..helpers import (
    hash_value,
    hash_function,
    get_available_cpus,
    save,
    create_pyscript,
    load_and_run,
)
from .. import helpers_file
from ..specs import File, Directory


def test_save(tmpdir):
    outdir = Path(tmpdir)
    with pytest.raises(ValueError):
        save(tmpdir)
    foo = multiply(name="mult", x=1, y=2)
    # save task
    save(outdir, task=foo)
    del foo
    # load saved task
    task_pkl = outdir / "_task.pklz"
    foo = cp.loads(task_pkl.read_bytes())
    assert foo.name == "mult"
    assert foo.inputs.x == 1 and foo.inputs.y == 2
    # execute task and save result
    res = foo()
    assert res.output.out == 2
    save(outdir, result=res)
    del res
    # load saved result
    res_pkl = outdir / "_result.pklz"
    res = cp.loads(res_pkl.read_bytes())
    assert res.output.out == 2


def test_create_pyscript(tmpdir):
    outdir = Path(tmpdir)
    with pytest.raises(Exception):
        create_pyscript(outdir, "checksum")
    foo = multiply(name="mult", x=1, y=2)
    save(outdir, task=foo)
    pyscript = create_pyscript(outdir, foo.checksum)
    assert pyscript.exists()


def test_hash_file(tmpdir):
    outdir = Path(tmpdir)
    with open(outdir / "test.file", "wt") as fp:
        fp.write("test")
    assert (
        helpers_file.hash_file(outdir / "test.file")
        == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    )


def test_hashfun_float():
    import math

    pi_50 = 3.14159265358979323846264338327950288419716939937510
    pi_15 = 3.141592653589793
    pi_10 = 3.1415926536
    # comparing for x that have the same x.as_integer_ratio()
    assert (
        math.pi.as_integer_ratio()
        == pi_50.as_integer_ratio()
        == pi_15.as_integer_ratio()
    )
    assert hash_function(math.pi) == hash_function(pi_15) == hash_function(pi_50)
    # comparing for x that have different x.as_integer_ratio()
    assert math.pi.as_integer_ratio() != pi_10.as_integer_ratio()
    assert hash_function(math.pi) != hash_function(pi_10)


def test_hash_value_dict():
    dict1 = {"a": 10, "b": 5}
    dict2 = {"b": 5, "a": 10}
    assert (
        hash_value(dict1)
        == hash_value(dict2)
        == [["a", hash_value(10)], ["b", hash_value(5)]]
        == [["a", 10], ["b", 5]]
    )


def test_hash_value_list_tpl():
    lst = [2, 5.6, "ala"]
    tpl = (2, 5.6, "ala")
    assert hash_value(lst) == [hash_value(2), hash_value(5.6), hash_value("ala")] == lst
    assert hash_value(lst) == hash_value(tpl)


def test_hash_value_list_dict():
    lst = [2, {"a": "ala", "b": 1}]
    hash_value(lst)
    assert (
        hash_value(lst)
        == [hash_value(2), hash_value([["a", "ala"], ["b", 1]])]
        == [2, [["a", "ala"], ["b", 1]]]
    )


def test_hash_value_files(tmpdir):
    file_1 = tmpdir.join("file_1.txt")
    file_2 = tmpdir.join("file_2.txt")
    with open(file_1, "w") as f:
        f.write("hello")
    with open(file_2, "w") as f:
        f.write("hello")

    assert hash_value(file_1, tp=File) == hash_value(file_2, tp=File)
    assert hash_value(file_1, tp=str) != hash_value(file_2, tp=str)
    assert hash_value(file_1) != hash_value(file_2)
    assert hash_value(file_1, tp=File) == helpers_file.hash_file(file_1)


def test_hash_value_files_list(tmpdir):
    file_1 = tmpdir.join("file_1.txt")
    file_2 = tmpdir.join("file_2.txt")
    with open(file_1, "w") as f:
        f.write("hello")
    with open(file_2, "w") as f:
        f.write("hi")

    assert hash_value([file_1, file_2], tp=File) == [
        hash_value(file_1, tp=File),
        hash_value(file_2, tp=File),
    ]


def test_hash_value_dir(tmpdir):
    file_1 = tmpdir.join("file_1.txt")
    file_2 = tmpdir.join("file_2.txt")
    with open(file_1, "w") as f:
        f.write("hello")
    with open(file_2, "w") as f:
        f.write("hi")

    test_sha = hashlib.sha256()
    for fx in [file_1, file_2]:
        test_sha.update(helpers_file.hash_file(fx).encode())

    bad_sha = hashlib.sha256()
    for fx in [file_2, file_1]:
        bad_sha.update(helpers_file.hash_file(fx).encode())

    orig_hash = helpers_file.hash_dir(tmpdir)

    assert orig_hash == test_sha.hexdigest()
    assert orig_hash != bad_sha.hexdigest()
    assert orig_hash == hash_value(tmpdir, tp=Directory)


def test_hash_value_nested(tmpdir):
    hidden = tmpdir.mkdir(".hidden")
    nested = tmpdir.mkdir("nested")
    file_1 = tmpdir.join("file_1.txt")
    file_2 = hidden.join("file_2.txt")
    file_3 = nested.join(".file_3.txt")
    file_4 = nested.join("file_4.txt")

    test_sha = hashlib.sha256()
    for fx in [file_1, file_2, file_3, file_4]:
        with open(fx, "w") as f:
            f.write(str(random.randint(0, 1000)))
        test_sha.update(helpers_file.hash_file(fx).encode())

    orig_hash = helpers_file.hash_dir(tmpdir)

    assert orig_hash == test_sha.hexdigest()
    assert orig_hash == hash_value(tmpdir, tp=Directory)

    nohidden_hash = helpers_file.hash_dir(
        tmpdir, ignore_hidden_dirs=True, ignore_hidden_files=True
    )
    nohiddendirs_hash = helpers_file.hash_dir(tmpdir, ignore_hidden_dirs=True)
    nohiddenfiles_hash = helpers_file.hash_dir(tmpdir, ignore_hidden_files=True)

    assert orig_hash != nohidden_hash
    assert orig_hash != nohiddendirs_hash
    assert orig_hash != nohiddenfiles_hash

    file_3.remove()
    assert helpers_file.hash_dir(tmpdir) == nohiddenfiles_hash
    hidden.remove()
    assert helpers_file.hash_dir(tmpdir) == nohidden_hash


def test_get_available_cpus():
    assert get_available_cpus() > 0
    try:
        import psutil

        has_psutil = True
    except ImportError:
        has_psutil = False

    if hasattr(os, "sched_getaffinity"):
        assert get_available_cpus() == len(os.sched_getaffinity(0))

    if has_psutil and platform.system().lower() != "darwin":
        assert get_available_cpus() == len(psutil.Process().cpu_affinity())

    if platform.system().lower() == "darwin":
        assert get_available_cpus() == os.cpu_count()


def test_load_and_run(tmpdir):
    """ testing load_and_run for pickled task"""
    task_pkl = Path(tmpdir.join("task_main.pkl"))

    task = multiply(name="mult", x=[1, 2], y=10).split("x")
    task.state.prepare_states(inputs=task.inputs)
    task.state.prepare_inputs()
    with task_pkl.open("wb") as fp:
        cp.dump(task, fp)

    task_0 = load_and_run(task_pkl=task_pkl, ind=0)
    assert task_0.result().output.out == 10
    task_1 = load_and_run(task_pkl=task_pkl, ind=1)
    assert task_1.result().output.out == 20
