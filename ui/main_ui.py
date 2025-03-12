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
from autorig.modules.neck import NeckModule
from autorig.modules.head import HeadModule


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
        self.module_type_combo.addItems(["Spine", "Arm", "Leg", "Neck", "Head"])

        self.module_side_label = QtWidgets.QLabel("Side:")
        self.module_side_combo = QtWidgets.QComboBox()
        self.module_side_combo.addItems(["Center", "Left", "Right"])

        self.module_name_label = QtWidgets.QLabel("Name:")
        self.module_name_field = QtWidgets.QLineEdit()

        self.add_module_button = QtWidgets.QPushButton("Add Module")
        self.add_module_button.setEnabled(False)  # Disabled until rig is initialized

        self.mirror_modules_button = QtWidgets.QPushButton("Mirror Modules")
        self.mirror_modules_button.setEnabled(False)  # Disabled until rig is initialized
        self.mirror_modules_button.setStyleSheet("background-color: #E6A8D7; font-weight: bold;")

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

        # Neck settings
        self.neck_settings_widget = QtWidgets.QWidget()
        self.neck_joints_label = QtWidgets.QLabel("Number of Neck Joints:")
        self.neck_joints_spinner = QtWidgets.QSpinBox()
        self.neck_joints_spinner.setRange(1, 5)
        self.neck_joints_spinner.setValue(3)

        neck_settings_layout = QtWidgets.QHBoxLayout()
        neck_settings_layout.addWidget(self.neck_joints_label)
        neck_settings_layout.addWidget(self.neck_joints_spinner)
        self.neck_settings_widget.setLayout(neck_settings_layout)

        # Head settings (empty for now)
        self.head_settings_widget = QtWidgets.QWidget()
        self.head_settings_label = QtWidgets.QLabel("No settings needed for head module")

        head_settings_layout = QtWidgets.QHBoxLayout()
        head_settings_layout.addWidget(self.head_settings_label)
        self.head_settings_widget.setLayout(head_settings_layout)

        # Stacked widget to switch between module settings
        self.settings_stack = QtWidgets.QStackedWidget()
        self.settings_stack.addWidget(self.spine_settings_widget)  # 0 - Spine
        self.settings_stack.addWidget(self.limb_settings_widget)  # 1 - Limb (Arm/Leg)
        self.settings_stack.addWidget(self.neck_settings_widget)  # 2 - Neck
        self.settings_stack.addWidget(self.head_settings_widget)  # 3 - Head

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

        self.add_root_button = QtWidgets.QPushButton("Add Root Joint")
        self.add_root_button.setEnabled(False)
        self.add_root_button.setStyleSheet("background-color: #FFA500; color: white; font-weight: bold;")

        # Add Cleanup button in the build controls section
        self.cleanup_button = QtWidgets.QPushButton("Cleanup Scene")
        self.cleanup_button.setStyleSheet("background-color: #FFC300; color: black; font-weight: bold;")
        self.cleanup_button.setEnabled(False)  # Initially disabled until rig is initialized

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
        module_list_layout.addWidget(self.mirror_modules_button)
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

        build_layout.addWidget(self.add_root_button)
        # Add cleanup button to the build layout
        build_layout.addWidget(self.cleanup_button)

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
        self.mirror_modules_button.clicked.connect(self.mirror_modules)

        # Set default module name
        self.update_module_name()
        self.module_type_combo.currentIndexChanged.connect(self.update_module_name)
        self.module_side_combo.currentIndexChanged.connect(self.update_module_name)

        self.add_root_button.clicked.connect(self.add_root_joint)

        # Connect cleanup button
        self.cleanup_button.clicked.connect(self.cleanup_scene)
        # Enable cleanup button when rig is initialized
        self.init_button.clicked.connect(lambda: self.cleanup_button.setEnabled(True))

    def update_settings_stack(self, index):
        """Update the settings stack widget based on the selected module type."""
        if index == 0:  # Spine
            self.settings_stack.setCurrentIndex(0)
        elif index in [1, 2]:  # Arm or Leg
            self.settings_stack.setCurrentIndex(1)
            # Update limb type combo box based on selection
            self.limb_type_combo.setCurrentIndex(0 if index == 1 else 1)  # Arm or Leg
        elif index == 3:  # Neck
            self.settings_stack.setCurrentIndex(2)
        elif index == 4:  # Head
            self.settings_stack.setCurrentIndex(3)

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
        self.mirror_modules_button.setEnabled(True)
        self.add_root_button.setEnabled(True)

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
        elif module_type == "Neck":
            num_joints = self.neck_joints_spinner.value()
            module = NeckModule(side, module_name, num_joints)
        elif module_type == "Head":
            module = HeadModule(side, module_name)

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

    def mirror_modules(self):
        """Mirror left side modules to right side."""
        if not self.manager:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please initialize the rig first.")
            return

        # Verify we have modules to mirror
        if not self.manager.modules:
            QtWidgets.QMessageBox.warning(self, "Warning", "No modules added yet.")
            return

        # Check if there are any left side modules to mirror
        left_modules = [m for m in self.manager.modules.values() if m.side == "l"]
        if not left_modules:
            QtWidgets.QMessageBox.warning(self, "Warning", "No left side modules found to mirror.")
            return

        # Confirm with user
        result = QtWidgets.QMessageBox.question(
            self,
            "Mirror Modules",
            "This will mirror all left side modules to the right side. Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if result == QtWidgets.QMessageBox.Yes:
            # Execute mirroring
            mirrored_count = self.manager.mirror_modules()

            # Update the module list in the UI
            self.update_module_list()

            QtWidgets.QMessageBox.information(
                self,
                "Success",
                f"Mirrored {mirrored_count} modules to the right side."
            )

    def update_module_list(self):
        """Update the module list in the UI."""
        # Clear the existing list
        self.module_list.clear()

        # Add all modules from the manager
        for module_id, module in self.manager.modules.items():
            module_type = module.module_type.capitalize()
            list_item = QtWidgets.QListWidgetItem(f"{module.side}_{module.module_name} ({module_type})")
            self.module_list.addItem(list_item)

    def add_root_joint(self):
        """Add a root joint and create proper joint hierarchy, connecting controls appropriately."""
        if not self.manager:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please initialize the rig first.")
            return

        # Confirm with user
        result = QtWidgets.QMessageBox.question(
            self, "Add Root Joint",
            "This will create a root joint and modify the hierarchy. Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if result == QtWidgets.QMessageBox.Yes:
            # Important: Reference to the joints group
            joints_grp = self.manager.joints_grp

            # Check if we already have a root joint
            root_joint_name = f"{self.manager.character_name}_root_jnt"
            if cmds.objExists(root_joint_name):
                cmds.delete(root_joint_name)

            # Create the root joint directly under the joints group
            cmds.select(clear=True)
            cmds.select(joints_grp)  # Select the joints group first
            root_joint = cmds.joint(name=root_joint_name, position=(0, 0, 0))
            print(f"Created {root_joint} under {joints_grp}")

            # Create a rig systems group for IK/FK chains
            systems_grp_name = f"{self.manager.character_name}_rig_systems"
            if cmds.objExists(systems_grp_name):
                cmds.delete(systems_grp_name)

            systems_grp = cmds.group(empty=True, name=systems_grp_name)
            cmds.parent(systems_grp, self.manager.rig_grp)
            print(f"Created rig systems group: {systems_grp}")

            # Create a visualizations group for curve visualization elements
            vis_grp_name = f"{self.manager.character_name}_visualizations"
            if cmds.objExists(vis_grp_name):
                cmds.delete(vis_grp_name)

            vis_grp = cmds.group(empty=True, name=vis_grp_name)
            cmds.parent(vis_grp, systems_grp)
            print(f"Created visualizations group: {vis_grp}")

            # Find all pole vector visualization curves and parent them to the visualizations group
            for module in self.manager.modules.values():
                if isinstance(module, LimbModule) and hasattr(module, 'utility_nodes'):
                    if 'pole_viz_curve' in module.utility_nodes:
                        curve = module.utility_nodes['pole_viz_curve']
                        if cmds.objExists(curve):
                            cmds.parent(curve, vis_grp)
                            print(f"Moved pole vector visualization {curve} to {vis_grp}")

            # Hide the guides group
            if self.manager.guides_grp and cmds.objExists(self.manager.guides_grp):
                cmds.setAttr(f"{self.manager.guides_grp}.visibility", 0)
                print("Guide group visibility turned off")

            # Find the COG joint
            cog_joint = None
            spine_module = None
            cog_control = None
            for module in self.manager.modules.values():
                if isinstance(module, SpineModule) and "cog" in module.joints:
                    spine_module = module
                    cog_joint = module.joints["cog"]
                    if "cog" in module.controls:
                        cog_control = module.controls["cog"]
                    break

            if not cog_joint or not cmds.objExists(cog_joint):
                QtWidgets.QMessageBox.warning(self, "Warning", "COG joint not found. Cannot complete hierarchy setup.")
                return

            # STEP 1: Reparent COG to root
            print("\n--- STEP 1: Setting up main skeleton hierarchy ---")
            cmds.parent(cog_joint, root_joint)
            print(f"Parented {cog_joint} to {root_joint}")

            # STEP 2: Find the pelvis joint in the spine module
            pelvis_joint = None
            if spine_module and "pelvis" in spine_module.joints:
                pelvis_joint = spine_module.joints["pelvis"]

            # STEP 3: Connect hips to pelvis (binding joint chain and controls)
            if pelvis_joint and cmds.objExists(pelvis_joint):
                # Find all leg modules (both left and right sides)
                leg_modules = [m for m in self.manager.modules.values() if
                               isinstance(m, LimbModule) and m.limb_type == "leg"]

                print(f"Found {len(leg_modules)} leg modules to connect")

                # Reparent hip joints to pelvis (only main binding joints)
                for leg_module in leg_modules:
                    print(f"Processing leg module: {leg_module.module_id} (side: {leg_module.side})")

                    if "hip" in leg_module.joints and cmds.objExists(leg_module.joints["hip"]):
                        hip_joint = leg_module.joints["hip"]
                        cmds.parent(hip_joint, pelvis_joint)
                        print(f"Reparented {hip_joint} to {pelvis_joint}")

                    # Move IK/FK chains to systems group with constraints
                    for prefix in ["ik_", "fk_"]:
                        root_key = f"{prefix}hip"
                        if root_key in leg_module.joints and cmds.objExists(leg_module.joints[root_key]):
                            root_joint = leg_module.joints[root_key]
                            try:
                                # Create a subgroup for this chain
                                chain_grp = cmds.group(empty=True, name=f"{leg_module.module_id}_{prefix}chain_grp")
                                cmds.parent(chain_grp, systems_grp)

                                # Get current parent
                                current_parent = cmds.listRelatives(root_joint, parent=True)

                                # Create constraint to pelvis before unparenting
                                # This ensures the IK/FK chains still follow the pelvis
                                if prefix == "ik_":
                                    constraint_name = f"{root_joint}_to_pelvis_parentConstraint"
                                    if not cmds.objExists(constraint_name):
                                        cmds.parentConstraint(pelvis_joint, root_joint, maintainOffset=True,
                                                              name=constraint_name)
                                        print(f"Created parent constraint from {pelvis_joint} to {root_joint}")

                                # Unparent from current parent
                                if current_parent:
                                    cmds.parent(root_joint, world=True)

                                # Parent to the chain group
                                cmds.parent(root_joint, chain_grp)
                                print(f"Moved {root_joint} chain to systems group")

                            except Exception as e:
                                print(f"Warning: Error moving {root_joint}: {str(e)}")

                # STEP 4: Find the chest joint and set up connections for arms
                chest_joint = None
                chest_control = None
                if spine_module:
                    if "chest" in spine_module.joints:
                        chest_joint = spine_module.joints["chest"]
                    if "chest" in spine_module.controls:
                        chest_control = spine_module.controls["chest"]
                        print(f"Found chest control: {chest_control}")

                    # STEP 4A: Connect arms to chest (binding joint chain and controls)
                    if chest_joint and cmds.objExists(chest_joint) and chest_control and cmds.objExists(chest_control):
                        # Find all arm modules (both left and right sides)
                        arm_modules = [m for m in self.manager.modules.values() if
                                       isinstance(m, LimbModule) and m.limb_type == "arm"]

                        print(f"Found {len(arm_modules)} arm modules to connect")

                        # Process each arm module individually for clarity
                        for arm_module in arm_modules:
                            print(f"\n=== PROCESSING ARM MODULE: {arm_module.module_id} (side: {arm_module.side}) ===")

                            # DEBUGGING: Print all controls in the module
                            print(f"Available controls in {arm_module.module_id}:")
                            for control_name, control in arm_module.controls.items():
                                print(f"  {control_name}: {control}")

                            # IMPROVED: Check if clavicle control exists in the scene even if not in module
                            expected_clavicle_ctrl_name = f"{arm_module.module_id}_clavicle_ctrl"

                            # First check if it's in the module's controls
                            if "clavicle" not in arm_module.controls:
                                # Check if it exists in the scene anyway
                                if cmds.objExists(expected_clavicle_ctrl_name):
                                    print(f"Found existing clavicle control in scene: {expected_clavicle_ctrl_name}")
                                    # Add it to the module's controls dictionary
                                    arm_module.controls["clavicle"] = expected_clavicle_ctrl_name
                                else:
                                    print(
                                        f"Clavicle control not found in scene or module: {expected_clavicle_ctrl_name}")

                            # 1. CONNECT CLAVICLE JOINT TO CHEST JOINT
                            if "clavicle" in arm_module.joints and cmds.objExists(arm_module.joints["clavicle"]):
                                clavicle_joint = arm_module.joints["clavicle"]

                                # Parent to chest if not already
                                current_parent = cmds.listRelatives(clavicle_joint, parent=True)
                                if not current_parent or current_parent[0] != chest_joint:
                                    try:
                                        cmds.parent(clavicle_joint, chest_joint)
                                        print(
                                            f"CONNECTED: Clavicle joint {clavicle_joint} -> chest joint {chest_joint}")
                                    except Exception as e:
                                        print(f"ERROR parenting clavicle joint: {str(e)}")
                                else:
                                    print(
                                        f"Clavicle joint {clavicle_joint} already connected to chest joint {chest_joint}")

                            # 2. CONNECT CLAVICLE CONTROL TO CHEST CONTROL
                            if "clavicle" in arm_module.controls:
                                clavicle_ctrl = arm_module.controls["clavicle"]
                                clavicle_ctrl_grp = f"{clavicle_ctrl}_grp"

                                if cmds.objExists(clavicle_ctrl) and cmds.objExists(clavicle_ctrl_grp):
                                    # Parent to chest control if not already
                                    current_parent = cmds.listRelatives(clavicle_ctrl_grp, parent=True)
                                    if not current_parent or current_parent[0] != chest_control:
                                        try:
                                            cmds.parent(clavicle_ctrl_grp, chest_control)
                                            print(
                                                f"CONNECTED: Clavicle control group {clavicle_ctrl_grp} -> chest control {chest_control}")
                                        except Exception as e:
                                            print(f"ERROR parenting clavicle control: {str(e)}")
                                    else:
                                        print(
                                            f"Clavicle control group {clavicle_ctrl_grp} already parented to chest control {chest_control}")

                            # 3. CONNECT FK SHOULDER CONTROL TO CLAVICLE CONTROL - this is key for arm movement
                            if "fk_shoulder" in arm_module.controls and "clavicle" in arm_module.controls:
                                fk_shoulder_ctrl = arm_module.controls["fk_shoulder"]
                                fk_shoulder_grp = f"{fk_shoulder_ctrl}_grp"
                                clavicle_ctrl = arm_module.controls["clavicle"]

                                if cmds.objExists(fk_shoulder_grp) and cmds.objExists(clavicle_ctrl):
                                    # Check current parent
                                    current_parent = cmds.listRelatives(fk_shoulder_grp, parent=True)
                                    if not current_parent or current_parent[0] != clavicle_ctrl:
                                        try:
                                            cmds.parent(fk_shoulder_grp, clavicle_ctrl)
                                            print(
                                                f"CONNECTED: FK shoulder control group {fk_shoulder_grp} -> clavicle control {clavicle_ctrl}")
                                        except Exception as e:
                                            print(f"ERROR parenting FK shoulder control: {str(e)}")
                                    else:
                                        print(
                                            f"FK shoulder control group {fk_shoulder_grp} already parented to clavicle control {clavicle_ctrl}")

                            # 4. VERIFY AND RECREATE CLAVICLE CONSTRAINTS IF NEEDED
                            if "clavicle" in arm_module.controls and "clavicle" in arm_module.joints:
                                clavicle_ctrl = arm_module.controls["clavicle"]
                                clavicle_joint = arm_module.joints["clavicle"]

                                if cmds.objExists(clavicle_ctrl) and cmds.objExists(clavicle_joint):
                                    # Check existing constraints
                                    constraints = cmds.listConnections(clavicle_joint, source=True,
                                                                       type="parentConstraint") or []

                                    if not constraints:
                                        print(f"No parent constraint found on {clavicle_joint}, creating one...")
                                        cmds.parentConstraint(clavicle_ctrl, clavicle_joint, maintainOffset=True)
                                        print(f"Created new constraint from {clavicle_ctrl} to {clavicle_joint}")

                            # 5. MOVE IK/FK CHAINS TO SYSTEMS GROUP WITH PROPER CONSTRAINTS TO CLAVICLE
                            for prefix in ["ik_", "fk_"]:
                                root_key = f"{prefix}shoulder"
                                if root_key in arm_module.joints and cmds.objExists(arm_module.joints[root_key]):
                                    root_joint = arm_module.joints[root_key]
                                    try:
                                        # Create a subgroup for this chain
                                        chain_grp = cmds.group(empty=True,
                                                               name=f"{arm_module.module_id}_{prefix}chain_grp")
                                        cmds.parent(chain_grp, systems_grp)

                                        # Get current parent before unparenting
                                        current_parent = cmds.listRelatives(root_joint, parent=True)

                                        # CRITICAL FIX: Create constraint to clavicle BEFORE unparenting
                                        # This ensures the IK shoulder still follows the clavicle even after moving
                                        if prefix == "ik_" and "clavicle" in arm_module.joints:
                                            constraint_name = f"{root_joint}_to_clavicle_parentConstraint"
                                            if not cmds.objExists(constraint_name):
                                                cmds.parentConstraint(
                                                    arm_module.joints["clavicle"],
                                                    root_joint,
                                                    maintainOffset=True,
                                                    name=constraint_name
                                                )
                                                print(f"Created parent constraint from clavicle to {root_joint}")

                                        # Unparent from current parent
                                        if current_parent:
                                            cmds.parent(root_joint, world=True)

                                        # Parent to the chain group
                                        cmds.parent(root_joint, chain_grp)
                                        print(f"Moved {root_joint} chain to systems group")

                                        # Verify constraint is still working after reparenting
                                        constraints = cmds.listConnections(root_joint, source=True,
                                                                           type="parentConstraint") or []
                                        if prefix == "ik_" and not constraints:
                                            print(f"Warning: Constraint was lost, recreating for {root_joint}")
                                            if "clavicle" in arm_module.joints:
                                                cmds.parentConstraint(
                                                    arm_module.joints["clavicle"],
                                                    root_joint,
                                                    maintainOffset=True
                                                )
                                                print(f"Recreated parent constraint from clavicle to {root_joint}")

                                    except Exception as e:
                                        print(f"Warning: Error moving {root_joint}: {str(e)}")

                        # STEP 5: Connect neck base to chest
                        if chest_joint and chest_control:
                            neck_modules = [m for m in self.manager.modules.values() if isinstance(m, NeckModule)]

                            for neck_module in neck_modules:
                                # Check if neck_base exists
                                if "neck_base" not in neck_module.joints:
                                    print(f"Warning: Neck module has no neck_base joint")
                                    continue

                                # Get neck base joint
                                neck_base_joint = neck_module.joints["neck_base"]

                                # Verify joint is not already connected to chest
                                current_parent = cmds.listRelatives(neck_base_joint, parent=True)
                                if current_parent and current_parent[0] == chest_joint:
                                    print(f"Neck base joint {neck_base_joint} already connected to chest {chest_joint}")
                                else:
                                    # Get all of the neck's children to maintain hierarchy
                                    neck_children = cmds.listRelatives(neck_base_joint, children=True,
                                                                       type="joint") or []

                                    # Temporarily unparent children if any
                                    for child in neck_children:
                                        cmds.parent(child, world=True)

                                    # Parent neck base to chest
                                    cmds.parent(neck_base_joint, chest_joint)
                                    print(f"Reparented {neck_base_joint} to {chest_joint}")

                                    # Make sure the rotation values stay at zero
                                    cmds.setAttr(f"{neck_base_joint}.rotate", 0, 0, 0)

                                    # Reparent children back to neck_base
                                    for child in neck_children:
                                        cmds.parent(child, neck_base_joint)
                                        print(f"  Restored child {child} to {neck_base_joint}")

                                # Connect neck control to chest control
                                if "neck_base" in neck_module.controls:
                                    neck_base_ctrl = neck_module.controls["neck_base"]
                                    neck_base_grp = f"{neck_base_ctrl}_grp"

                                    if cmds.objExists(neck_base_grp):
                                        # Check if already connected
                                        current_parent = cmds.listRelatives(neck_base_grp, parent=True)
                                        if not current_parent or current_parent[0] != chest_control:
                                            try:
                                                cmds.parent(neck_base_grp, chest_control)
                                                print(
                                                    f"Connected neck base control {neck_base_ctrl} to chest control {chest_control}")
                                            except Exception as e:
                                                print(f"Error connecting neck control: {str(e)}")

                    # STEP 6: Connect head to the LAST neck joint (not first neck joint)
                    head_modules = [m for m in self.manager.modules.values() if isinstance(m, HeadModule)]
                    neck_modules = [m for m in self.manager.modules.values() if isinstance(m, NeckModule)]

                    if head_modules and neck_modules:
                        # Find a head module
                        head_module = head_modules[0]

                        # Find a neck module
                        neck_module = neck_modules[0]

                        # Get the LAST neck joint and control - IMPORTANT FIX
                        last_neck_joint = None
                        last_neck_control = None
                        last_neck_name = f"neck_{neck_module.num_joints:02d}"

                        if last_neck_name in neck_module.joints:
                            last_neck_joint = neck_module.joints[last_neck_name]
                            print(f"Found last neck joint: {last_neck_joint}")
                        else:
                            print(f"Warning: Last neck joint ({last_neck_name}) not found")
                            # Find all neck joints and use the highest number
                            neck_joints = []
                            for i in range(1, 10):  # Check up to 10 neck joints
                                key = f"neck_{i:02d}"
                                if key in neck_module.joints:
                                    neck_joints.append((i, neck_module.joints[key]))

                            if neck_joints:
                                # Use the highest numbered joint
                                neck_joints.sort(reverse=True)
                                last_neck_joint = neck_joints[0][1]
                                print(f"Using highest neck joint found: {last_neck_joint}")

                        # Find the last neck control (usually "top_neck")
                        if "top_neck" in neck_module.controls:
                            last_neck_control = neck_module.controls["top_neck"]
                            print(f"Found last neck control: {last_neck_control}")

                        # Check if head base exists and connect it to the LAST neck joint
                        if "head_base" in head_module.joints and last_neck_joint and cmds.objExists(last_neck_joint):
                            head_base_joint = head_module.joints["head_base"]
                            print(f"Processing head joint: {head_base_joint}")

                            # Save any head end joint first
                            head_end_joint = None
                            if "head_end" in head_module.joints:
                                head_end_joint = head_module.joints["head_end"]
                                # Temporarily parent to world
                                if cmds.listRelatives(head_end_joint, parent=True):
                                    cmds.parent(head_end_joint, world=True)
                                    print(f"Temporarily unparented head end joint: {head_end_joint}")

                            # Get current parent of head base
                            current_parent = cmds.listRelatives(head_base_joint, parent=True)
                            print(f"Current parent of head joint: {current_parent}")

                            # IMPORTANT FIX: Explicitly connect head to the LAST neck joint
                            if not current_parent or current_parent[0] != last_neck_joint:
                                # First unparent
                                if current_parent:
                                    cmds.parent(head_base_joint, world=True)
                                    print(f"Unparented head from {current_parent[0]}")

                                # Now parent to last neck joint
                                cmds.parent(head_base_joint, last_neck_joint)
                                print(
                                    f"FIXED: Connected head joint {head_base_joint} to LAST neck joint {last_neck_joint}")

                                # Fix head orientation
                                neck_orient = cmds.getAttr(f"{last_neck_joint}.jointOrient")[0]
                                cmds.setAttr(f"{head_base_joint}.jointOrient", neck_orient[0], neck_orient[1],
                                             neck_orient[2])
                                cmds.setAttr(f"{head_base_joint}.rotate", 0, 0, 0)  # Zero out rotation

                            # Reparent head_end back to head_base
                            if head_end_joint and cmds.objExists(head_end_joint):
                                cmds.parent(head_end_joint, head_base_joint)
                                print(f"Restored head end joint to head base")

                                # Fix orientation
                                cmds.setAttr(f"{head_end_joint}.jointOrient", 0, 0, 0)
                                cmds.setAttr(f"{head_end_joint}.rotate", 0, 0, 0)

                            # Connect head control to last neck control
                            if "head" in head_module.controls and last_neck_control:
                                head_ctrl = head_module.controls["head"]
                                head_ctrl_grp = f"{head_ctrl}_grp"

                                if cmds.objExists(head_ctrl_grp):
                                    current_parent = cmds.listRelatives(head_ctrl_grp, parent=True)
                                    if not current_parent or current_parent[0] != last_neck_control:
                                        try:
                                            cmds.parent(head_ctrl_grp, last_neck_control)
                                            print(
                                                f"Connected head control {head_ctrl} to last neck control {last_neck_control}")
                                        except Exception as e:
                                            print(f"Error connecting head control: {str(e)}")

                                    # Verify head constraint
                                    if "head_base" in head_module.joints:
                                        head_constraints = cmds.listConnections(head_module.joints["head_base"],
                                                                                source=True,
                                                                                type="parentConstraint") or []
                                        if not head_constraints:
                                            cmds.parentConstraint(head_ctrl, head_module.joints["head_base"],
                                                                  maintainOffset=True)
                                            print(f"Recreated constraint between head control and head joint")

                    # STEP 7: Fix FK shoulder controls for both arms
                    arm_modules = [m for m in self.manager.modules.values() if
                                   isinstance(m, LimbModule) and m.limb_type == "arm"]

                    for arm_module in arm_modules:
                        print(f"\n=== FIXING FK SHOULDER CONSTRAINTS FOR {arm_module.module_id} ===")

                        # Verify FK shoulder constraint
                        if "fk_shoulder" in arm_module.controls and "fk_shoulder" in arm_module.joints:
                            fk_ctrl = arm_module.controls["fk_shoulder"]
                            fk_joint = arm_module.joints["fk_shoulder"]

                            # Check if there's a constraint
                            constraints = cmds.listConnections(fk_joint, source=True, destination=False,
                                                               type="constraint") or []
                            if not constraints:
                                print(f"Adding missing constraint from {fk_ctrl} to {fk_joint}")
                                try:
                                    cmds.parentConstraint(fk_ctrl, fk_joint, maintainOffset=True)
                                    print(f"Created new constraint from {fk_ctrl} to {fk_joint}")
                                except Exception as e:
                                    print(f"Error creating constraint: {str(e)}")

                    try:
                        # STEP 8: Organize clusters
                        self.manager.organize_clusters()
                    except Exception as e:
                        print(f"Warning: Error organizing clusters: {str(e)}")

                    QtWidgets.QMessageBox.information(self, "Success", "Root joint created and hierarchy organized.")

    def cleanup_scene(self):
        """
        Perform a comprehensive scene cleanup.
        Removes empty groups, unnecessary nodes, and helps organize the Maya scene.
        """
        # Confirm with user
        result = QtWidgets.QMessageBox.question(
            self,
            "Cleanup Scene",
            "This will remove empty groups and help organize the scene. Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if result == QtWidgets.QMessageBox.Yes:
            # 1. Remove Empty Groups
            empty_groups = self._find_empty_nulls()
            delete_count = self._delete_empty_nulls(empty_groups)

            # Show results
            QtWidgets.QMessageBox.information(
                self,
                "Cleanup Complete",
                f"Cleanup Results:\n"
                f"- Removed {delete_count} empty groups\n"
            )

    def _find_empty_nulls(self):
        """
        Finds empty null transform nodes in the scene.

        Returns:
            list: Names of empty null transform nodes
        """
        # Get all transform nodes
        nulls = cmds.ls(type='transform')

        # List to store empty nulls
        empty_nulls = []

        for null in nulls:
            # Skip if node doesn't exist
            if not cmds.objExists(null):
                continue

            # Check if the node has no children and is a transform
            if not cmds.listRelatives(null, children=True) and cmds.nodeType(null) == 'transform':
                # Exclude Maya's default objects and groups
                if null.startswith("|"):
                    continue

                # Exclude specific Maya system groups
                if any(reserved in null for reserved in [
                    "persp", "top", "front", "side",
                    "defaultLayer", "LayerManager"
                ]):
                    continue

                empty_nulls.append(null)

        return empty_nulls

    def _delete_empty_nulls(self, nulls_to_delete):
        """
        Delete the list of empty null transform nodes.

        Args:
            nulls_to_delete (list): List of null node names to delete

        Returns:
            int: Number of nulls deleted
        """
        delete_count = 0
        for null in nulls_to_delete:
            try:
                if cmds.objExists(null):
                    # Final check to ensure it's still an empty transform
                    if not cmds.listRelatives(null, children=True) and cmds.nodeType(null) == 'transform':
                        cmds.delete(null)
                        delete_count += 1
                        print(f"Deleted empty null: {null}")
            except Exception as e:
                print(f"Error deleting null {null}: {str(e)}")

        return delete_count

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