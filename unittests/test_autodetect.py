# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import json
import os
import pytest

import unittests.utility as test_util
from reframe.core.runtime import runtime
from reframe.frontend.autodetect import detect_topology
from reframe.utility.cpuinfo import cpuinfo


@pytest.fixture
def exec_ctx(make_exec_ctx_g, tmp_path, monkeypatch):
    # Monkey-patch HOME, since topology is always written there
    monkeypatch.setenv('HOME', str(tmp_path))

    # Create a devices file manually, since it is not auto-generated
    meta_prefix = tmp_path / '.reframe' / 'topology' / 'generic-default'
    os.makedirs(meta_prefix)
    with open(meta_prefix / 'devices.json', 'w') as fp:
        json.dump([
            {
                'type': 'gpu',
                'arch': 'a100',
                'num_devices': 8
            }
        ], fp)

    yield from make_exec_ctx_g()


@pytest.fixture
def invalid_topo_exec_ctx(make_exec_ctx_g, tmp_path, monkeypatch):
    # Monkey-patch HOME, since topology is always written there
    monkeypatch.setenv('HOME', str(tmp_path))

    # Create invalid processor and devices files
    meta_prefix = tmp_path / '.reframe' / 'topology' / 'generic-default'
    os.makedirs(meta_prefix)
    with open(meta_prefix / 'processor.json', 'w') as fp:
        fp.write('{')

    with open(meta_prefix / 'devices.json', 'w') as fp:
        fp.write('{')

    yield from make_exec_ctx_g()


def test_autotect(exec_ctx):
    detect_topology()
    part = runtime().system.partitions[0]
    assert part.processor.info == cpuinfo()
    if part.processor.info:
        assert part.processor.num_cpus == part.processor.info['num_cpus']

    assert len(part.devices) == 1
    assert part.devices[0].info == {
        'type': 'gpu',
        'arch': 'a100',
        'num_devices': 8
    }
    assert part.devices[0].device_type == 'gpu'

    # Test immutability of ProcessorInfo and DeviceInfo
    with pytest.raises(AttributeError):
        part.processor.num_cpus = 3

    with pytest.raises(AttributeError):
        part.processor.foo = 10

    with pytest.raises(AttributeError):
        part.devices[0].arch = 'foo'

    with pytest.raises(AttributeError):
        part.devices[0].foo = 10


def test_autotect_with_invalid_files(invalid_topo_exec_ctx):
    detect_topology()
    part = runtime().system.partitions[0]
    assert part.processor.info == cpuinfo()
    assert part.devices == []


# FIXME: We should consider making these framework-wide fixtures

@pytest.fixture
def user_exec_ctx(make_exec_ctx_g):
    if test_util.USER_CONFIG_FILE is None:
        pytest.skip('no user configuration file supplied')

    yield from make_exec_ctx_g(test_util.USER_CONFIG_FILE,
                               test_util.USER_SYSTEM)


@pytest.fixture
def remote_exec_ctx(user_exec_ctx):
    partition = test_util.partition_by_scheduler()
    if not partition:
        pytest.skip('job submission not supported')

    return partition, partition.environs[0]


def test_remote_autodetect(remote_exec_ctx):
    # All we can do with this test is to trigger the remote auto-detection
    # path; since we don't know what the remote user system is, we cannot test
    # if the topology is right.
    detect_topology()
