# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------


import pandas as pd
from os.path import join, basename
from json import dumps

import qiime2
from qiime2.plugins.feature_table.visualizers import summarize


Q2_INDEX = """<!DOCTYPE html>
<html>
  <body>
    <iframe src="./support_files/%s" width="100%%" height="850" frameborder=0>
    </iframe>
  </body>
</html>"""


def _generate_html_summary(biom_fp, metadata, out_dir, is_analysis):
    if is_analysis:
        metadata = qiime2.Metadata(pd.DataFrame.from_dict(
            metadata, orient='index'))
    else:
        metadata = qiime2.Metadata.load(metadata)

    table = qiime2.Artifact.import_data('FeatureTable[Frequency]', biom_fp)

    summary, = summarize(table=table, sample_metadata=metadata)
    index_paths = summary.get_index_paths()
    # this block is not really necessary but better safe than sorry
    if 'html' not in index_paths:
        return (False, None,
                "Only Qiime 2 visualization with an html index are supported")

    index_name = basename(index_paths['html'])
    index_fp = join(out_dir, 'index.html')
    with open(index_fp, 'w') as f:
        f.write(Q2_INDEX % index_name)

    viz_fp = join(out_dir, 'support_files')
    summary.export_data(viz_fp)

    return (index_fp, viz_fp)


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
        md = qclient.get(qurl)['qiime-map']
    else:
        is_analysis = True
        qurl = '/qiita_db/analysis/%s/metadata/' % artifact_info['analysis']
        md = qclient.get(qurl)

    # Step 3: generate HTML summary
    # if we get to this point of the code we are sure that this is a biom file
    # and that it only has one element
    index_fp, viz_fp = _generate_html_summary(
        artifact_info['files']['biom'][0], md, out_dir, is_analysis)

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
