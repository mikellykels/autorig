"""
Modular Rig System
Spine Module (Refactored)

This module contains the implementation of the spine rig module.
Refactored to improve joint orientations and spine control structure.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import math
from autorig.core.module_base import BaseModule
from autorig.core.utils import (create_guide, create_joint, create_control,
                                set_color_override, CONTROL_COLORS, GUIDE_BLADE_COLOR)
from autorig.core.joint_utils import (is_planar_chain, make_planar, create_oriented_joint_chain,
                                     fix_joint_orientations, fix_specific_joint_orientation)
from autorig.core.vector_utils import (vector_from_two_points, vector_length, normalize_vector,
                                     add_vectors, subtract_vectors, get_midpoint)


class SpineModule(BaseModule):
    """
    Module for creating a spine rig with improved orientation.
    """

    def __init__(self, side="c", module_name="spine", num_joints=5):
        """
        Initialize the spine module.

        Args:
            side (str): Side of the body
            module_name (str): Name of the module
            num_joints (int): Number of spine joints
        """
        super().__init__(side, module_name, "spine")
        self.num_joints = num_joints

        # Additional blade guide references for orientation
        self.blade_guides = {}

        # Store planar validation results
        self.is_planar = True
        self.planar_adjusted = False

    def create_guides(self):
        """Create the spine guides with orientation helpers."""
        self._create_module_groups()

        # Create COG guide at origin
        self.guides["cog"] = create_guide(f"{self.module_id}_cog", (0, 0, 0), self.guide_grp)

        # Create pelvis guide (renamed from hip)
        self.guides["pelvis"] = create_guide(f"{self.module_id}_pelvis", (0, 10, 0), self.guide_grp)

        # Create spine guides with proper padding
        step = 10.0 / (self.num_joints - 1) if self.num_joints > 1 else 0
        for i in range(self.num_joints):
            # Use 2-digit padding for spine numbers
            name = f"{self.module_id}_spine_{i + 1:02d}"
            pos = (0, 10 + step * i, 0)
            self.guides[f"spine_{i + 1:02d}"] = create_guide(name, pos, self.guide_grp)

        # Create chest guide
        self.guides["chest"] = create_guide(f"{self.module_id}_chest",
                                          (0, 10 + step * (self.num_joints - 1), 0),
                                          self.guide_grp)

        # Create blade guides for orientation references
        # COG/Pelvis up vector
        self.blade_guides["upv_pelvis"] = create_guide(
            f"{self.module_id}_upv_pelvis",
            (0, 10, -2),  # Positioned behind pelvis
            self.guide_grp,
            color=GUIDE_BLADE_COLOR
        )

        # Mid spine up vector
        mid_idx = max(1, self.num_joints // 2)
        mid_spine_pos = cmds.xform(self.guides[f"spine_{mid_idx:02d}"], q=True, t=True, ws=True)
        self.blade_guides["upv_mid_spine"] = create_guide(
            f"{self.module_id}_upv_mid_spine",
            (mid_spine_pos[0], mid_spine_pos[1], mid_spine_pos[2] - 2),  # Behind spine
            self.guide_grp,
            color=GUIDE_BLADE_COLOR
        )

        # Chest up vector
        chest_pos = cmds.xform(self.guides["chest"], q=True, t=True, ws=True)
        self.blade_guides["upv_chest"] = create_guide(
            f"{self.module_id}_upv_chest",
            (chest_pos[0], chest_pos[1], chest_pos[2] - 2),  # Behind chest
            self.guide_grp,
            color=GUIDE_BLADE_COLOR
        )

        # Create visual connections between guides and their blade guides
        self._create_guide_connections()

    def _create_guide_connections(self):
        """Create visual curve connections between guides and their blade guides."""
        # Define connections to create
        connections = [
            ("pelvis", "upv_pelvis"),
            (f"spine_{max(1, self.num_joints // 2):02d}", "upv_mid_spine"),
            ("chest", "upv_chest")
        ]

        # Create curve connections
        for start, end in connections:
            if start in self.guides and end in self.blade_guides:
                # Create curve between guides
                points = [
                    cmds.xform(self.guides[start], q=True, t=True, ws=True),
                    cmds.xform(self.blade_guides[end], q=True, t=True, ws=True)
                ]

                curve = cmds.curve(
                    name=f"{self.module_id}_{start}_upv_connection",
                    p=points,
                    degree=1
                )

                # Set curve color to match blade guides
                shape = cmds.listRelatives(curve, shapes=True)[0]
                cmds.setAttr(f"{shape}.overrideEnabled", 1)
                cmds.setAttr(f"{shape}.overrideRGBColors", 1)
                cmds.setAttr(f"{shape}.overrideColorR", 0)
                cmds.setAttr(f"{shape}.overrideColorG", 0.8)
                cmds.setAttr(f"{shape}.overrideColorB", 0.8)

                # Parent to guide group
                cmds.parent(curve, self.guide_grp)

                # Create position constraints so the curve follows the guides
                cls = cmds.cluster(f"{curve}.cv[0]")[1]
                cmds.pointConstraint(self.guides[start], cls)

                cls = cmds.cluster(f"{curve}.cv[1]")[1]
                cmds.pointConstraint(self.blade_guides[end], cls)

                # Hide clusters
                cmds.setAttr(f"{cls}.visibility", 0)

    def build(self):
        """Build the spine rig."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        # 1. Validate and adjust guide positions for coherence
        self._validate_guides()

        # 2. Create joints with proper orientation
        self._create_spine_joints_with_orientation()

        # 3. Create spine controls
        self._create_spine_controls()

        # 4. Set up spine constraints
        self._setup_spine_constraints()

    def _validate_guides(self):
        """
        Validate guide positions and make adjustments if needed.
        Checks for planarity in the spine guides.
        """
        # Get positions of all spine guides in sequence
        positions = []
        for i in range(self.num_joints):
            guide_name = f"spine_{i + 1:02d}"
            if guide_name in self.guides:
                pos = cmds.xform(self.guides[guide_name], query=True, translation=True, worldSpace=True)
                positions.append(pos)

        # Add chest position if it exists
        if "chest" in self.guides:
            pos = cmds.xform(self.guides["chest"], query=True, translation=True, worldSpace=True)
            positions.append(pos)

        # Check if guides form a planar chain
        self.is_planar = is_planar_chain(positions)

        if not self.is_planar:
            print(f"Warning: {self.module_id} guide chain is not planar.")

            # Adjust positions to be planar, maintaining the original heights
            adjusted_positions = make_planar(positions)
            self.planar_adjusted = True

            # Update guide positions
            guides_to_update = [f"spine_{i + 1:02d}" for i in range(self.num_joints)]
            if "chest" in self.guides:
                guides_to_update.append("chest")

            for i, guide_name in enumerate(guides_to_update):
                if i < len(adjusted_positions) and guide_name in self.guides:
                    cmds.xform(self.guides[guide_name], t=adjusted_positions[i], ws=True)

            print(f"Guide positions adjusted to ensure planarity for {self.module_id}")

        # Also check vertical alignment of COG and pelvis
        if "cog" in self.guides and "pelvis" in self.guides:
            cog_pos = cmds.xform(self.guides["cog"], query=True, translation=True, worldSpace=True)
            pelvis_pos = cmds.xform(self.guides["pelvis"], query=True, translation=True, worldSpace=True)

            # Check if X and Z coordinates differ by more than a small threshold
            if abs(cog_pos[0] - pelvis_pos[0]) > 0.01 or abs(cog_pos[2] - pelvis_pos[2]) > 0.01:
                print(f"Warning: COG and pelvis are not vertically aligned for {self.module_id}")

                # Adjust pelvis X and Z to match COG
                new_pelvis_pos = [cog_pos[0], pelvis_pos[1], cog_pos[2]]
                cmds.xform(self.guides["pelvis"], t=new_pelvis_pos, ws=True)
                print(f"Pelvis position adjusted to align with COG for {self.module_id}")

    def _create_spine_joints_with_orientation(self):
        """Create spine joints with proper hierarchy and specific orientation for each section."""
        # First, clear any existing joints
        self._clear_existing_spine_joints()

        # Get guide positions
        positions = []
        guide_sequence = ["pelvis"]

        # Add spine guides in sequence
        for i in range(self.num_joints):
            guide_name = f"spine_{i + 1:02d}"
            guide_sequence.append(guide_name)

        # Add chest guide
        guide_sequence.append("chest")

        # Get positions in order and verify they exist
        print("\nCollecting guide positions for spine joints:")
        for guide_name in guide_sequence:
            if guide_name in self.guides:
                pos = cmds.xform(self.guides[guide_name], query=True, translation=True, worldSpace=True)
                positions.append(pos)
                print(f"  {guide_name}: {pos}")
            else:
                print(f"  Warning: Guide '{guide_name}' not found")
                return

        # Check if positions appear valid
        if len(positions) < 2:
            print("Error: Not enough valid guide positions to create spine")
            return

        # Create joint names
        joint_names = []
        for i, guide_name in enumerate(guide_sequence):
            joint_name = f"{self.module_id}_{guide_name}_jnt"
            joint_names.append(joint_name)

        # Create COG joint first
        cog_joint = None
        if "cog" in self.guides:
            # Get COG position
            cog_pos = cmds.xform(self.guides["cog"], query=True, translation=True, worldSpace=True)

            # Create the COG joint
            cmds.select(clear=True)
            cog_joint = cmds.joint(name=f"{self.module_id}_cog_jnt", position=cog_pos)
            self.joints["cog"] = cog_joint

            # Parent to joint group
            cmds.parent(cog_joint, self.joint_grp)

            # Set neutral orientation directly
            cmds.setAttr(f"{cog_joint}.jointOrient", 0, 0, 0)
            print(f"Created COG joint: {cog_joint} at {cog_pos}")

        # Create pelvis as child of COG
        cmds.select(clear=True)
        if cog_joint:
            cmds.select(cog_joint)
        pelvis_joint = cmds.joint(name=joint_names[0], p=positions[0])
        if not cog_joint:
            cmds.parent(pelvis_joint, self.joint_grp)
        self.joints[guide_sequence[0]] = pelvis_joint
        print(f"Created pelvis joint: {pelvis_joint} at {positions[0]}")

        # Create spine_01 as a child of COG (not pelvis)
        cmds.select(clear=True)
        if cog_joint:
            cmds.select(cog_joint)
        else:
            cmds.select(self.joint_grp)
        spine01_joint = cmds.joint(name=joint_names[1], p=positions[1])
        self.joints[guide_sequence[1]] = spine01_joint
        print(f"Created spine_01 joint: {spine01_joint} at {positions[1]}")

        # Create spine_02
        if self.num_joints >= 2:
            cmds.select(spine01_joint)
            spine02_joint = cmds.joint(name=joint_names[2], p=positions[2])
            self.joints[guide_sequence[2]] = spine02_joint
            print(f"Created spine_02 joint: {spine02_joint} at {positions[2]}")

        # Create spine_03 and beyond with their children
        if self.num_joints >= 3:
            for i in range(3, len(joint_names)):
                prev_joint = self.joints[guide_sequence[i - 1]]
                cmds.select(prev_joint)
                joint = cmds.joint(name=joint_names[i], p=positions[i])
                self.joints[guide_sequence[i]] = joint
                print(f"Created joint: {joint} at {positions[i]}")

        # Orient joints in specific sections as requested:

        # First section (up to spine_02): Use yup
        if "spine_01" in self.joints:
            # Start from the first spine joint
            cmds.select(self.joints["spine_01"])

            # If spine_02 exists, orient both with yup
            if "spine_02" in self.joints:
                print("Orienting first spine section with xyz/yup")
                cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)

        # Second section (spine_03 and spine_04): Use zdown
        for i in range(3, min(self.num_joints + 1, 5)):  # spine_03 and spine_04 if they exist
            joint_name = f"spine_{i:02d}"
            if joint_name in self.joints:
                print(f"Orienting {joint_name} with xyz/zdown")
                cmds.select(self.joints[joint_name])
                cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="zdown", zeroScaleOrient=True)

        # Make sure chest follows the orientation of the last spine joint
        if "chest" in self.joints and f"spine_{self.num_joints:02d}" in self.joints:
            last_spine = self.joints[f"spine_{self.num_joints:02d}"]
            chest_joint = self.joints["chest"]

            # Get orientation from last spine joint
            last_orient = cmds.getAttr(f"{last_spine}.jointOrient")[0]

            # Apply to chest joint
            cmds.setAttr(f"{chest_joint}.jointOrient", last_orient[0], last_orient[1], last_orient[2])
            print(f"Matched chest joint orientation to last spine: {last_orient}")

        print("Spine joint creation complete with proper hierarchy and orientation")

    def _clear_existing_spine_joints(self):
        """Clear any existing spine joints before creating new ones."""
        # Build a list of potential joint names
        joint_list = [f"{self.module_id}_cog_jnt", f"{self.module_id}_pelvis_jnt"]

        # Add spine joints
        for i in range(self.num_joints):
            joint_list.append(f"{self.module_id}_spine_{i + 1:02d}_jnt")

        # Add chest joint
        joint_list.append(f"{self.module_id}_chest_jnt")

        # Delete any existing joints
        for joint in joint_list:
            if cmds.objExists(joint):
                cmds.delete(joint)

        # Clear the joints dictionary
        self.joints = {}

    def _create_spine_controls(self):
        """Create the spine controls with proper hierarchy and no pelvis control."""
        print(f"Creating spine controls for {self.module_id}")

        # Clear any existing controls
        self._clear_existing_controls()

        # Create COG control as the root
        if "cog" in self.joints:
            self._create_cog_control()

        # No pelvis control - removed

        # Create spine controls in sequence, starting from spine_01 under COG
        for i in range(1, self.num_joints + 1):
            spine_name = f"spine_{i:02d}"
            if spine_name in self.joints:
                if i == 1:
                    # First spine control parented directly to COG
                    self._create_spine_control(spine_name, i, parent_to_cog=True)
                else:
                    # Other spine controls follow the chain
                    self._create_spine_control(spine_name, i)

        # Create chest control at the end of the chain
        if "chest" in self.joints:
            self._create_chest_control()

        print(f"Spine controls created for {self.module_id}")

    def _clear_existing_controls(self):
        """Clear any existing spine controls."""
        # Build a list of potential control names
        control_names = [f"{self.module_id}_cog_ctrl"]  # Add COG back to the list

        # Add spine controls
        for i in range(1, self.num_joints + 1):
            control_names.append(f"{self.module_id}_spine_{i:02d}_ctrl")

        # Add chest control
        control_names.append(f"{self.module_id}_chest_ctrl")

        # Delete any existing controls
        for ctrl in control_names:
            if cmds.objExists(ctrl):
                ctrl_grp = f"{ctrl}_grp"
                if cmds.objExists(ctrl_grp):
                    cmds.delete(ctrl_grp)
                else:
                    cmds.delete(ctrl)

        # Clear controls dictionary
        self.controls = {}

    def _create_cog_control(self):
        """Create the COG (root) control with square shape."""
        cog_joint = self.joints["cog"]
        cog_pos = cmds.xform(cog_joint, query=True, translation=True, worldSpace=True)

        # Create square control with larger size
        cog_ctrl, cog_grp = create_control(
            f"{self.module_id}_cog_ctrl",
            "square",  # Square shape for COG
            20.0,  # Larger size
            CONTROL_COLORS["cog"],  # Orange color
            parent=self.control_grp
        )

        # Position at COG joint
        cmds.xform(cog_grp, translation=cog_pos, worldSpace=True)

        # Store in controls dictionary
        self.controls["cog"] = cog_ctrl

    def _create_spine_control(self, spine_name, index, parent_to_cog=False):
        """Create a control for a spine joint."""
        spine_joint = self.joints[spine_name]
        spine_pos = cmds.xform(spine_joint, query=True, translation=True, worldSpace=True)

        # Use circle shape
        spine_ctrl, spine_grp = create_control(
            f"{self.module_id}_{spine_name}_ctrl",
            "circle",  # Circle shape for spine
            20.0 - (index * 0.4),  # Gradual size reduction
            CONTROL_COLORS["main"],  # Yellow color
            normal=[1, 0, 0]  # X axis normal for proper orientation
        )

        # Position and orient to match joint
        cmds.xform(spine_grp, translation=spine_pos, worldSpace=True)
        temp_constraint = cmds.orientConstraint(spine_joint, spine_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Parent according to hierarchy
        if parent_to_cog and "cog" in self.controls:
            # First spine control goes directly under COG
            cmds.parent(spine_grp, self.controls["cog"])
            print(f"  Parented {spine_name} directly to COG")
        elif index > 1:
            # Other spine controls follow chain hierarchy
            prev_spine = f"spine_{index - 1:02d}"
            if prev_spine in self.controls:
                cmds.parent(spine_grp, self.controls[prev_spine])
                print(f"  Parented {spine_name} to {prev_spine}")
        else:
            # Fallback to control group if COG doesn't exist
            cmds.parent(spine_grp, self.control_grp)
            print(f"  Parented {spine_name} to control group (fallback)")

        # Store in controls dictionary
        self.controls[spine_name] = spine_ctrl

    def _create_chest_control(self):
        """Create the chest control."""
        chest_joint = self.joints["chest"]
        chest_pos = cmds.xform(chest_joint, query=True, translation=True, worldSpace=True)

        # Create control with reduced size
        chest_ctrl, chest_grp = create_control(
            f"{self.module_id}_chest_ctrl",
            "circle",  # Circle shape
            20.0,  # Reduced size (was 16.0)
            CONTROL_COLORS["main"],  # Yellow color
            normal=[1, 0, 0]  # Initial orientation (will be adjusted)
        )

        # Position and orient to match joint
        cmds.xform(chest_grp, translation=chest_pos, worldSpace=True)
        temp_constraint = cmds.orientConstraint(chest_joint, chest_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Parent to last spine control
        last_spine = f"spine_{self.num_joints:02d}"
        if last_spine in self.controls:
            cmds.parent(chest_grp, self.controls[last_spine])

        # Store in controls dictionary
        self.controls["chest"] = chest_ctrl

    def _setup_spine_constraints(self):
        """Set up constraints between spine controls and joints."""
        print(f"Setting up spine constraints for {self.module_id}")

        # COG control to COG joint
        if "cog" in self.controls and "cog" in self.joints:
            cmds.parentConstraint(
                self.controls["cog"],
                self.joints["cog"],
                maintainOffset=True
            )
            print(f"  Created parent constraint: cog")

        # Spine controls to spine joints
        for i in range(1, self.num_joints + 1):
            spine_name = f"spine_{i:02d}"
            if spine_name in self.controls and spine_name in self.joints:
                cmds.parentConstraint(
                    self.controls[spine_name],
                    self.joints[spine_name],
                    maintainOffset=True
                )
                print(f"  Created parent constraint: {spine_name}")

        # Chest control to chest joint
        if "chest" in self.controls and "chest" in self.joints:
            cmds.parentConstraint(
                self.controls["chest"],
                self.joints["chest"],
                maintainOffset=True
            )
            print(f"  Created parent constraint: chest")

        print(f"Spine constraints completed for {self.module_id}")

    def get_guide_positions(self):
        """
        Get the positions of all module guides.

        Returns:
            dict: Guide positions including blade guides
        """
        positions = super().get_guide_positions()

        # Add blade guide positions
        for guide_name, guide in self.blade_guides.items():
            if cmds.objExists(guide):
                pos = cmds.xform(guide, query=True, translation=True, worldSpace=True)
                rot = cmds.xform(guide, query=True, rotation=True, worldSpace=True)
                positions[guide_name] = {
                    'position': pos,
                    'rotation': rot
                }

        return positions

    def set_guide_positions(self, positions):
        """
        Set the positions of all module guides.

        Args:
            positions (dict): Guide positions including blade guides
        """
        # First set standard guide positions
        super().set_guide_positions(positions)

        # Then set blade guide positions
        for guide_name, guide_data in positions.items():
            if guide_name in self.blade_guides and cmds.objExists(self.blade_guides[guide_name]):
                guide = self.blade_guides[guide_name]
                cmds.xform(guide, translation=guide_data['position'], worldSpace=True)
                cmds.xform(guide, rotation=guide_data['rotation'], worldSpace=True)