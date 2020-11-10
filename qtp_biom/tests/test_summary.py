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
from os.path import exists, isdir, join
from shutil import rmtree
from json import dumps
from skbio.tree import TreeNode

from qiita_client.testing import PluginTestCase

from qtp_biom.summary import generate_html_summary, _generate_html_summary


class SummaryTestsWith(PluginTestCase):
    def _generate_job(self):
        self.parameters = {'input_data': self.artifact_id}

        data = {'command': dumps(['BIOM type', '2.1.4 - Qiime2',
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
        self.assertEqual(obs_error, "")
        self.assertTrue(obs_success)
        self.assertIsNone(obs_ainfo)

        # testing analysis biom
        self.out_dir = mkdtemp()
        self._clean_up_files.append(self.out_dir)
        self.artifact_id = 9
        self._generate_job()
        obs_success, obs_ainfo, obs_error = generate_html_summary(
            self.qclient, self.job_id, self.parameters, self.out_dir)

        # asserting reply
        self.assertEqual(obs_error, "")
        self.assertTrue(obs_success)
        self.assertIsNone(obs_ainfo)

    def test__generate_html_summary_phylogeny(self):
        fp_biom = join('qtp_biom', 'support_files', 'sepp.biom')
        fp_tree = join('qtp_biom', 'support_files', 'sepp.tre')

        # load metadata
        qurl = '/qiita_db/analysis/%s/metadata/' % 1
        md = self.qclient.get(qurl)

        # load phylogeny
        tree = TreeNode.read(fp_tree)

        obs_index_fp, obs_viz_fp, qza_fp = _generate_html_summary(
            fp_biom, md, self.out_dir, True, tree=tree)

        # test if two expected tags show up in the html summary page
        with open(obs_index_fp) as f:
            obs_html = ''.join(f.readlines())
            self.assertTrue('<th>Number placed fragments</th>' in obs_html)
            self.assertTrue('<td>434</td>' in obs_html)

        # test that phylogeny specific html content does not show up if no
        # tree is given
        obs_index_fp, obs_viz_fp, qza_fp = _generate_html_summary(
            fp_biom, md, self.out_dir, True, tree=None)
        with open(obs_index_fp) as f:
            obs_html = ''.join(f.readlines())
            self.assertTrue('<th>Number placed fragments</th>' not in obs_html)


if __name__ == '__main__':
    main()
