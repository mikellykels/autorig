"""
Modular Auto-Rig System
UI Implementation

This module contains the UI for the modular auto-rigging system.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import sys
from PySide2 import QtWidgets, QtCore, QtGui
import maya.OpenMayaUI as omui
import shiboken2

from autorig.core.manager import ModuleManager
from autorig.core.utils import CONTROL_COLORS
from autorig.modules.spine import SpineModule
from autorig.modules.limb import LimbModule


def maya_main_window():
    """Return the Maya main window widget"""
    main_window = omui.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(int(main_window), QtWidgets.QWidget)


class ModularRigUI(QtWidgets.QDialog):
    """
    UI for the modular auto-rigging system.
    """

    def __init__(self, parent=maya_main_window()):
        super(ModularRigUI, self).__init__(parent)

        self.setWindowTitle("Modular Auto-Rig")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.manager = None
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        """Create the UI widgets."""
        # Character Settings section
        self.character_name_label = QtWidgets.QLabel("Character Name:")
        self.character_name_field = QtWidgets.QLineEdit("character")

        self.init_button = QtWidgets.QPushButton("Initialize Rig")

        # Module Management section
        self.module_type_label = QtWidgets.QLabel("Module Type:")
        self.module_type_combo = QtWidgets.QComboBox()
        self.module_type_combo.addItems(["Spine", "Arm", "Leg"])

        self.module_side_label = QtWidgets.QLabel("Side:")
        self.module_side_combo = QtWidgets.QComboBox()
        self.module_side_combo.addItems(["Center", "Left", "Right"])

        self.module_name_label = QtWidgets.QLabel("Name:")
        self.module_name_field = QtWidgets.QLineEdit()

        self.add_module_button = QtWidgets.QPushButton("Add Module")
        self.add_module_button.setEnabled(False)  # Disabled until rig is initialized

        # Module Settings section
        self.settings_label = QtWidgets.QLabel("Module Settings")
        self.settings_label.setStyleSheet("font-weight: bold; margin-top: 10px;")

        # Spine settings
        self.spine_settings_widget = QtWidgets.QWidget()
        self.spine_joints_label = QtWidgets.QLabel("Number of Joints:")
        self.spine_joints_spinner = QtWidgets.QSpinBox()
        self.spine_joints_spinner.setRange(3, 10)
        self.spine_joints_spinner.setValue(5)

        spine_settings_layout = QtWidgets.QHBoxLayout()
        spine_settings_layout.addWidget(self.spine_joints_label)
        spine_settings_layout.addWidget(self.spine_joints_spinner)
        self.spine_settings_widget.setLayout(spine_settings_layout)

        # Limb settings
        self.limb_settings_widget = QtWidgets.QWidget()
        self.limb_type_label = QtWidgets.QLabel("Limb Type:")
        self.limb_type_combo = QtWidgets.QComboBox()
        self.limb_type_combo.addItems(["Arm", "Leg"])

        limb_settings_layout = QtWidgets.QHBoxLayout()
        limb_settings_layout.addWidget(self.limb_type_label)
        limb_settings_layout.addWidget(self.limb_type_combo)
        self.limb_settings_widget.setLayout(limb_settings_layout)

        # Stacked widget to switch between module settings
        self.settings_stack = QtWidgets.QStackedWidget()
        self.settings_stack.addWidget(self.spine_settings_widget)
        self.settings_stack.addWidget(self.limb_settings_widget)

        # Module List section
        self.module_list_label = QtWidgets.QLabel("Added Modules:")
        self.module_list = QtWidgets.QListWidget()

        # Guide and Build Controls section
        self.create_guides_button = QtWidgets.QPushButton("Create All Guides")
        self.create_guides_button.setEnabled(False)

        self.save_guides_button = QtWidgets.QPushButton("Save Guide Positions")
        self.save_guides_button.setEnabled(False)

        self.load_guides_button = QtWidgets.QPushButton("Load Guide Positions")
        self.load_guides_button.setEnabled(False)

        self.build_rig_button = QtWidgets.QPushButton("BUILD RIG")
        self.build_rig_button.setEnabled(False)
        self.build_rig_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

    def create_layouts(self):
        """Create the UI layouts."""
        main_layout = QtWidgets.QVBoxLayout(self)

        # Character Settings group
        character_group = QtWidgets.QGroupBox("Character Settings")
        character_layout = QtWidgets.QHBoxLayout()
        character_layout.addWidget(self.character_name_label)
        character_layout.addWidget(self.character_name_field)
        character_layout.addWidget(self.init_button)
        character_group.setLayout(character_layout)

        # Module Creation group
        module_creation_group = QtWidgets.QGroupBox("Add Module")
        module_creation_layout = QtWidgets.QGridLayout()

        module_creation_layout.addWidget(self.module_type_label, 0, 0)
        module_creation_layout.addWidget(self.module_type_combo, 0, 1)

        module_creation_layout.addWidget(self.module_side_label, 1, 0)
        module_creation_layout.addWidget(self.module_side_combo, 1, 1)

        module_creation_layout.addWidget(self.module_name_label, 2, 0)
        module_creation_layout.addWidget(self.module_name_field, 2, 1)

        module_creation_layout.addWidget(self.settings_label, 3, 0, 1, 2)
        module_creation_layout.addWidget(self.settings_stack, 4, 0, 1, 2)

        module_creation_layout.addWidget(self.add_module_button, 5, 0, 1, 2)

        module_creation_group.setLayout(module_creation_layout)

        # Module List group
        module_list_group = QtWidgets.QGroupBox("Module List")
        module_list_layout = QtWidgets.QVBoxLayout()
        module_list_layout.addWidget(self.module_list)
        module_list_group.setLayout(module_list_layout)

        # Guide and Build Controls group
        build_group = QtWidgets.QGroupBox("Build Controls")
        build_layout = QtWidgets.QVBoxLayout()

        guide_layout = QtWidgets.QHBoxLayout()
        guide_layout.addWidget(self.create_guides_button)
        guide_layout.addWidget(self.save_guides_button)
        guide_layout.addWidget(self.load_guides_button)

        build_layout.addLayout(guide_layout)
        build_layout.addWidget(self.build_rig_button)

        build_group.setLayout(build_layout)

        # Add all groups to main layout
        main_layout.addWidget(character_group)
        main_layout.addWidget(module_creation_group)
        main_layout.addWidget(module_list_group)
        main_layout.addWidget(build_group)

    def create_connections(self):
        """Create signal/slot connections."""
        # Connect signals
        self.module_type_combo.currentIndexChanged.connect(self.update_settings_stack)
        self.init_button.clicked.connect(self.initialize_rig)
        self.add_module_button.clicked.connect(self.add_module)
        self.create_guides_button.clicked.connect(self.create_guides)
        self.save_guides_button.clicked.connect(self.save_guide_positions)
        self.load_guides_button.clicked.connect(self.load_guide_positions)
        self.build_rig_button.clicked.connect(self.build_rig)

        # Set default module name
        self.update_module_name()
        self.module_type_combo.currentIndexChanged.connect(self.update_module_name)
        self.module_side_combo.currentIndexChanged.connect(self.update_module_name)

    def update_settings_stack(self, index):
        """Update the settings stack widget based on the selected module type."""
        self.settings_stack.setCurrentIndex(0 if index == 0 else 1)  # Spine or Limb

        # Update limb type combo box visibility
        if index == 1:  # Arm
            self.limb_type_combo.setCurrentIndex(0)  # Arm
        elif index == 2:  # Leg
            self.limb_type_combo.setCurrentIndex(1)  # Leg

    def update_module_name(self):
        """Update the module name field based on the selected type and side."""
        module_type = self.module_type_combo.currentText().lower()
        side = self.module_side_combo.currentText().lower()

        if side == "center":
            side_prefix = "c"
        elif side == "left":
            side_prefix = "l"
        elif side == "right":
            side_prefix = "r"

        self.module_name_field.setText(f"{module_type}")

    def initialize_rig(self):
        """Initialize the rig manager."""
        character_name = self.character_name_field.text()
        if not character_name:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a character name.")
            return

        # Initialize the module manager
        self.manager = ModuleManager(character_name)

        # Enable module controls
        self.add_module_button.setEnabled(True)
        self.create_guides_button.setEnabled(True)
        self.save_guides_button.setEnabled(True)
        self.load_guides_button.setEnabled(True)
        self.build_rig_button.setEnabled(True)

        QtWidgets.QMessageBox.information(self, "Success", f"Initialized rig for character: {character_name}")

    def add_module(self):
        """Add a module to the rig."""
        if not self.manager:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please initialize the rig first.")
            return

        module_type = self.module_type_combo.currentText()
        side_text = self.module_side_combo.currentText()
        module_name = self.module_name_field.text()

        if not module_name:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a module name.")
            return

        # Convert side to code
        if side_text == "Center":
            side = "c"
        elif side_text == "Left":
            side = "l"
        elif side_text == "Right":
            side = "r"

        # Create the appropriate module type
        module = None
        if module_type == "Spine":
            num_joints = self.spine_joints_spinner.value()
            module = SpineModule(side, module_name, num_joints)
        elif module_type in ["Arm", "Leg"]:
            limb_type = self.limb_type_combo.currentText().lower()
            module = LimbModule(side, module_name, limb_type)

        if module:
            # Register the module
            self.manager.register_module(module)

            # Add to the module list
            list_item = QtWidgets.QListWidgetItem(f"{side}_{module_name} ({module_type})")
            self.module_list.addItem(list_item)

            QtWidgets.QMessageBox.information(self, "Success", f"Added {module_type} module: {side}_{module_name}")

    def create_guides(self):
        """Create guides for all modules."""
        if not self.manager:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please initialize the rig first.")
            return

        if not self.manager.modules:
            QtWidgets.QMessageBox.warning(self, "Warning", "No modules added yet.")
            return

        self.manager.create_all_guides()

        QtWidgets.QMessageBox.information(self, "Success",
                                          "Created guides for all modules. Please position them as needed.")

    def save_guide_positions(self):
        """Save guide positions to a file."""
        if not self.manager:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please initialize the rig first.")
            return

        if not self.manager.modules:
            QtWidgets.QMessageBox.warning(self, "Warning", "No modules added yet.")
            return

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Guide Positions", "", "JSON Files (*.json)"
        )

        if file_path:
            self.manager.save_guide_positions(file_path)
            QtWidgets.QMessageBox.information(self, "Success", f"Saved guide positions to: {file_path}")

    def load_guide_positions(self):
        """Load guide positions from a file."""
        if not self.manager:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please initialize the rig first.")
            return

        if not self.manager.modules:
            QtWidgets.QMessageBox.warning(self, "Warning", "No modules added yet.")
            return

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Guide Positions", "", "JSON Files (*.json)"
        )

        if file_path:
            self.manager.load_guide_positions(file_path)
            QtWidgets.QMessageBox.information(self, "Success", f"Loaded guide positions from: {file_path}")

    def build_rig(self):
        """Build the rig."""
        if not self.manager:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please initialize the rig first.")
            return

        if not self.manager.modules:
            QtWidgets.QMessageBox.warning(self, "Warning", "No modules added yet.")
            return

        # Confirm with user
        result = QtWidgets.QMessageBox.question(
            self,
            "Build Rig",
            "Are you sure you want to build the rig? This will create the final rig structure based on the current guide positions.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if result == QtWidgets.QMessageBox.Yes:
            self.manager.build_all_modules()
            QtWidgets.QMessageBox.information(self, "Success", "Rig built successfully!")

def show_ui():
    """Show the UI, ensuring only one instance exists."""
    # Check if window already exists and delete it
    window_name = "ModularRigUI"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    # Create and show new dialog
    dialog = ModularRigUI()
    dialog.setObjectName(window_name)
    dialog.setWindowFlags(dialog.windowFlags() | QtCore.Qt.Window)
    dialog.setWindowTitle("Modular Auto-Rig")
    dialog.show()

    return dialog

if __name__ == "__main__":
    show_ui()