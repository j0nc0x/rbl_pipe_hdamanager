#!/usr/bin/env python

"""HDA history."""

import logging
import os
import re
import subprocess
import time
from datetime import datetime

from PySide2.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from git import Repo

from rbl_pipe_hdamanager import utilities

from rbl_pipe_houdini.utils import nodes


logger = logging.getLogger(__name__)


class HDAHistory(object):
    """HDA Release History."""

    __config = utilities.get_config()
    hda_repo = __config.get("hda_repo")
    history_ui = None

    def __init__(
        self,
        node,
        manager,
    ):
        """
        Initialise the HDAHistory for the given node and manager.

        Args:
            node(hou.Node): The node we want to check the history for.
            manager(HDAManager): The HDAManager instance.
        """
        logger.info("Initialising HDA Release History")
        self.node = node
        self.manager = manager
        self.package_history = []
        self.history = []

    def history_dir(self):
        """
        Get the path to the HDA history directory.

        Returns:
            (str): The path to the history directory.
        """
        return os.path.join(self.manager.edit_dir, ".history")

    def package_dir(self):
        """Get the HDA history package.

        The path within the HDA history directory to the correct hda package given the
        HDA to be released.

        Returns:
            package_dir(str): The package directory.
        """
        repo = self.repo()
        package_dir = os.path.join(self.history_dir(), repo.package_name)
        return package_dir

    def hda_dir(self):
        """Get the HDA history directory.

        The path within the HDA history directory to the correct HDA / HDA package
        given the hda to be released.

        Returns:
            hda_dir(str): The HDA directory.
        """
        definition = nodes.definition_from_node(self.node.path())
        hda_name = utilities.expanded_hda_name(definition)
        hda_dir = os.path.join(self.package_dir(), "hda", hda_name)
        return hda_dir

    def section_path(self, section):
        """
        Get the path to the given section file within the HDA history.

        Args:
            section(str): The section within the HDA - ie. PythonModule.

        Returns:
            section_path(str): The path to the expanded section on disk.

        Raises:
            RuntimeError: Invalid section found.
        """
        hda_dir = self.hda_dir()
        if os.path.exists(hda_dir):
            definition_dirs = [
                definition_dir
                for definition_dir in os.listdir(hda_dir)
                if os.path.isdir(os.path.join(hda_dir, definition_dir))
            ]
            if len(definition_dirs) != 1:
                raise RuntimeError(
                    "Invalid number of subdirs found within HDA definition."
                )

            section_path = os.path.join(
                hda_dir,
                definition_dirs[0],
                section,
            )
            return section_path
        else:
            raise RuntimeError("HDA definition directory not found.")

    def repo(self):
        """Get the HDA repo given the HDA to be released.

        Returns:
            repo(HDARepo): The instance of repo for the current node type name.
        """
        namespace = utilities.node_type_namespace(self.node.type().name())
        repo = self.manager.repo_from_namespace(namespace)
        return repo

    def release_history(self):
        """Show release history.

        Raises:
            RuntimeError: Valid repository couldn't be found.
        """
        # Clone the repo ready to check the history
        if os.path.isdir(self.history_dir()):
            cloned_repo = Repo(self.history_dir())
        else:
            repo = Repo(self.hda_repo)
            cloned_repo = repo.clone(self.history_dir())

        # Pull the latest master
        cloned_repo.git.checkout("master")
        cloned_repo.git.pull()

        # Checkout the relevant commit
        repo = self.repo()
        if not repo:
            raise RuntimeError(
                "No valid repository found for {name}".format(
                    name=self.node.type().name(),
                )
            )
        cloned_repo.git.checkout(repo.commit_hash)

        # Generate the history for this HDA from git
        self.update_package_history()
        self.update_hda_history()
        self.complete_node_versions()

        HDAHistory.history_ui = HDAHistoryUI(self.history, self.node.type().name())
        HDAHistory.history_ui.show()

    def update_package_history(self):
        """Read the git history for the package.py."""
        package_dir = self.package_dir()

        # Change into the git repo so that it is possible to run git log etc.
        os.chdir(package_dir)

        # regex used to process git history
        split_regex = re.compile("commit (.{40})")
        tag_regex = re.compile("(tag: .*),")
        date_regex = re.compile("Date:(.*)")

        # Run git log on the package.py to get details of any updates
        package_path = os.path.join(package_dir, "package.py")
        log = subprocess.check_output(
            "git log --decorate=True -- {path}".format(
                path=package_path,
            ),
            shell=True,
        ).decode("utf-8")

        i = 0
        for log_split in split_regex.split(log):
            if not log_split:
                continue
            record = {}

            # Skip the commit hashes but process all of the other entries
            if i % 2 == 1:
                date = None

                # look for any tags in the log
                match_tags = tag_regex.search(log_split)

                if match_tags:
                    # process tags and add to dictionary
                    tags = []
                    for match in match_tags.group(0).split(","):
                        tag = match.strip()
                        if tag.startswith("tag: "):
                            tags.append(tag[5:])
                    record["tags"] = tags

                    # look for a date in the log
                    match_date = date_regex.search(log_split)
                    if match_date:
                        # convert date to timestamp and add to dict
                        date = match_date.group(1).strip()
                        record["timestamp"] = time.mktime(
                            datetime.strptime(
                                date[:-6],
                                "%a %b %d %H:%M:%S %Y",
                            ).timetuple()
                        )

                    # Keep track of each entry from the log
                    self.package_history.append(record)
            i += 1

    def update_hda_history(self):
        """Read the git history for the HDA."""
        hda_dir = self.hda_dir()

        # Change into the git repo so that it is possible to run git log etc.
        os.chdir(hda_dir)

        repo = self.repo()

        # regex used to process git history
        split_regex = re.compile("commit (.{40})")
        hda_ver_regex = re.compile("\+Operator:(.*)")
        author_regex = re.compile("Author:(.*)<")
        date_regex = re.compile("Date:(.*)")

        # Run git log on the INDEX__SECTION within the hda as we know this will
        # be written on each publish
        index_path = os.path.join(hda_dir, "INDEX__SECTION")
        log = subprocess.check_output(
            "git log --decorate=True -- {path}".format(
                path=hda_dir,
            ),
            shell=True,
        ).decode("utf-8")

        i = 0
        ver = None
        commit = None
        for log_split in split_regex.split(log):
            if not log_split:
                continue

            record = {}
            # Process the commit hash
            if i % 2 == 0:
                # diff the index file in order to extract the node version
                diff = subprocess.check_output(
                    "git diff {commit}~ {commit} -- {path}".format(
                        commit=log_split,
                        path=index_path,
                    ),
                    shell=True,
                ).decode("utf-8")
                # keep track of the commit hash so we can add it to our history
                # data later
                commit = log_split

                for line in diff.split("\n"):
                    match_ver = hda_ver_regex.search(line)
                    if match_ver:
                        ver = match_ver.group(1).strip()

            # Process the rest of the log
            else:
                author = None
                date = None
                comment = []

                # Try and extract the author, data and comment
                for line in log_split.split("\n"):
                    match_author = author_regex.search(line)
                    match_date = date_regex.search(line)
                    if match_author:
                        author = match_author.group(1).strip()
                    elif match_date:
                        date = match_date.group(1).strip()
                    else:
                        if line:
                            comment.append(line)

                # Check if we have enough data to create a record for this hda
                if author and date:
                    # Add the author, date, comment and the commit hash
                    record["author"] = author
                    record["date"] = date
                    record["comment"] = "".join(comment).strip()
                    record["commit"] = commit

                    # Calculate and add the timestamp
                    timestamp = time.mktime(
                        datetime.strptime(date[:-6], "%a %b %d %H:%M:%S %Y").timetuple()
                    )
                    record["timestamp"] = timestamp

                    # Diff the PythonModule and add to dict
                    python_diff = subprocess.check_output(
                        "git diff {commit}~ {commit} -- {path}".format(
                            commit=commit, path=self.section_path("PythonModule")
                        ),
                        shell=True,
                    ).decode("utf-8")
                    record["python_diff"] = python_diff

                    # Add the package version from the package_history
                    package_releases = [
                        pkg
                        for pkg in sorted(
                            self.package_history, key=lambda k: k["timestamp"]
                        )
                        if pkg.get("timestamp") > timestamp
                    ]
                    if package_releases:
                        tags = package_releases[0].get("tags")
                        for tag in tags:
                            if tag.startswith(repo.package_name):
                                record["package_version"] = tag

                    # Add the nodeTypeName
                    if ver:
                        record["node_version"] = ver
                        ver = None

                self.history.append(record)
            i += 1

    def complete_node_versions(self):
        """Add missing node versions.

        Currently the HDA history data will only have the nodeTypeName for
        updates where it changed. This method fills in the gaps.
        """
        version = None
        for pkg in sorted(self.history, key=lambda k: k["timestamp"]):
            current_version = pkg.get("node_version")

            # If a version exists for this record, keep track of it
            if current_version:
                version = current_version
            elif version:
                pkg["node_version"] = version
            else:
                logger.warning("No node version data found.")


