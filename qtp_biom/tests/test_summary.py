# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import main
from tempfile import mkdtemp
from os import remove
from os.path import exists, isdir
from shutil import rmtree
from json import dumps

from qiita_client.testing import PluginTestCase

from qtp_biom.summary import generate_html_summary


class SummaryTestsWith(PluginTestCase):
    def _generate_job(self):
        self.parameters = {'input_data': self.artifact_id}

        data = {'command': dumps(['BIOM type', '2.1.4',
                                  'Generate HTML summary']),
                'parameters': dumps(self.parameters),
                'status': 'running'}
        self.job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

    def setUp(self):
        self.artifact_id = 4
        self._generate_job()
        self.out_dir = mkdtemp()

        self._clean_up_files = [self.out_dir]

    def tearDown(self):
        for fp in self._clean_up_files:
            if exists(fp):
                if isdir(fp):
                    rmtree(fp)
                else:
                    remove(fp)

    def test_generate_html_summary(self):
        # testing regular biom
        obs_success, obs_ainfo, obs_error = generate_html_summary(
            self.qclient, self.job_id, self.parameters, self.out_dir)

        # asserting reply
        self.assertTrue(obs_success)
        self.assertIsNone(obs_ainfo)
        self.assertEqual(obs_error, "")

        # testing analysis biom
        self.artifact_id = 9
        self._generate_job()
        obs_success, obs_ainfo, obs_error = generate_html_summary(
            self.qclient, self.job_id, self.parameters, self.out_dir)


if __name__ == '__main__':
    main()
