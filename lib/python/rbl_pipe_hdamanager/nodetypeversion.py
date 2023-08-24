#!/usr/bin/env python

"""HDA manager node type version."""

import logging

import hou

from rbl_pipe_hdamanager import utilities

logger = logging.getLogger(__name__)


class NodeTypeVersion(object):
    """NodeTypeVersion - Details about a specific version of a Houdini NodeType."""

    def __init__(
        self,
        path,
        definition=None,
        install=False,
    ):
        """
        Initalise the NodeTypeVersion.

        Args:
            path(str): The path to the HDA that containst this version.
            definition(:obj:`hou.HDADefinition`,optional): The definition for this
                version.
            install(:obj:`bool`,optional): Should this version be installed.
        """
        logger.debug("Initialised NodeTypeVersion: {version}".format(version=self))
        self.path = path
        self.definition = definition
        self.installed = False
        if install:
            self.install_definition()

    def install_definition(self):
        """Install this definition into the current Houdini session."""
        path = self.definition.libraryFilePath()
        hou.hda.installFile(
            path,
            oplibraries_file="Scanned Asset Library Directories",
            force_use_assets=True,
        )

        self.installed = True
        logger.info("Installed file {path}".format(path=path))

        utilities.cleanup_embedded_definitions(self.definition.nodeType())

    def hide(self):
        """Hide this node type definition."""
        if self.definition.isInstalled():
            node_type = self.definition.nodeType()
            logger.info("Hiding {node_type}".format(node_type=node_type))
            node_type.setHidden(True)
