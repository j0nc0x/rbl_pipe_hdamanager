#!/usr/bin/env python

"""Handle HDA packages."""

import json
import logging
import os
import re

import hou

from packaging.version import Version
from packaging.version import parse

from rbl_pipe_core.util import filesystem

from rbl_pipe_hdamanager import nodetype
from rbl_pipe_hdamanager import utilities

from rbl_pipe_houdini.utils import nodes


logger = logging.getLogger(__name__)


class HDARepo(object):
    """HDA Repository - associated with a rez package that contains Houdini HDAs."""

    __config = utilities.get_config()
    packages_root = __config.get("packages_root")

    def __init__(
        self,
        manager,
        repo_path,
        editable=False,
    ):
        """Initialise the HDA repo.

        Args:
            manager(HDAManager): An instance of the HDA manager currently being used.
            repo_path(str): The path on disk to where the HDA repository is located.
            editable(:obj:`bool`,optional): Are the HDAs in this repository editable?
        """
        self.manager = manager
        self.editable = editable
        self.repo_path = repo_path
        self.asset_subdirectory = "hda"
        self.node_types = dict()
        self.extensions = [".hda"]
        self.package_name = None
        self.package_version = None
        self.commit_hash = None

        if not self.editable:
            self.load_package_details()

        logger.info(
            "Initialised HDA Repo: {name} ({path})".format(
                name=self.package_name, path=self.repo_path
            )
        )

    def asset_directory(self):
        """Get the path to the HDA directory for the current HDA repo.

        Returns:
            (str): The path to the HDA directory on disk.
        """
        return os.path.join(self.repo_path, self.asset_subdirectory)

    def package_path(self):
        """Get the path to the HDA package.py file on disk.

        Returns:
            (str): The path to the package.py file for this HDA repo on disk.
        """
        return os.path.join(self.repo_path, "package.py")

    def repo_root(self):
        """Get the root of the HDA repo on the filesystem.

        Returns:
            (str): The path to the HDA repo on disk.
        """
        if self.editable:
            return self.repo_path

        return os.path.dirname(self.repo_path)

    def get_name(self):
        """Get the repo name.

        Returns:
            (str): The name of the HDA repo.
        """
        if self.editable:
            return "editable"
        else:
            return self.package_name

    def process_definition(self, definition, current_version=True, force=False):
        """Update the node_types dictionary usng the provided definition.

        Args:
            definition(hou.HDADefinition): The node definition to process.
            current_version(:obj:`bool`,optional): Is this definition part of the
                current package.
            force(:obj:`bool`,optional): Force the version to be processed irrespective
                of if it already exists.

        Returns:
            (None)
        """
        current_name = definition.nodeTypeName()
        category = definition.nodeTypeCategory().name()
        index = utilities.node_type_index(current_name, category)
        name = utilities.node_type_name(current_name)
        namespace = utilities.node_type_namespace(current_name)
        version = utilities.node_type_version(current_name)

        # Add the node_type to our dictionary if it doesn't already exist
        if index not in self.node_types:
            if current_version:
                hda_node_type = nodetype.NodeType(self.manager, name, namespace)
                self.node_types[index] = hda_node_type
            else:
                # We don't care about nodeTypes that no longer exist in the latest
                # package version.
                logger.debug(
                    "Skipping {name} as doesn't exist in latest vesion".format(
                        name=index
                    )
                )
                return

        # Skip any versions already loaded by another package version
        if (
            self.node_types[index].get_version(version)
            and not self.editable
            and not force
        ):
            logger.debug(
                "{index} already loaded from another package".format(index=index)
            )
            return

        # Skip any versions higher than the maximum (first) loaded version
        if version and not current_version:
            this_version = parse(version)
            max_version = self.node_types.get(index).max_version()
            if this_version > max_version:
                logger.debug(
                    "{index}: skipping version {ver} (Current version: {max})".format(
                        index=index,
                        ver=this_version,
                        max=max_version,
                    )
                )
                return

        # Otherwise load as normal
        self.node_types[index].add_version(
            version,
            definition,
            force=force,
        )

    def process_hda_file(self, path, current_version=True, force=False):
        """Process the given HDA file and handle any definitions it contains.

        Args:
            path(str): The path to the HDA file we are processing.
            current_version(:obj:`bool`,optional): Is this HDA part of the current
                version of the HDA package.
            force(:obj:`bool`,optional): Force the HDA to be installed.
        """
        definitions = hou.hda.definitionsInFile(path)
        for definition in definitions:
            self.process_definition(
                definition, current_version=current_version, force=force
            )

    def process_package_directory(self, asset_dir, current_version=True):
        """Process a rez package version for HDAs.

        Args:
            asset_dir(str): The HDA directory to read from.
            current_version(:obj:`bool`,optional): Is the directory being proccessed the
                current version.

        Raises:
            RuntimeError: The asset directory couldn't be loaded.
        """
        logger.debug("Reading from asset_dir {directory}".format(directory=asset_dir))

        if not os.path.exists(asset_dir):
            if self.editable:
                logger.info(
                    "Couldn't load asset_dir: {directory}".format(directory=asset_dir)
                )
                return
            else:
                raise RuntimeError(
                    "Couldn't load asset_dir: {directory}".format(directory=asset_dir)
                )

        for hda_file in os.listdir(asset_dir):
            if os.path.splitext(hda_file)[1].lower() in self.extensions:
                full_path = os.path.join(asset_dir, hda_file)
                self.process_hda_file(full_path, current_version=current_version)

    def process_ophide_list(self, ophide_list_path):
        """Process an ophide list at the given path.

        The ophide list is a JSON formatted file which incudes a 'hide_list' of node
        types to be hidden from the tab menu.

        Args:
            ophide_list_path(str): Path to the JSON file to read from.

        Returns:
            (None)
        """
        ophide_list_data = None
        with open(ophide_list_path, "r") as ophide_list:
            ophide_list_data = json.load(ophide_list)

        if not ophide_list_data:
            logger.warning(
                "ophide list failed to load from {path}".format(
                    path=ophide_list_path,
                )
            )
            return

        hide_list = ophide_list_data.get("hide_list")
        if not hide_list:
            logger.warning(
                "hide_list not found in {path}".format(
                    path=ophide_list_data,
                )
            )
            return

        for node_type_name in hide_list:
            node_type = self.node_types.get(node_type_name)
            if not node_type:
                logger.warning(
                    "Skipping ophide for definition not loaded: {nodetype}".format(
                        nodetype=node_type_name,
                    )
                )
                continue
            node_type.hide_all_versions()

    def load(self):
        """Load all definitions contained by this repository."""
        if self.editable:
            self.process_package_directory(self.repo_path)
        else:
            # Load the repo
            self.load_versions(self.repo_root())
            # Load package versions from main packages root if located elsewhere.
            if not filesystem.is_released(self.repo_root()):
                path = os.path.join(self.packages_root, self.package_name)
                logger.info(
                    "Repo root not located in main rez package location. Loading "
                    "additional versions from {path}".format(
                        path=path,
                    )
                )
                self.load_versions(path)

    def load_versions(self, repo_root, same_major_version=True):
        """Load previous versions of the HDA package.

        Look through previous versions of the rez package to find older versions of each
        hou.HDADefinition. By default this is limited to the current major version of
        the package repo.

        Args:
            repo_root(str): The root of the HDA package.
            same_major_version(:obj:`bool`,optional): Should the loading of previous
                versions be limited to the current major version.
        """
        current_version = parse(self.package_version)

        package_versions = [parse(ver) for ver in os.listdir(repo_root)]

        package_versions = [
            ver
            for ver in package_versions
            if isinstance(ver, Version) and ver <= current_version
        ]

        if same_major_version:
            package_versions = [
                ver for ver in package_versions if ver.major == current_version.major
            ]

        package_versions.sort(reverse=True)
        for version in package_versions:
            current = False
            if version == current_version:
                current = True

            asset_dir = os.path.join(repo_root, str(version), self.asset_subdirectory)
            self.process_package_directory(asset_dir, current_version=current)

            if current:
                ophide_list_path = os.path.join(repo_root, str(version), "ophide.json")
                if os.path.isfile(ophide_list_path):
                    self.process_ophide_list(ophide_list_path)

    def load_package_details(self):
        """Read the package.py file to determine the rez package and version.

        Returns:
            (None)
        """
        package_path = os.path.join(self.repo_path, "package.py")
        with open(package_path, "r") as file:
            package_contents = file.read()

        name_regex = re.compile(r"\nname\s*=\s*[\"'](.+)[\"']")
        name_match = name_regex.search(package_contents)
        if name_match:
            self.package_name = name_match.group(1)

        version_regex = re.compile(r"\nversion\s*=\s*[\"'](.+)[\"']")
        version_match = version_regex.search(package_contents)
        if version_match:
            self.package_version = version_match.group(1)

        logger.debug(
            "Loaded rez package details for {name}-{version}".format(
                name=self.package_name, version=self.package_version
            )
        )

        # try and load the commit hash for this release
        revision = re.compile(r"\nrevision =.*\n *{(.|\n)*?}")
        commit = re.compile(r"\s*'commit': '(.*)',")
        revision_match = revision.search(package_contents)
        if revision_match:
            commit_match = commit.search(revision_match.group(0))
            if commit_match:
                self.commit_hash = commit_match.group(1)
                logger.info(
                    "Release commit found for {name}.".format(
                        name=self.package_name,
                    )
                )
                return

        logger.warning(
            "Release commit not found for {name}.".format(
                name=self.package_name,
            )
        )

    def namespace_from_package(self):
        """Define the available namespaces as infered from the package name.

        ie. houdini_hdas_pipeline = rebellion.pipeline.

        Returns:
            (str): The namespace based on the package name.
        """
        if self.package_name.startswith("houdini_hdas_"):
            namespace = self.package_name[13:]

            return "rebellion.{namespace}".format(namespace=namespace)

        return None

    def available_namespaces(self):
        """Return a list of the namespaces available for this repo.

        Returns:
            (list): All namespaces available for the current repo.
        """
        if self.editable:
            return list()

        # Eventually load config here, to allow namespaces to be defined, but for now
        # just set a default based on the package name
        namespace = self.namespace_from_package()

        if namespace:
            return [namespace]

        return list()

    def update_node_type_name(
        self, current_node, node_type_name=None, namespace=None, name=None, version=None
    ):
        """Update nodeTypeName for the given definition.

        Args:
            current_node(hou.Node): The node to update the node type name for.
            node_type_name(:obj: `str`,optional): The node type name to update the node
                to.
            namespace(:obj: `str`,optional): The namespace component of the node name to
                update the node to.
            name(:obj: `str`,optional): The name component of the node name to update
                the node to.
            version(:obj: `str`,optional): The version component of the node name to
                update the node name to.

        Raises:
            RuntimeError: Nothing to update.
        """
        path = current_node.path()
        definition = nodes.definition_from_node(path)
        if node_type_name is not None and utilities.valid_node_type_name(
            node_type_name
        ):
            namespace = utilities.node_type_namespace(node_type_name)
            name = utilities.node_type_name(node_type_name)
            version = utilities.node_type_version(node_type_name)
        elif namespace is None and name is None and version is None:
            raise RuntimeError(
                "Nothing to update for {definition}".format(definition=definition)
            )

        # Copy and install definition modifying the nodetypename
        updated_node_type_name = self.add_definition_copy(
            definition,
            namespace=namespace,
            name=name,
            version=version,
        )

        # Clean-up the old nodetypename
        self.remove_definition(definition)

        # Update the node in the scene
        current_node.changeNodeType(updated_node_type_name)

        # Update the hda version to match the nodetype version
        updated_definition = nodes.definition_from_node(path)
        updated_definition.setVersion(version)

    def update_namespace(self, current_node, namespace):
        """Update the nodeType namespace for the given definition.

        Args:
            current_node(hou.Node): The node to update the namespace for.
            namespace(str): The namespace to update the node to.

        Raises:
            RuntimeError: Invalid namespace used.
        """
        # Validate the namespace is allowed
        all_namespaces = self.manager.all_available_namespaces()
        if namespace not in all_namespaces:
            raise RuntimeError(
                "{namespace} is an invalid namespace. Should be one of {all}".format(
                    namespace=namespace, all=all_namespaces
                )
            )

        self.update_node_type_name(self, current_node, namespace=namespace)

    def update_name(self, current_node, name):
        """Update the nodeType name for the given defintion.

        Args:
            current_node(hou.Node): The node to update the name for.
            name(str): The name to update the node to.
        """
        self.update_node_type_name(self, current_node, name=name)

    def update_version(self, current_node, version):
        """Update the nodeType version for the given defintion.

        Args:
            current_node(hou.Node): The node to update the version for.
            version(str): The version to update the node to.
        """
        self.update_node_type_name(self, current_node, version=version)

    def remove_definition(self, definition):
        """Remove the given defintion from the HDA Manager.

        Also uninistall the definition from the current session and back it up the .hda
        file.

        Args:
            definition(hou.HDADefinition): The node definition to remove.

        Raises:
            RuntimeError: NodeType not found.
        """
        # Remove version
        current_name = definition.nodeTypeName()
        category = definition.nodeTypeCategory().name()
        index = utilities.node_type_index(current_name, category)
        nodetype = self.manager.nodetype_from_definition(definition)
        nodetype.remove_version(definition)

        # Remove the nodetype if no versions remain
        if len(nodetype.versions) == 0:
            if index not in self.node_types:
                raise RuntimeError(
                    "NodeType {nodetype} not found in {repo}".format(
                        nodetype=index, repo=self.get_name()
                    )
                )
            del self.node_types[index]
            logger.debug(
                "Removed NodeType {nodetype} from {repo}".format(
                    nodetype=index, repo=self.get_name()
                )
            )
        else:
            logger.debug(
                "Nothing to remove. More than one version remains for "
                "{nodetype}.".format(nodetype=index)
            )

    def add_definition_copy(self, definition, namespace=None, name=None, version=None):
        """Create a copy of a node definition.

        Update the nodeTypeName if required.

        Args:
            definition(hou.HDADefinition): The node definition to copy.
            namespace(:obj:`str`,optional): The node namespace to use for the copy.
            name(:obj:`str`,optional): The node name to use for the copy.
            version(:obj:`str`,optional): The node version to use for the copy.

        Returns:
            (str): The name of the copied node.
        """
        # Write the HDA to the edit_dir
        editable_path = utilities.editable_hda_path_from_components(
            definition, self.manager.edit_dir, namespace=namespace, name=name
        )

        # See if we are updating the NodeTypeName
        if namespace or name or version:
            new_name = utilities.node_type_name_from_components(
                definition, namespace=namespace, name=name, version=version
            )
        else:
            new_name = None

        definition.copyToHDAFile(editable_path, new_name=new_name)
        logger.debug("Definition saved to {path}".format(path=editable_path))

        # Add the newly written HDA to the HDA Manager
        self.process_hda_file(editable_path, force=True)

        return new_name
