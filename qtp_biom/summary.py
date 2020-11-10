# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from os import remove
from os.path import join, basename
from json import dumps
import pandas as pd
from tempfile import mkstemp

import qiime2
from qiime2.plugins.feature_table.visualizers import summarize
from skbio.tree import TreeNode
from biom import load_table


Q2_INDEX = """<!DOCTYPE html>
<html>
  <body>
    %s <!-- summarizing phylogenetic tree, if existent -->
    <iframe src="./support_files/%s" width="100%%" height="850" frameborder=0>
    </iframe>
  </body>
</html>"""


def _generate_metadata_file(response, out_fp):
    """Method to minimize code duplication: merges the prep/sample info files

    Parameters
    ----------
    response : dict
        The response from checking a preparation from Qiita
    out_fp : str
        The filepath where we want to store the merged metadata
    """
    sf = pd.read_csv(response['sample-file'], sep='\t', dtype='str',
                     na_values=[], keep_default_na=True)
    pf = pd.read_csv(response['prep-file'], sep='\t', dtype='str',
                     na_values=[], keep_default_na=True)
    sf.set_index('sample_name', inplace=True)
    pf.set_index('sample_name', inplace=True)
    # merging sample and info files
    df = pf.join(sf, lsuffix="_prep")
    df.to_csv(out_fp, sep='\t')


def _generate_html_summary(biom_fp, metadata, out_dir, is_analysis, tree=None):
    if is_analysis:
        # we need to save and load the df so qiime does it's magic for parsing
        # columns
        fd, path = mkstemp()
        df = pd.DataFrame.from_dict(metadata, orient='index')
        df.to_csv(path, index_label='#SampleID', na_rep='', sep='\t',
                  encoding='utf-8')
        metadata = qiime2.Metadata.load(path)
        remove(path)
    else:
        metadata = qiime2.Metadata.load(metadata)

    table = qiime2.Artifact.import_data('FeatureTable[Frequency]', biom_fp)

    summary, = summarize(table=table, sample_metadata=metadata)
    index_paths = summary.get_index_paths()
    # this block is not really necessary but better safe than sorry
    if 'html' not in index_paths:
        return (False, None,
                "Only Qiime 2 visualization with an html index are supported")

    # gather some stats about the phylogenetic tree if exists
    summary_tree = ""
    if tree is not None:
        num_placements = len([
            1
            for tip
            in tree.tips()
            if (tip.name is not None) and (not tip.name.isdigit())])
        num_tips_reference = tree.count(tips=True) - num_placements
        num_rejected = len(load_table(biom_fp).ids(axis='observation')) - \
            num_placements
        summary_tree = (
            "    <table>\n"
            "      <tr>\n"
            "        <th>Number placed fragments</th>\n"
            "        <td>%s</td>\n"
            "      </tr>\n"
            "      <tr>\n"
            "        <th>Number rejected fragments</th>\n"
            "        <td>%s</td>\n"
            "      </tr>\n"
            "      <tr>\n"
            "        <th>Number tips in reference</th>\n"
            "        <td>%s</td>\n"
            "      </tr>\n"
            "    </table>") % (num_placements, num_rejected,
                               num_tips_reference)

    index_name = basename(index_paths['html'])
    index_fp = join(out_dir, 'index.html')
    with open(index_fp, 'w') as f:
        f.write(Q2_INDEX % (summary_tree, index_name))

    viz_fp = join(out_dir, 'support_files')
    summary.export_data(viz_fp)

    table_fp = table.save(join(out_dir, 'feature-table.qza'))

    return (index_fp, viz_fp, table_fp)


def generate_html_summary(qclient, job_id, parameters, out_dir):
    """Generates the HTML summary of a BIOM artifact

    Parameters
    ----------
    qclient : qiita_client.QiitaClient
        The Qiita server client
    job_id : str
        The job id
    parameters : dict
        The parameter values to validate and create the artifact
    out_dir : str
        The path to the job's output directory

    Returns
    -------
    bool, None, str
        Whether the job is successful
        Ignored
        The error message, if not successful
    """
    # Step 1: gather file information from qiita using REST api
    artifact_id = parameters['input_data']
    qclient_url = "/qiita_db/artifacts/%s/" % artifact_id
    artifact_info = qclient.get(qclient_url)

    # Step 2: get the mapping file, depends if analysis or not
    if artifact_info['analysis'] is None:
        is_analysis = False
        qurl = ('/qiita_db/prep_template/%s/' %
                artifact_info['prep_information'][0])
        response = qclient.get(qurl)
        md = f'{out_dir}/merged_information_file.txt'
        _generate_metadata_file(response, md)
    else:
        is_analysis = True
        qurl = '/qiita_db/analysis/%s/metadata/' % artifact_info['analysis']
        md = qclient.get(qurl)

    tree = None
    if 'plain_text' in artifact_info['files']:
        tree = TreeNode.read(artifact_info['files']['plain_text'][0])

    # Step 3: generate HTML summary
    # if we get to this point of the code we are sure that this is a biom file
    # and that it only has one element
    index_fp, viz_fp, qza_fp = _generate_html_summary(
        artifact_info['files']['biom'][0], md, out_dir, is_analysis, tree)

    # Step 4: add the new file to the artifact using REST api
    success = True
    error_msg = ""
    try:
        qclient.patch(qclient_url, 'add', '/html_summary/',
                      value=dumps({'html': index_fp, 'dir': viz_fp}))
    except Exception as e:
        success = False
        error_msg = str(e)

    return success, None, error_msg
