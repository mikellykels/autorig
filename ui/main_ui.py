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

        self.add_root_button = QtWidgets.QPushButton("Add Root Joint")
        self.add_root_button.setEnabled(False)
        self.add_root_button.setStyleSheet("background-color: #FFA500; color: white; font-weight: bold;")

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
        """Add a root joint and create proper joint hierarchy while organizing the rig."""
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
            # Create rig_systems group if it doesn't exist
            rig_systems_grp = f"{self.manager.character_name}_rig_systems"
            if not cmds.objExists(rig_systems_grp):
                rig_systems_grp = cmds.group(empty=True, name=rig_systems_grp)
                cmds.parent(rig_systems_grp, self.manager.rig_grp)
                print(f"Created rig systems group: {rig_systems_grp}")

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

            # Find the COG joint
            cog_joint = None
            for module in self.manager.modules.values():
                if isinstance(module, SpineModule) and "cog" in module.joints:
                    cog_joint = module.joints["cog"]
                    break

            if not cog_joint or not cmds.objExists(cog_joint):
                QtWidgets.QMessageBox.warning(self, "Warning", "COG joint not found. Cannot complete hierarchy setup.")
                return

            # STEP 1: COLLECT AND STORE POSITIONS OF IMPORTANT NODES
            print("\n--- STEP 1: Storing positions before reorganization ---")
            ik_data = {}

            for module in self.manager.modules.values():
                if not isinstance(module, LimbModule):
                    continue

                if "ik_handle" not in module.controls or not cmds.objExists(module.controls["ik_handle"]):
                    continue

                # Get key components
                ik_handle = module.controls["ik_handle"]
                pole_ctrl = module.controls.get("pole") if "pole" in module.controls else None

                # Store IK handle data
                module_data = {
                    "ik_handle": ik_handle,
                    "pole_ctrl": pole_ctrl,
                    "pole_ctrl_pos": cmds.xform(pole_ctrl, q=True, t=True, ws=True) if pole_ctrl else None
                }

                # Store current pole vector X,Y,Z values
                for axis in ["X", "Y", "Z"]:
                    attr = f"poleVector{axis}"
                    if cmds.attributeQuery(attr, node=ik_handle, exists=True):
                        try:
                            value = cmds.getAttr(f"{ik_handle}.{attr}")
                            module_data[f"poleVector{axis}"] = value
                            print(f"Stored {ik_handle}.{attr} = {value}")
                        except:
                            pass

                # For arm modules, also store clavicle and IK handle group
                if module.limb_type == "arm":
                    if "clavicle" in module.joints and cmds.objExists(module.joints["clavicle"]):
                        module_data["clavicle"] = module.joints["clavicle"]

                    # Try to find the arm IK handle group
                    ik_handle_grp = f"{module.module_id}_arm_ikh_grp"
                    if cmds.objExists(ik_handle_grp):
                        module_data["ik_handle_grp"] = ik_handle_grp

                # Store data for this module
                ik_data[module.module_id] = module_data

            # STEP 2: REORGANIZE JOINT HIERARCHY
            print("\n--- STEP 2: Moving IK/FK systems to rig_systems group ---")
            for module in self.manager.modules.values():
                # Move IK and FK joint chains to the systems group
                for prefix in ["ik_", "fk_"]:
                    for joint_name in module.joints.keys():
                        if joint_name.startswith(prefix):
                            joint = module.joints[joint_name]
                            if cmds.objExists(joint):
                                try:
                                    # Get current parent
                                    current_parent = cmds.listRelatives(joint, parent=True) or []

                                    # Only process root joints of each IK/FK chain
                                    if current_parent and current_parent[0] != rig_systems_grp:
                                        if "shoulder" in joint_name or "hip" in joint_name or "clavicle" in joint_name:
                                            print(f"Moving {joint} to {rig_systems_grp}")
                                            cmds.parent(joint, rig_systems_grp)
                                except Exception as e:
                                    print(f"Error reparenting {joint}: {str(e)}")

            # STEP 3: SETUP MAIN BINDING SKELETON
            print("\n--- STEP 3: Setting up main skeleton hierarchy ---")
            # Reparent COG joint to root
            cmds.parent(cog_joint, root_joint)
            print(f"Parented {cog_joint} to {root_joint}")

            # Find the pelvis joint in the spine module
            pelvis_joint = None
            spine_module = None
            for module in self.manager.modules.values():
                if isinstance(module, SpineModule):
                    spine_module = module
                    if "pelvis" in module.joints:
                        pelvis_joint = module.joints["pelvis"]
                        break

            # Connect hips to pelvis (binding joint chain only)
            if pelvis_joint and cmds.objExists(pelvis_joint):
                # Find all leg modules
                leg_modules = [m for m in self.manager.modules.values() if
                               isinstance(m, LimbModule) and m.limb_type == "leg"]

                # Reparent hip joints to pelvis (only main binding joints)
                for leg_module in leg_modules:
                    if "hip" in leg_module.joints and cmds.objExists(leg_module.joints["hip"]):
                        hip_joint = leg_module.joints["hip"]
                        cmds.parent(hip_joint, pelvis_joint)
                        print(f"Reparented {hip_joint} to {pelvis_joint}")

            # Connect arms to chest (binding joint chain only)
            if spine_module and "chest" in spine_module.joints:
                chest_joint = spine_module.joints["chest"]
                arm_modules = [m for m in self.manager.modules.values() if
                               isinstance(m, LimbModule) and m.limb_type == "arm"]

                # Reparent clavicle joints to chest (only main binding joints)
                for arm_module in arm_modules:
                    if "clavicle" in arm_module.joints and cmds.objExists(arm_module.joints["clavicle"]):
                        clavicle_joint = arm_module.joints["clavicle"]
                        cmds.parent(clavicle_joint, chest_joint)
                        print(f"Reparented {clavicle_joint} to {chest_joint}")

            # STEP 4: CLEANUP EMPTY GROUPS
            print("\n--- STEP 4: Cleaning up empty groups ---")
            # Find and delete empty module groups in joints_grp
            character_name = self.manager.character_name

            # Get all direct children of joints_grp that aren't the root joint
            try:
                joint_groups = cmds.listRelatives(joints_grp, children=True, type="transform") or []
                for grp in joint_groups:
                    # Skip the root joint
                    if grp == root_joint_name:
                        continue

                    # Skip if not a module group
                    if not (grp.startswith('l_') or grp.startswith('r_') or grp.startswith('c_')):
                        continue

                    # Check if it has children
                    children = cmds.listRelatives(grp, children=True) or []
                    if not children:
                        try:
                            print(f"Deleting empty joint group: {grp}")
                            cmds.delete(grp)
                        except Exception as e:
                            print(f"Error deleting {grp}: {str(e)}")
            except Exception as e:
                print(f"Error cleaning up joint groups: {str(e)}")

            # STEP 5: CONNECT CLAVICLES TO IK SYSTEMS FOR ARMS
            print("\n--- STEP 5: Connecting clavicles to IK systems ---")

            for module_id, data in ik_data.items():
                if "clavicle" in data and "ik_handle_grp" in data:
                    clavicle = data["clavicle"]
                    ik_handle_grp = data["ik_handle_grp"]

                    print(f"Connecting arm IK handle group {ik_handle_grp} to clavicle {clavicle}")
                    cmds.pointConstraint(clavicle, ik_handle_grp, maintainOffset=True)

            # STEP 6: FIX POLE VECTORS USING STORED VALUES
            print("\n--- STEP 6: Fixing pole vectors using stored values ---")

            for module_id, data in ik_data.items():
                ik_handle = data.get("ik_handle")
                pole_ctrl = data.get("pole_ctrl")

                if not ik_handle or not pole_ctrl or not cmds.objExists(ik_handle) or not cmds.objExists(pole_ctrl):
                    continue

                print(f"Fixing pole vector for {module_id}")

                # First remove any existing constraints
                constraints = cmds.listConnections(ik_handle, type="poleVectorConstraint") or []
                for constraint in constraints:
                    try:
                        print(f"  Removing constraint: {constraint}")
                        cmds.delete(constraint)
                    except Exception as e:
                        print(f"  Warning: Could not delete constraint {constraint}: {str(e)}")

                # Manually set the initial poleVector values to prevent popping
                for axis in ["X", "Y", "Z"]:
                    if f"poleVector{axis}" in data:
                        try:
                            cmds.setAttr(f"{ik_handle}.poleVector{axis}", 0)
                        except Exception as e:
                            print(f"  Warning: Could not zero poleVector{axis}: {str(e)}")

                # Create the pole vector constraint
                try:
                    print(f"  Creating pole vector constraint: {pole_ctrl} -> {ik_handle}")
                    cmds.poleVectorConstraint(pole_ctrl, ik_handle)
                except Exception as e:
                    print(f"  Error creating pole vector constraint: {str(e)}")

                # Important: Verify constraint is correct
                # Check if we have any poleVector values not equal to zero
                has_nonzero = False
                for axis in ["X", "Y", "Z"]:
                    try:
                        value = cmds.getAttr(f"{ik_handle}.poleVector{axis}")
                        print(f"  Final poleVector{axis} = {value}")
                        if abs(value) > 0.0001:
                            has_nonzero = True
                    except:
                        pass

                # If we still have non-zero values, we need to try a different approach
                if has_nonzero:
                    print(f"  IMPORTANT: Still have non-zero pole vector values. Using manual zeroing approach.")

                    # Remove constraint again
                    constraints = cmds.listConnections(ik_handle, type="poleVectorConstraint") or []
                    for constraint in constraints:
                        try:
                            cmds.delete(constraint)
                        except:
                            pass

                    # Force pole vector values to zero regardless of connections
                    for axis in ["X", "Y", "Z"]:
                        try:
                            # Break any connections first
                            connections = cmds.listConnections(f"{ik_handle}.poleVector{axis}", source=True,
                                                               plugs=True) or []
                            for conn in connections:
                                try:
                                    cmds.disconnectAttr(conn, f"{ik_handle}.poleVector{axis}")
                                except:
                                    pass

                            # Set to 0
                            cmds.setAttr(f"{ik_handle}.poleVector{axis}", 0)
                            print(f"  Forced poleVector{axis} to 0")
                        except:
                            pass

                    # Now move the pole control to be directly in-line with the three main joints
                    # to avoid stretching or collapsing
                    if module_id.endswith("arm"):
                        # Get positions of shoulder, elbow, wrist
                        shoulder = module.joints.get("ik_shoulder")
                        elbow = module.joints.get("ik_elbow")
                        wrist = module.joints.get("ik_wrist")

                        if shoulder and elbow and wrist and cmds.objExists(shoulder) and cmds.objExists(
                                elbow) and cmds.objExists(wrist):
                            shoulder_pos = cmds.xform(shoulder, q=True, t=True, ws=True)
                            elbow_pos = cmds.xform(elbow, q=True, t=True, ws=True)
                            wrist_pos = cmds.xform(wrist, q=True, t=True, ws=True)

                            # Calculate the vector from elbow to pole
                            # We'll keep the same distance but adjust direction to be perpendicular to arm
                            orig_pole_pos = cmds.xform(pole_ctrl, q=True, t=True, ws=True)

                            # Move pole position back on Z (perpendicular to arm plane) by 50 units
                            cmds.setAttr(f"{pole_ctrl}.translateZ", -50)

                            print(f"  Positioned pole control behind elbow")

                    # Now create the pole vector constraint again
                    try:
                        cmds.poleVectorConstraint(pole_ctrl, ik_handle)
                        print(f"  Created final pole vector constraint")
                    except Exception as e:
                        print(f"  Error creating final pole vector constraint: {str(e)}")

            # STEP 7: ORGANIZE CLUSTERS
            print("\n--- STEP 7: Organizing clusters ---")
            try:
                # Find all cluster handles
                all_clusters = cmds.ls("*Handle", type="transform") or []

                # Filter to only include actual cluster handles
                rig_clusters = []
                for cluster in all_clusters:
                    # Verify it's a cluster handle
                    if cmds.objExists(cluster) and cmds.listRelatives(cluster, shapes=True, type="clusterHandle"):
                        rig_clusters.append(cluster)

                if rig_clusters:
                    # Create a new group directly under the rig group
                    clustersgrp = cmds.group(empty=True, name=f"{character_name}_clusters_grp")
                    cmds.parent(clustersgrp, self.manager.rig_grp)

                    # Add all clusters using select and parent
                    cmds.select(clear=True)

                    for cluster in rig_clusters:
                        try:
                            cmds.parent(cluster, clustersgrp)
                            print(f"  Parented cluster {cluster} to clusters group")
                        except Exception as e:
                            print(f"  Warning: Could not parent {cluster}: {str(e)}")

                    cmds.setAttr(f"{clustersgrp}.visibility", 0)
                    print(f"Organized {len(rig_clusters)} clusters")
            except Exception as e:
                print(f"Error organizing clusters: {str(e)}")

            QtWidgets.QMessageBox.information(self, "Success", "Root joint created and hierarchy organized.")

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