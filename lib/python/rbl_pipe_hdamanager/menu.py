#!/usr/bin/env python

"""HDA manager menu utilities."""

import logging

from rbl_pipe_hdamanager import manager
from rbl_pipe_hdamanager import utilities

from rbl_pipe_houdini.utils import nodes

logger = logging.getLogger(__name__)


def get_hda_manager():
    """Find the HDAManager instance stored in the current Houdini session.

    Returns:
        (HDAManager): The instance for the running HDA manager.
    """
    return manager.HDAManager.init()


def in_edit_directory(current_node):
    """Check if the current_node definition is located in the HDAManager edit directory.

    Args:
        current_node(hou.Node): Check if definition is in the edit directory.

    Returns:
        (bool): Is the definition editable.
    """
    if nodes.definition_from_node(current_node.path()):
        manager = get_hda_manager()
        definition = nodes.definition_from_node(current_node.path())
        if definition.libraryFilePath().startswith(manager.edit_dir):
            return True
    return False


def display_main_menu(current_node):
    """Check if the main HDAManager menu should be displayed for the current_node.

    Args:
        current_node(hou.Node): Check if the main menu should be displayed.

    Returns:
        (bool): Display the menu?
    """
    return nodes.is_digital_asset(
        current_node.path()
    ) and not utilities.using_embedded_definition(current_node)


def display_make_editable(current_node):
    """Check if the Edit with HDA Manager menu should be displayed for the current_node.

    Args:
        current_node(hou.Node): Check if the editable menu should be displayed.

    Returns:
        (bool): Display the menu?
    """
    return (
        nodes.is_digital_asset(current_node.path())
        and not utilities.using_embedded_definition(current_node)
        and not in_edit_directory(current_node)
    )


def display_discard_editable(current_node):
    """Check if the Discard Definition menu should be displayed for the current_node.

    Args:
        current_node(hou.Node): Check if the discard menu should be displayed.

    Returns:
        (bool): Display the menu?
    """
    return nodes.is_digital_asset(current_node.path()) and in_edit_directory(
        current_node
    )


def display_configure(current_node):
    """Check if the Configure Definition menu should be displayed for the current_node.

    Args:
        current_node(hou.Node): Check if the configure menu should be displayed.

    Returns:
        (bool): Display the menu?
    """
    return nodes.is_digital_asset(current_node.path()) and in_edit_directory(
        current_node
    )


def display_publish(current_node):
    """Check if the Publish Definition menu should be displayed for the current_node.

    Args:
        current_node(hou.Node): Check if the display menu should be displayed.

    Returns:
        (bool): Display the menu?
    """
    if (
        utilities.allow_publish()
        and nodes.is_digital_asset(current_node.path())
        and in_edit_directory(current_node)
    ):
        return True
    return False


def publish_locked(current_node):
    """Check if publishing is locked for the current session.

    Args:
        current_node(hou.Node): Check if publishing is locked.

    Returns:
        (bool): Is publish locked?
    """
    return not utilities.allow_publish()


def project_locked(current_node):
    """Check if publishing is locked to the project for the current session.

    Args:
        current_node(hou.Node): Check if publishing is locked to the current project.

    Returns:
        (bool): Is publish locked to the current show?
    """
    return utilities.allow_show_publish()


def make_editable(current_node):
    """Edit with HDA Manager callback.

    Args:
        current_node(hou.Node): The node to make an editable definition for.
    """
    man = get_hda_manager()
    man.edit_definition(current_node)


def discard_editable(current_node):
    """Discard Definition callback.

    Args:
        current_node(hou.Node): The node to discard the editable definition for.
    """
    man = get_hda_manager()
    man.discard_definition(current_node)


def configure(current_node):
    """Configure Definition callback.

    Args:
        current_node(hou.Node): The node to load the configure UI for.
    """
    man = get_hda_manager()
    man.configure_definition(current_node)


def publish(current_node):
    """Publish Definition callback.

    Args:
        current_node(hou.Node): The node to publish the definition for.
    """
    man = get_hda_manager()
    man.prepare_publish(current_node)


def history(current_node):
    """Release history callback.

    Args:
        current_node(hou.Node): The node to load the release history for.
    """
    man = get_hda_manager()
    man.release_history(current_node)