class HDAHistoryUI(QWidget):
    """HDA Release History UI."""

    def __init__(self, history, node_type_name):
        """
        Create an instance of the HDA History UI.

        Args:
            history(list): A list of dictionaries containing information about a node
                types history.
            node_type_name(str): The node type name for the definition being displayed.
        """
        super(HDAHistoryUI, self).__init__()

        self.setLayout(QVBoxLayout())

        self.history = history
        self.node_type_name = node_type_name

        self.author_field = None
        self.date_field = None
        self.timestamp_field = None
        self.comment_field = None
        self.version_field = None
        self.package_field = None
        self.commit_field = None
        self.python_field = None

        self.__setup_ui()

    def __setup_ui(self):
        """Create the UI."""
        self.setWindowTitle(
            "HDA History: {name}".format(
                name=self.node_type_name,
            )
        )
        columns = [
            "author",
            "date",
            "comment",
            "",
        ]

        row_count = len(self.history)
        column_count = len(columns)

        main_layout = QHBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(column_count)
        self.table.setRowCount(row_count)

        self.table.setHorizontalHeaderLabels(columns)

        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 600)
        self.table.setColumnWidth(3, 100)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

        for row in range(row_count):  # add items from array to QTableWidget
            for column in range(column_count):
                column_text = columns[column]
                if column_text == "":
                    self.details = QPushButton("Details")
                    self.details.clicked.connect(self.handle_details_clicked)
                    self.table.setCellWidget(row, column, self.details)
                else:
                    item = self.history[row].get(column_text)
                    self.table.setItem(row, column, QTableWidgetItem(item))

        main_layout.addWidget(self.table)

        details_layout = QVBoxLayout()

        # Author
        author_layout = QHBoxLayout()
        author_label = QLabel("Author")
        author_label.setFixedWidth(100)
        self.author_field = QLineEdit()
        self.author_field.setReadOnly(True)
        self.author_field.setFixedWidth(600)
        author_layout.addWidget(author_label)
        author_layout.addWidget(self.author_field)
        details_layout.addLayout(author_layout)

        # Date
        date_layout = QHBoxLayout()
        date_label = QLabel("Date")
        date_label.setFixedWidth(100)
        self.date_field = QLineEdit()
        self.date_field.setReadOnly(True)
        self.date_field.setFixedWidth(600)
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_field)
        details_layout.addLayout(date_layout)

        # Timestamp
        timestamp_layout = QHBoxLayout()
        timestamp_label = QLabel("Timestamp")
        timestamp_label.setFixedWidth(100)
        self.timestamp_field = QLineEdit()
        self.timestamp_field.setReadOnly(True)
        self.timestamp_field.setFixedWidth(600)
        timestamp_layout.addWidget(timestamp_label)
        timestamp_layout.addWidget(self.timestamp_field)
        details_layout.addLayout(timestamp_layout)

        # Comment
        comment_layout = QHBoxLayout()
        comment_label = QLabel("Comment")
        comment_label.setFixedWidth(100)
        self.comment_field = QLineEdit()
        self.comment_field.setReadOnly(True)
        self.comment_field.setFixedWidth(600)
        comment_layout.addWidget(comment_label)
        comment_layout.addWidget(self.comment_field)
        details_layout.addLayout(comment_layout)

        # NodeTypeName
        version_layout = QHBoxLayout()
        version_label = QLabel("Version")
        version_label.setFixedWidth(100)
        self.version_field = QLineEdit()
        self.version_field.setReadOnly(True)
        self.version_field.setFixedWidth(600)
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_field)
        details_layout.addLayout(version_layout)

        # Package version
        package_layout = QHBoxLayout()
        package_label = QLabel("Package")
        package_label.setFixedWidth(100)
        self.package_field = QLineEdit()
        self.package_field.setReadOnly(True)
        self.package_field.setFixedWidth(600)
        package_layout.addWidget(package_label)
        package_layout.addWidget(self.package_field)
        details_layout.addLayout(package_layout)

        # Commit
        commit_layout = QHBoxLayout()
        commit_label = QLabel("Commit")
        commit_label.setFixedWidth(100)
        self.commit_field = QLineEdit()
        self.commit_field.setReadOnly(True)
        self.commit_field.setFixedWidth(600)
        commit_layout.addWidget(commit_label)
        commit_layout.addWidget(self.commit_field)
        details_layout.addLayout(commit_layout)

        # PythonDiff
        python_layout = QHBoxLayout()
        python_label = QLabel("Python Diff")
        python_label.setFixedWidth(100)
        self.python_field = QPlainTextEdit()
        self.python_field.setReadOnly(True)
        self.python_field.setFixedWidth(600)
        python_layout.addWidget(python_label)
        python_layout.addWidget(self.python_field)
        details_layout.addLayout(python_layout)

        main_layout.addLayout(details_layout)

        self.layout().addLayout(main_layout)

        self.resize(1920, 800)

    def handle_details_clicked(self):
        """Handle when the details button in the UI is clicked."""
        button = QApplication.focusWidget()
        index = self.table.indexAt(button.pos())
        if index.isValid():
            self.update_details(index.row())

    def update_details(self, index):
        """
        Update the details side panel based on which index is selected.

        Args:
            index(int): The index of the row that was clicked.
        """
        self.author_field.setText(str(self.history[index].get("author")))
        self.date_field.setText(str(self.history[index].get("date")))
        self.timestamp_field.setText(str(self.history[index].get("timestamp")))
        self.comment_field.setText(str(self.history[index].get("comment")))
        self.version_field.setText(str(self.history[index].get("node_version")))
        self.package_field.setText(str(self.history[index].get("package_version")))
        self.commit_field.setText(str(self.history[index].get("commit")))
        self.python_field.setPlainText(str(self.history[index].get("python_diff")))
