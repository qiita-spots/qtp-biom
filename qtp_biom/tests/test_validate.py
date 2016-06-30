# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
from tempfile import mkstemp, mkdtemp
from os import close, remove, environ
from os.path import exists, isdir, join, basename
from shutil import rmtree
from json import dumps

import numpy as np
from biom import Table, load_table
from biom.util import biom_open
from qiita_client import QiitaClient, ArtifactInfo

from qtp_biom.validate import validate

CLIENT_ID = '19ndkO3oMKsoChjVVWluF7QkxHRfYhTKSFbAVt8IhK7gZgDaO4'
CLIENT_SECRET = ('J7FfQ7CQdOxuKhQAf1eoGgBAE81Ns8Gu3EKaWFm3IO2JKh'
                 'AmmCWZuabe0O5Mp28s1')


class CreateTests(TestCase):
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
        self.out_dir = mkdtemp()

        self._clean_up_files = [self.out_dir]

    def tearDown(self):
        for fp in self._clean_up_files:
            if exists(fp):
                if isdir(fp):
                    rmtree(fp)
                else:
                    remove(fp)

    def _create_job_and_biom(self, sample_ids, template=1):
        # Create the BIOM table that needs to be valdiated
        fd, biom_fp = mkstemp(suffix=".biom")
        close(fd)
        data = np.random.randint(100, size=(2, len(sample_ids)))
        table = Table(data, ['O1', 'O2'], sample_ids)
        with biom_open(biom_fp, 'w') as f:
            table.to_hdf5(f, "Test")
        self._clean_up_files.append(biom_fp)

        # Create a new job
        parameters = {'template': template,
                      'files': dumps({'BIOM': [biom_fp]}),
                      'artifact_type': 'BIOM'}
        data = {'command': 4,
                'parameters': dumps(parameters),
                'status': 'running'}
        res = self.qclient.post('/apitest/processing_job/', data=data)
        job_id = res['job']

        return biom_fp, job_id, parameters

    def test_validate_unknown_type(self):
        parameters = {'template': 1, 'files': dumps({'BIOM': ['ignored']}),
                      'artifact_type': 'UNKNOWN'}
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, 'job-id', parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        exp = 'Unknown artifact type UNKNOWN. Supported types: BIOM'
        self.assertEqual(obs_error, exp)

    def test_validate_no_changes(self):
        sample_ids = ['1.SKB2.640194', '1.SKM4.640180', '1.SKB3.640195',
                      '1.SKB6.640176', '1.SKD6.640190', '1.SKM6.640187',
                      '1.SKD9.640182', '1.SKM8.640201', '1.SKM2.640199',
                      '1.SKD2.640178', '1.SKB7.640196', '1.SKD4.640185',
                      '1.SKB8.640193', '1.SKM3.640197', '1.SKD5.640186',
                      '1.SKB1.640202', '1.SKM1.640183', '1.SKD1.640179',
                      '1.SKD3.640198', '1.SKB5.640181', '1.SKB4.640189',
                      '1.SKB9.640200', '1.SKM9.640192', '1.SKD8.640184',
                      '1.SKM5.640177', '1.SKM7.640188', '1.SKD7.640191']
        biom_fp, job_id, parameters = self._create_job_and_biom(sample_ids)

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [(biom_fp, 'biom')])])
        self.assertEqual(obs_error, "")

    def test_validate_no_changes_superset(self):
        sample_ids = ['1.SKB2.640194', '1.SKM4.640180', '1.SKB3.640195',
                      '1.SKB6.640176', '1.SKD6.640190', '1.SKM6.640187',
                      '1.SKD9.640182', '1.SKM8.640201', '1.SKM2.640199']
        biom_fp, job_id, parameters = self._create_job_and_biom(sample_ids)
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [(biom_fp, 'biom')])])
        self.assertEqual(obs_error, "")

    def test_validate_unknown_samples(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1'},
            'SKD8.640184': {'col': 'val2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['Sample1', 'Sample2', 'Sample3']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        exp = ('The sample ids in the BIOM table do not match the ones in the '
               'prep information. Please, provide the column "run_prefix" in '
               'the prep information to map the existing sample ids to the '
               'prep information sample ids.')
        self.assertEqual(obs_error, exp)

    def test_validate_missing_samples(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1',
                            'run_prefix': 'Sample1'},
            'SKD8.640184': {'col': 'val2',
                            'run_prefix': 'Sample2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['Sample1', 'Sample2', 'New.Sample']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        self.assertFalse(obs_success)
        self.assertIsNone(obs_ainfo)
        exp = ('Your prep information is missing samples that are present in '
               'your BIOM table: New.Sample')
        self.assertEqual(obs_error, exp)

    def test_validate_run_prefix(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1',
                            'run_prefix': 'Sample1'},
            'SKD8.640184': {'col': 'val2',
                            'run_prefix': 'Sample2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['Sample1', 'Sample2']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])
        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        exp_biom_fp = join(self.out_dir, basename(biom_fp))
        self._clean_up_files.append(exp_biom_fp)
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [(exp_biom_fp, 'biom')])])
        self.assertEqual(obs_error, "")
        obs_t = load_table(exp_biom_fp)
        self.assertItemsEqual(obs_t.ids(), ["1.SKB8.640193", "1.SKD8.640184"])

    def test_validate_prefix(self):
        prep_info = {
            'SKB8.640193': {'col': 'val1'},
            'SKD8.640184': {'col': 'val2'}}
        data = {'prep_info': dumps(prep_info),
                'study': 1,
                'data_type': '16S'}
        res = self.qclient.post('/apitest/prep_template/', data=data)

        sample_ids = ['SKB8.640193', 'SKD8.640184']
        biom_fp, job_id, parameters = self._create_job_and_biom(
            sample_ids, template=res['prep'])

        obs_success, obs_ainfo, obs_error = validate(
            self.qclient, job_id, parameters, self.out_dir)
        exp_biom_fp = join(self.out_dir, basename(biom_fp))
        self._clean_up_files.append(exp_biom_fp)
        self.assertTrue(obs_success)
        self.assertEqual(
            obs_ainfo, [ArtifactInfo(None, 'BIOM', [(exp_biom_fp, 'biom')])])
        self.assertEqual(obs_error, "")
        obs_t = load_table(exp_biom_fp)
        self.assertItemsEqual(obs_t.ids(), ['1.SKB8.640193', '1.SKD8.640184'])

if __name__ == '__main__':
    main()
