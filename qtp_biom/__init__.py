# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from qiita_client import QiitaTypePlugin, QiitaArtifactType

from .validate import validate
from .summary import generate_html_summary

# Define the supported artifact types
artifact_types = [
    QiitaArtifactType('BIOM', 'BIOM table', False, False,
                      [('biom', True), ('directory', False), ('log', False)])]

# Initialize the plugin
plugin = QiitaTypePlugin('BIOM type', '2.1.4',
                         'The Biological Observation Matrix format',
                         validate, generate_html_summary,
                         artifact_types)
