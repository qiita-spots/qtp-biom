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

from biom import Table
import numpy as np
from qiita_client.testing import PluginTestCase

from qtp_biom.summary import generate_html_summary, _generate_html


class SummaryTestsWith(PluginTestCase):
    def setUp(self):
        self.artifact_id = 4
        self.parameters = {'input_data': self.artifact_id}

        data = {'command': dumps(['BIOM type', '2.1.4',
                                  'Generate HTML summary']),
                'parameters': dumps(self.parameters),
                'status': 'running'}
        self.job_id = self.qclient.post(
            '/apitest/processing_job/', data=data)['job']

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
        obs_success, obs_ainfo, obs_error = generate_html_summary(
            self.qclient, self.job_id, self.parameters, self.out_dir)

        # asserting reply
        self.assertTrue(obs_success)
        self.assertIsNone(obs_ainfo)
        self.assertEqual(obs_error, "")

        # asserting content of html
        res = self.qclient.get("/qiita_db/artifacts/%s/" % self.artifact_id)
        html_fp = res['files']['html_summary'][0]
        self._clean_up_files.append(html_fp)

        with open(html_fp) as html_f:
            html = html_f.read()
        self.assertRegexpMatches(html, '\n'.join(EXP_HTML_REGEXP))

    def test_generate_html_summary_rarefied(self):
        # Create a new biom table
        data = np.asarray([[0, 2, 4], [2, 2, 2], [4, 2, 0]])
        table = Table(data, ['O1', 'O2', 'O3'], ['S1', 'S2', 'S3'])
        obs = _generate_html(table)
        self.assertEqual(obs, '\n'.join(EXP_HTML_RAREFIED))


EXP_HTML_REGEXP = [
    '<b>Number of samples:</b> 7<br/>',
    '<b>Number of features:</b> 4202<br/>',
    '<b>Minimum count:</b> 9594<br/>',
    '<b>Maximum count:</b> 14509<br/>',
    '<b>Median count:</b> 12713<br/>',
    '<b>Mean count:</b> 12472<br/>',
    '<br/><hr/><br/>',
    '<img src = "data:image/png;base64,.*"/>']

EXP_HTML_RAREFIED = [
    '<b>Number of samples:</b> 3<br/>',
    '<b>Number of features:</b> 3<br/>',
    '<b>Minimum count:</b> 6<br/>',
    '<b>Maximum count:</b> 6<br/>',
    '<b>Median count:</b> 6<br/>',
    '<b>Mean count:</b> 6<br/>',
    '<br/><hr/><br/>',
    'All the samples in your BIOM table have 6 sequences']


if __name__ == '__main__':
    main()
