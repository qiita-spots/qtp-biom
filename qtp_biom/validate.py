# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from os.path import join, basename

from json import loads

from biom import load_table
from biom.util import biom_open
from biom.exception import TableException
from qiita_client import ArtifactInfo
from qiita_files.parse import load, FastaIterator
from .summary import _generate_html_summary, _generate_metadata_file
from skbio.tree import TreeNode


def validate(qclient, job_id, parameters, out_dir):
    """Validate and fix a new BIOM artifact

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
    bool, list of qiita_client.ArtifactInfo , str
        Whether the job is successful
        The artifact information, if successful
        The error message, if not successful
    """
    prep_id = parameters.get('template')
    analysis_id = parameters.get('analysis')
    files = loads(parameters['files'])
    a_type = parameters['artifact_type']

    if a_type != "BIOM":
        return (False, None, "Unknown artifact type %s. Supported types: BIOM"
                             % a_type)

    qclient.update_job_step(job_id, "Step 1: Collecting metadata")
    if prep_id is not None:
        is_analysis = False
        metadata = qclient.get("/qiita_db/prep_template/%s/data/" % prep_id)
        metadata = metadata['data']

        qurl = ('/qiita_db/prep_template/%s/' % prep_id)
        response = qclient.get(qurl)

        md = f'{out_dir}/merged_information_file.txt'
        _generate_metadata_file(response, md)
    elif analysis_id is not None:
        is_analysis = True
        metadata = qclient.get("/qiita_db/analysis/%s/metadata/" % analysis_id)

        md = metadata
    else:
        return (False, None, "Missing metadata information")

    # Check if the biom table has the same sample ids as the prep info
    qclient.update_job_step(job_id, "Step 2: Validating BIOM file")
    new_biom_fp = biom_fp = files['biom'][0]
    table = load_table(biom_fp)
    metadata_ids = set(metadata)
    biom_sample_ids = set(table.ids())

    if not metadata_ids.issuperset(biom_sample_ids):
        # The BIOM sample ids are different from the ones in the prep template
        qclient.update_job_step(job_id, "Step 3: Fixing BIOM sample ids")
        # Attempt 1: the user provided the run prefix column - in this case
        # the run prefix column holds the sample ids present in the BIOM file
        if 'run_prefix' in metadata[next(iter(metadata_ids))]:
            id_map = {v['run_prefix']: k for k, v in metadata.items()}
        else:
            # Attemp 2: the sample ids in the BIOM table are the same that in
            # the prep template but without the prefix
            prefix = next(iter(metadata_ids)).split('.', 1)[0]
            prefixed = set("%s.%s" % (prefix, s) for s in biom_sample_ids)
            if metadata_ids.issuperset(prefixed):
                id_map = {s: "%s.%s" % (prefix, s) for s in biom_sample_ids}
            else:
                # There is nothing we can do. The samples in the BIOM table do
                # not match the ones in the prep template and we can't fix it
                error_msg = ('The sample ids in the BIOM table do not match '
                             'the ones in the prep information. Please, '
                             'provide the column "run_prefix" in the prep '
                             'information to map the existing sample ids to '
                             'the prep information sample ids.')
                return False, None, error_msg

        # Fix the sample ids
        try:
            table.update_ids(id_map, axis='sample')
        except TableException:
            missing = biom_sample_ids - set(id_map)
            error_msg = ('Your prep information is missing samples that are '
                         'present in your BIOM table: %s' % ', '.join(missing))
            return False, None, error_msg

        new_biom_fp = join(out_dir, basename(biom_fp))
        with biom_open(new_biom_fp, 'w') as f:
            table.to_hdf5(f, "Qiita BIOM type plugin")

    filepaths = [(new_biom_fp, 'biom')]

    # Validate the representative set, if it exists
    if 'preprocessed_fasta' in files:
        repset_fp = files['preprocessed_fasta'][0]

        # The observations ids of the biom table should be the same
        # as the representative sequences ids found in the representative set
        observation_ids = table.ids(axis='observation').tolist()
        extra_ids = []
        for record in load([repset_fp], constructor=FastaIterator):
            rec_id = record['SequenceID'].split()[0]
            try:
                observation_ids.remove(rec_id)
            except ValueError:
                extra_ids.append(rec_id)

        error_msg = []
        if extra_ids:
            error_msg.append("The representative set sequence file includes "
                             "observations not found in the BIOM table: %s"
                             % ', '.join(extra_ids))
        if observation_ids:
            error_msg.append("The representative set sequence file is missing "
                             "observation ids found in the BIOM tabe: %s" %
                             ', '.join(observation_ids))

        if error_msg:
            return False, None, '\n'.join(error_msg)

        filepaths.append((repset_fp, 'preprocessed_fasta'))

    # Validate the sequence specific phylogenetic tree (e.g. generated
    # by SEPP for Deblur), if it exists
    tree = None
    if 'plain_text' in files:
        phylogeny_fp = files['plain_text'][0]

        try:
            tree = TreeNode.read(phylogeny_fp)
            filepaths.append((phylogeny_fp, 'plain_text'))
        except Exception:
            return False, None, ("Phylogenetic tree cannot be parsed "
                                 "via scikit-biom")

    for fp_type, fps in files.items():
        if fp_type not in ('biom', 'preprocessed_fasta', 'plain_text'):
            for fp in fps:
                filepaths.append((fp, fp_type))

    index_fp, viz_fp, qza_fp = _generate_html_summary(
        new_biom_fp, md, join(out_dir), is_analysis, tree)

    filepaths.append((index_fp, 'html_summary'))
    filepaths.append((viz_fp, 'html_summary_dir'))
    if 'qza' not in files:
        filepaths.append((qza_fp, 'qza'))

    return True, [ArtifactInfo(None, 'BIOM', filepaths)], ""
