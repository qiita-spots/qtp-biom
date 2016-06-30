# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
from tempfile import mkdtemp, mkstemp
from os import remove, environ, close
from os.path import exists, isdir
from shutil import rmtree
from json import dumps

import numpy as np
from biom import Table
from biom.util import biom_open
from qiita_client import QiitaClient

from qtp_biom.plugin import execute_job


CLIENT_ID = '19ndkO3oMKsoChjVVWluF7QkxHRfYhTKSFbAVt8IhK7gZgDaO4'
CLIENT_SECRET = ('J7FfQ7CQdOxuKhQAf1eoGgBAE81Ns8Gu3EKaWFm3IO2JKh'
                 'AmmCWZuabe0O5Mp28s1')


class PluginTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Reset the test database
        server_cert = environ.get('QIITA_SERVER_CERT', None)
        qclient = QiitaClient("https://localhost:21174", CLIENT_ID,
                              CLIENT_SECRET, server_cert=server_cert)
        qclient.post("/apitest/reset/")

    def setUp(self):
        self.server_cert = environ.get('QIITA_SERVER_CERT', None)
        self.qclient = QiitaClient("https://localhost:21174", CLIENT_ID,
                                   CLIENT_SECRET, server_cert=self.server_cert)

        fd, fp = mkstemp()
        close(fd)
        with open(fp, 'w') as f:
            f.write(CONFIG_FILE % (self.server_cert, CLIENT_ID, CLIENT_SECRET))
        environ['QP_BIOM_TYPE_CONFIG_FP'] = fp

        self.out_dir = mkdtemp()
        self._clean_up_files = [self.out_dir]

    def tearDown(self):
        for fp in self._clean_up_files:
            if exists(fp):
                if isdir(fp):
                    rmtree(fp)
                else:
                    remove(fp)

    def test_execute_job_summary(self):
        # Create a summary job
        data = {'command': 5,
                'parameters': dumps({'input_data': 4}),
                'status': 'queued'}
        job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

        execute_job("https://localhost:21174", job_id, self.out_dir)

        obs = self.qclient.get_job_info(job_id)
        self.assertEqual(obs['status'], 'success')

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
        data = {'command': 4,
                'parameters': dumps(
                    {'files': dumps({'BIOM': [biom_fp]}),
                     'template': template,
                     'artifact_type': 'BIOM'}),
                'artifact_type': 'BIOM',
                'status': 'queued'}
        job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

        execute_job("https://localhost:21174", job_id, self.out_dir)
        obs = self.qclient.get_job_info(job_id)
        self.assertEqual(obs['status'], 'success')

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
        data = {'command': 4,
                'parameters': dumps(
                    {'files': dumps({'BIOM': [biom_fp]}),
                     'template': template,
                     'artifact_type': 'BIOM'}),
                'artifact_type': 'BIOM',
                'status': 'queued'}
        job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

        execute_job("https://localhost:21174", job_id, self.out_dir)
        obs = self.qclient.get_job_info(job_id)
        self.assertEqual(obs['status'], 'error')

CONFIG_FILE = """
[main]
SERVER_CERT = %s

# Oauth2 plugin configuration
CLIENT_ID = %s
CLIENT_SECRET = %s
"""

if __name__ == '__main__':
    main()
