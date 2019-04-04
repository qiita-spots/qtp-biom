# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import main
from tempfile import mkdtemp, mkstemp
from os import remove, close
from os.path import exists, isdir
from shutil import rmtree
from json import dumps
from time import sleep

import numpy as np
from biom import Table
from biom.util import biom_open
from qiita_client.testing import PluginTestCase

from qtp_biom import plugin


class PluginTests(PluginTestCase):
    def setUp(self):
        self.out_dir = mkdtemp()
        self._clean_up_files = [self.out_dir]

    def tearDown(self):
        for fp in self._clean_up_files:
            if exists(fp):
                if isdir(fp):
                    rmtree(fp)
                else:
                    remove(fp)

    def _wait_job(self, job_id):
        for i in range(10):
            status = self.qclient.get_job_info(job_id)['status']
            if status != 'running':
                break
            sleep(0.5)
        return status

    def test_execute_job_summary(self):
        # Create a summary job
        data = {'command': dumps(['BIOM type', '2.1.4 - Qiime2',
                                  'Generate HTML summary']),
                'parameters': dumps({'input_data': 4}),
                'status': 'queued'}
        job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

        plugin("https://localhost:8383", job_id, self.out_dir)

        obs = self._wait_job(job_id)
        self.assertEqual(obs, 'success')

    def test_execute_job_validate(self):
        # Create a prep template
        prep_info = {'SKB8.640193': {'col': 'val1'},
                     'SKD8.640184': {'col': 'val2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        template = self.qclient.post(
            '/apitest/prep_template/', data=data)['prep']
        # Create a new validate job
        fd, biom_fp = mkstemp(suffix=".biom")
        close(fd)
        data = np.random.randint(100, size=(2, 2))
        table = Table(data, ['O1', 'O2'], ['SKB8.640193', 'SKD8.640184'])
        with biom_open(biom_fp, 'w') as f:
            table.to_hdf5(f, "Test")
        data = {'command': dumps(['BIOM type', '2.1.4 - Qiime2', 'Validate']),
                'parameters': dumps(
                    {'files': dumps({'biom': [biom_fp]}),
                     'template': template,
                     'artifact_type': 'BIOM'}),
                'artifact_type': 'BIOM',
                'status': 'queued'}
        job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

        plugin("https://localhost:8383", job_id, self.out_dir)
        obs = self._wait_job(job_id)
        self.assertEqual(obs, 'success')

    def test_execute_job_error(self):
        # Create a prep template
        prep_info = {'SKB8.640193': {'col': 'val1'},
                     'SKD8.640184': {'col': 'val2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        template = self.qclient.post(
            '/apitest/prep_template/', data=data)['prep']
        # Create a new validate job
        fd, biom_fp = mkstemp(suffix=".biom")
        close(fd)
        data = np.random.randint(100, size=(2, 2))
        table = Table(data, ['O1', 'O2'], ['S1', 'S2'])
        with biom_open(biom_fp, 'w') as f:
            table.to_hdf5(f, "Test")
        data = {'command': dumps(['BIOM type', '2.1.4 - Qiime2', 'Validate']),
                'parameters': dumps(
                    {'files': dumps({'biom': [biom_fp]}),
                     'template': template,
                     'artifact_type': 'BIOM'}),
                'artifact_type': 'BIOM',
                'status': 'queued'}
        job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

        plugin("https://localhost:8383", job_id, self.out_dir)
        obs = self._wait_job(job_id)

        self.assertEqual(obs, 'error')


if __name__ == '__main__':
    main()
