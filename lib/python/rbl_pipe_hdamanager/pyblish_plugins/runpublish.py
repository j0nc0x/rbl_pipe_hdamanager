#!/usr/bin/env python

"""Run HDA publish."""

import pyblish.api

from rbl_pipe_hdamanager import manager


class RunPublish(pyblish.api.InstancePlugin):
    """Pyblish plugin to continue with the HDA publish."""

    order = pyblish.api.ExtractorOrder
    label = "Houdini HDA - Run Publish"

    def process(self, instance):
        """Pyblish process method.

        Args:
            instance(:obj:`list` of :obj:`hou.Node`): The Houdini node instances we are
                validating.
        """
        man = manager.HDAManager.init()
        for node in instance:
            man.publish_definition(node)
            manager.HDAManager.validator_ui.stop()
