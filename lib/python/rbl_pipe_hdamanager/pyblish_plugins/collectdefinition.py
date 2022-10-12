#!/usr/bin/env python

"""Collect node definitions to validate."""

import pyblish.api

from rbl_pipe_hdamanager import manager


class CollectDefinition(pyblish.api.ContextPlugin):
    """Collect Houdini nodes based on a given dictionary of node paths."""

    order = pyblish.api.CollectorOrder
    label = "Houdini HDA - Collect"

    def process(self, context):
        """Pyblish process method.

        Args:
            context(pyblish.Context): The Houdini node instances we are validating.
        """
        publish_node = manager.HDAManager.publish_node
        name = publish_node.type().name()
        instance = context.create_instance(name)
        instance[:] = [manager.HDAManager.publish_node]
