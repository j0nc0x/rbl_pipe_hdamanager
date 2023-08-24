#!/usr/bin/env python

"""HDA manager configuration UI."""

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from packaging.version import parse

from rbl_pipe_hdamanager import utilities

from rbl_pipe_houdini.utils import nodes


class ConfigureWindow(QWidget):
    """Qt Window for the Configure UI."""

    def __init__(self, manager, current_node, parent=None):
        """Initialise the ConfigureWindow.

        Args:
            manager(HDAManager): The instance of the running HDA manager.
            current_node(hou.Node): The node we are running the configuration windo for.
            parent(:obj:`QWindow`,optional): The parent application.
        """
        super(ConfigureWindow, self).__init__(parent)

        self.manager = manager
        self.current_node = current_node
        self.definition = nodes.definition_from_node(current_node.path())
        self.setLayout(QVBoxLayout())
        self.setup_window()
        self.setup_contents()

    def setup_window(self):
        """Set up the window."""
        # Work out window geometry
        position = QtGui.QCursor().pos()
        curx = position.x()
        cury = position.y()
        width = 600
        height = 200
        x = curx - (width / 2)
        y = cury - (height / 2)
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.setGeometry(x, y, width, height)
        self.setFixedSize(width, height)
        self.setWindowTitle("HDA Manager: Configure HDA")

    def setup_contents(self):
        """Set up the window contents and configure the callbacks."""
        current_name = self.definition.nodeTypeName()

        # Current nodeTypeName
        current_name_layout = QHBoxLayout()
        label = QLabel("Current nodeTypeName")
        label.setFixedWidth(150)
        current_name_layout.addWidget(label)
        self.current_name = QLabel(current_name)
        current_name_layout.addWidget(self.current_name)
        self.layout().addLayout(current_name_layout)

        # Updated nodeTypeName
        updated_name_layout = QHBoxLayout()
        label = QLabel("Updated nodeTypeName")
        label.setFixedWidth(150)
        updated_name_layout.addWidget(label)
        self.updated_name = QLabel()
        updated_name_layout.addWidget(self.updated_name)
        self.layout().addLayout(updated_name_layout)

        # Namespace
        namespace_layout = QHBoxLayout()
        label = QLabel("Namespace")
        label.setFixedWidth(150)
        namespace_layout.addWidget(label)
        self.namespace = QComboBox()
        self.namespace.addItems(self.manager.all_available_namespaces())
        index = self.namespace.findText(
            utilities.node_type_namespace(current_name), QtCore.Qt.MatchFixedString
        )
        if index >= 0:
            self.namespace.setCurrentIndex(index)
        namespace_layout.addWidget(self.namespace)
        self.layout().addLayout(namespace_layout)

        # Name
        name_layout = QHBoxLayout()
        label = QLabel("Name")
        label.setFixedWidth(150)
        name_layout.addWidget(label)
        self.name = QLineEdit(utilities.node_type_name(current_name))
        name_layout.addWidget(self.name)
        self.layout().addLayout(name_layout)

        # Version
        version_layout = QHBoxLayout()
        label = QLabel("Version")
        label.setFixedWidth(150)
        version_layout.addWidget(label)
        self.version = QComboBox()
        version_layout.addWidget(self.version)
        self.layout().addLayout(version_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.update_button = QPushButton("Update")
        button_layout.addWidget(self.update_button)
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.cancel_button)
        self.layout().addLayout(button_layout)

        self.update_version_menu()

        #  Callbacks
        self.namespace.currentIndexChanged.connect(self.update_version_menu)
        self.name.textEdited.connect(self.update_version_menu)
        self.version.currentIndexChanged.connect(self.update_node_type_name)
        self.update_button.clicked.connect(self.update)
        self.cancel_button.clicked.connect(self.close)

    def update_version_menu(self):
        """Update the version menu.

        This callback is run when changes are made to the namespace or name.
        """
        namespace = self.namespace.currentText()
        name = self.name.text()
        category = self.definition.nodeTypeCategory().name()
        menu = list()
        current_version = self.manager.current_node_type_version(
            category, namespace, name
        )
        if current_version:
            version = parse(current_version)
            major_increment = "{major}.{minor}.{patch}".format(
                major=version.major + 1, minor=0, patch=0
            )
            minor_increment = "{major}.{minor}.{patch}".format(
                major=version.major, minor=version.minor + 1, patch=0
            )
            patch_increment = "{major}.{minor}.{patch}".format(
                major=version.major, minor=version.minor, patch=version.micro + 1
            )
            menu.append("No change ({version})".format(version=current_version))
            menu.append("Increment Major ({version})".format(version=major_increment))
            menu.append("Increment Minor ({version})".format(version=minor_increment))
            menu.append("Increment Patch ({version})".format(version=patch_increment))
        else:
            menu.append("Initial Version (1.0.0)")

        self.version.clear()
        self.version.addItems(menu)

        self.update_node_type_name()

    def update_node_type_name(self):
        """Update the node type name.

        This callback is run when changes are made in the dialog.
        """
        namespace = self.namespace.currentText()
        name = self.name.text()
        category = self.definition.nodeTypeCategory().name()

        version_selection = self.version.currentText()
        version = self.manager.current_node_type_version(category, namespace, name)
        if not version:
            updated_version = "1.0.0"
        elif version_selection.startswith("Increment Major"):
            parsed_version = parse(version)
            updated_version = "{major}.{minor}.{patch}".format(
                major=parsed_version.major + 1, minor=0, patch=0
            )
        elif version_selection.startswith("Increment Minor"):
            parsed_version = parse(version)
            updated_version = "{major}.{minor}.{patch}".format(
                major=parsed_version.major, minor=parsed_version.minor + 1, patch=0
            )
        elif version_selection.startswith("Increment Patch"):
            parsed_version = parse(version)
            updated_version = "{major}.{minor}.{patch}".format(
                major=parsed_version.major,
                minor=parsed_version.minor,
                patch=parsed_version.micro + 1,
            )
        else:
            updated_version = version

        updated_name = "{namespace}::{name}::{version}".format(
            namespace=namespace, name=name, version=updated_version
        )
        self.updated_name.setText(updated_name)

        self.update_buttons()

    def update_buttons(self):
        """Configure which buttons are enabled."""
        if self.current_name.text() == self.updated_name.text():
            self.update_button.setEnabled(False)
        else:
            self.update_button.setEnabled(True)

    def update(self):
        """Update the definition.

        This callback is run when the update button is clicked.
        """
        repo = self.manager.repo_from_definition(self.definition)
        repo.update_node_type_name(
            self.current_node, node_type_name=self.updated_name.text()
        )
        self.close()
