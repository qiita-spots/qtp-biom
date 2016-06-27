# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
from tempfile import mkstemp, mkdtemp
from os import close, remove
from os.path import exists, isdir, join, basename
from shutil import rmtree

import numpy as np
from biom import Table

from biom.util import biom_open
from qiita_client import QiitaClient
import httpretty

from qtp_biom.summary import generate_html_summary


class SummaryTestsWith(TestCase):
    @httpretty.activate
    def setUp(self):
        # Registewr the URIs for the QiitaClient
        httpretty.register_uri(
            httpretty.POST,
            "https://test_server.com/qiita_db/authenticate/",
            body='{"access_token": "token", "token_type": "Bearer", '
                 '"expires_in": "3600"}')

        self.qclient = QiitaClient('https://test_server.com', 'client_id',
                                   'client_secret')
        # Create a biom table
        fd, self.biom_fp = mkstemp(suffix=".biom")
        close(fd)
        data = np.asarray([[0, 0, 1], [1, 3, 42]])
        table = Table(data, ['O1', 'O2'], ['1.S1', '1.S2', '1.S3'])
        with biom_open(self.biom_fp, 'w') as f:
            table.to_hdf5(f, "Test")
        self.out_dir = mkdtemp()
        self.artifact_id = 4
        self.parameters = {'input_data': self.artifact_id}

        self._clean_up_files = [self.biom_fp, self.out_dir]

    def tearDown(self):
        for fp in self._clean_up_files:
            if exists(fp):
                if isdir(fp):
                    rmtree(fp)
                else:
                    remove(fp)

    @httpretty.activate
    def test_generate_html_summary(self):
        httpretty_url = ("https://test_server.com/qiita_db/artifacts/"
                         "%s/filepaths/" % self.artifact_id)
        httpretty.register_uri(
            httpretty.GET, httpretty_url,
            body=('{"filepaths": [["%s", "biom"]]}' % self.biom_fp))
        httpretty.register_uri(httpretty.PATCH, httpretty_url)
        obs_success, obs_ainfo, obs_error = generate_html_summary(
            self.qclient, 'job-id', self.parameters, self.out_dir)

        # asserting reply
        self.assertTrue(obs_success)
        self.assertIsNone(obs_ainfo)
        self.assertEqual(obs_error, "")

        # asserting content of html
        html_fp = join(self.out_dir, "%s.html" % basename(self.biom_fp))
        with open(html_fp) as html_f:
            html = html_f.read()
        self.assertRegexpMatches(html, '\n'.join(EXP_HTML_REGEXP))

EXP_HTML_REGEXP = [
    '<b>Number of samples:</b> 3<br/>',
    '<b>Number of features:</b> 2<br/>',
    '<b>Minimum count:</b> 1<br/>',
    '<b>Maximum count:</b> 43<br/>',
    '<b>Median count:</b> 3<br/>',
    '<b>Mean count:</b> 15<br/>',
    '<br/><hr/><br/>',
    '<img src = "data:image/png;base64,.*"/>']

if __name__ == '__main__':
    main()
