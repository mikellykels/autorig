"""
Modular Rig System
Neck Module

This module contains the implementation of the neck rig module.

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


class NeckModule(BaseModule):
    """
    Module for creating a neck rig with improved orientation.
    """

    def __init__(self, side="c", module_name="neck", num_joints=3):
        """
        Initialize the neck module.

        Args:
            side (str): Side of the body (almost always "c" for center)
            module_name (str): Name of the module
            num_joints (int): Number of neck joints
        """
        super().__init__(side, module_name, "neck")
        self.num_joints = num_joints

        # Additional blade guide references for orientation
        self.blade_guides = {}

        # Store planar validation results
        self.is_planar = True
        self.planar_adjusted = False

    def create_guides(self):
        """Create the neck guides with orientation helpers."""
        self._create_module_groups()

        # Create neck base guide (connects to chest)
        self.guides["neck_base"] = create_guide(f"{self.module_id}_neck_base", (0, 18, 0), self.guide_grp)

        # Create neck guides with proper padding
        step = 3.0 / (self.num_joints) if self.num_joints > 0 else 0
        for i in range(self.num_joints):
            # Use 2-digit padding for neck numbers
            name = f"{self.module_id}_neck_{i + 1:02d}"
            pos = (0, 18 + step * (i + 1), 0)  # Start position after neck_base
            self.guides[f"neck_{i + 1:02d}"] = create_guide(name, pos, self.guide_grp)

        # Create blade guides for orientation references
        # Neck base up vector
        self.blade_guides["upv_neck_base"] = create_guide(
            f"{self.module_id}_upv_neck_base",
            (0, 18, -2),  # Positioned behind neck base
            self.guide_grp,
            color=GUIDE_BLADE_COLOR
        )

        # Mid neck up vector if we have enough joints
        if self.num_joints >= 3:
            mid_idx = max(1, self.num_joints // 2)
            if f"neck_{mid_idx:02d}" in self.guides:
                mid_neck_pos = cmds.xform(self.guides[f"neck_{mid_idx:02d}"], q=True, t=True, ws=True)
                self.blade_guides["upv_mid_neck"] = create_guide(
                    f"{self.module_id}_upv_mid_neck",
                    (mid_neck_pos[0], mid_neck_pos[1], mid_neck_pos[2] - 2),  # Behind mid neck
                    self.guide_grp,
                    color=GUIDE_BLADE_COLOR
                )

        # Create visual connections between guides and their blade guides
        self._create_guide_connections()

    def _create_guide_connections(self):
        """Create visual curve connections between guides and their blade guides."""
        # Define connections to create
        connections = [
            ("neck_base", "upv_neck_base")
        ]

        # Add mid-neck connection if it exists
        if self.num_joints >= 3:
            mid_idx = max(1, self.num_joints // 2)
            if f"neck_{mid_idx:02d}" in self.guides and "upv_mid_neck" in self.blade_guides:
                connections.append((f"neck_{mid_idx:02d}", "upv_mid_neck"))

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
                cls1 = cmds.cluster(f"{curve}.cv[0]")[1]
                cmds.pointConstraint(self.guides[start], cls1)

                cls2 = cmds.cluster(f"{curve}.cv[1]")[1]
                cmds.pointConstraint(self.blade_guides[end], cls2)

                # Hide clusters
                cmds.setAttr(f"{cls1}.visibility", 0)
                cmds.setAttr(f"{cls2}.visibility", 0)

    def build(self):
        """Build the neck rig."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        # 1. Validate and adjust guide positions for coherence
        self._validate_guides()

        # 2. Create joints with proper orientation
        self._create_joints_with_orientation()

        # 3. Check for head module and adjust last joint orientation
        self._check_for_head()

        # 4. Create controls
        self._create_controls()

        # 5. Set up constraints
        self._setup_constraints()

    def _check_for_head(self):
        """Check if a head module exists and orient the last neck joint toward it."""
        if not self.manager:
            return

        # Find a head module in the same rig
        head_module = None
        for module_id, module in self.manager.modules.items():
            if module.module_type == "head" and module.side == self.side:
                head_module = module
                break

        if not head_module or "head_base" not in head_module.guides:
            # No head module found, nothing to adjust
            return

        # Get the last neck joint
        last_neck_name = f"neck_{self.num_joints:02d}"
        if last_neck_name not in self.joints:
            return

        last_neck_joint = self.joints[last_neck_name]

        # Get position of last neck joint and head base guide
        neck_pos = cmds.xform(last_neck_joint, query=True, translation=True, worldSpace=True)
        head_pos = cmds.xform(head_module.guides["head_base"], query=True, translation=True, worldSpace=True)

        # Calculate vector from neck to head
        neck_to_head = [
            head_pos[0] - neck_pos[0],
            head_pos[1] - neck_pos[1],
            head_pos[2] - neck_pos[2]
        ]

        # Normalize
        length = (neck_to_head[0] ** 2 + neck_to_head[1] ** 2 + neck_to_head[2] ** 2) ** 0.5
        if length < 0.001:  # Too close together
            return

        # Don't need to do anything here - the head module will handle the connection
        # Just printing debug info
        print(f"Found head module that will connect to last neck joint {last_neck_joint}")

    def _validate_guides(self):
        """
        Validate guide positions and make adjustments if needed.
        Checks for planarity in the neck guides.
        """
        # Get positions of all guides in sequence
        positions = []

        # Add neck base
        if "neck_base" in self.guides:
            pos = cmds.xform(self.guides["neck_base"], query=True, translation=True, worldSpace=True)
            positions.append(pos)

        # Add neck guides
        for i in range(self.num_joints):
            guide_name = f"neck_{i + 1:02d}"
            if guide_name in self.guides:
                pos = cmds.xform(self.guides[guide_name], query=True, translation=True, worldSpace=True)
                positions.append(pos)

        # Check if guides form a planar chain
        self.is_planar = is_planar_chain(positions)

        if not self.is_planar:
            print(f"Warning: {self.module_id} guide chain is not planar.")

            # Adjust positions to be planar, maintaining the original heights
            adjusted_positions = make_planar(positions)
            self.planar_adjusted = True

            # Update guide positions
            guides_to_update = ["neck_base"]
            guides_to_update.extend([f"neck_{i + 1:02d}" for i in range(self.num_joints)])

            for i, guide_name in enumerate(guides_to_update):
                if i < len(adjusted_positions) and guide_name in self.guides:
                    cmds.xform(self.guides[guide_name], t=adjusted_positions[i], ws=True)

            print(f"Guide positions adjusted to ensure planarity for {self.module_id}")

    def _create_joints_with_orientation(self):
        """Create neck joints with proper hierarchy and orientation."""
        # First, clear any existing joints
        self._clear_existing_joints()

        # Get guide positions
        positions = []
        guide_sequence = ["neck_base"]

        # Add neck guides in sequence
        for i in range(self.num_joints):
            guide_name = f"neck_{i + 1:02d}"
            guide_sequence.append(guide_name)

        # Get positions in order and verify they exist
        print("\nCollecting guide positions for neck joints:")
        for guide_name in guide_sequence:
            if guide_name in self.guides:
                pos = cmds.xform(self.guides[guide_name], query=True, translation=True, worldSpace=True)
                positions.append(pos)
                print(f"  {guide_name}: {pos}")
            else:
                print(f"  Warning: Guide '{guide_name}' not found")
                return

        # Check if positions appear valid
        if len(positions) < 2:  # Need at least neck_base and neck_01
            print("Error: Not enough valid guide positions to create neck")
            return

        # Create joint names
        joint_names = []
        for guide_name in guide_sequence:
            joint_name = f"{self.module_id}_{guide_name}_jnt"
            joint_names.append(joint_name)

        # Create the joints using Maya commands for maximum control
        cmds.select(clear=True)

        # Create neck_base joint
        neck_base_joint = cmds.joint(name=joint_names[0], p=positions[0])
        cmds.parent(neck_base_joint, self.joint_grp)
        self.joints["neck_base"] = neck_base_joint

        # Create neck joints
        prev_joint = neck_base_joint
        for i in range(1, self.num_joints + 1):
            cmds.select(prev_joint)
            joint = cmds.joint(name=joint_names[i], p=positions[i])
            self.joints[guide_sequence[i]] = joint
            prev_joint = joint

        # Try to find a head module to include in orientation
        head_guide_pos = None
        if self.manager:
            for module_id, module in self.manager.modules.items():
                if module.module_type == "head" and module.side == self.side:
                    if "head_base" in module.guides:
                        head_guide_pos = cmds.xform(module.guides["head_base"], query=True, translation=True,
                                                    worldSpace=True)
                        print(f"Found head guide position at {head_guide_pos} - will include in neck orientation")
                        break

        if head_guide_pos:
            # If we have a head guide, add it temporarily to help with orientation
            temp_head_joint = None
            try:
                # Select last neck joint
                last_neck_joint = self.joints[f"neck_{self.num_joints:02d}"]
                cmds.select(last_neck_joint)

                # Create a temporary joint at head position
                temp_head_joint = cmds.joint(name=f"{self.module_id}_temp_head_jnt", p=head_guide_pos)

                # Orient the full chain
                cmds.select(neck_base_joint)
                cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="zdown", children=True,
                           zeroScaleOrient=True)

                # Delete the temporary joint
                cmds.delete(temp_head_joint)
                temp_head_joint = None
            except Exception as e:
                print(f"Error during orientation with temp head: {str(e)}")
                if temp_head_joint and cmds.objExists(temp_head_joint):
                    cmds.delete(temp_head_joint)
        else:
            # Standard orientation without head reference
            print("No head guide found - using standard orientation")
            cmds.select(neck_base_joint)
            cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="zdown", children=True, zeroScaleOrient=True)

        # Verify the orientation of the joints
        for joint_key in guide_sequence:
            if joint_key in self.joints:
                joint = self.joints[joint_key]
                orient = cmds.getAttr(f"{joint}.jointOrient")[0]
                print(f"Joint {joint} orientation: {orient}")

        print("Neck joint creation complete with proper hierarchy and orientation")

        # Run debug to verify orientations
        self.debug_joint_orientations()

    def _clear_existing_joints(self):
        """Clear any existing neck joints before creating new ones."""
        # Build a list of potential joint names
        joint_list = [f"{self.module_id}_neck_base_jnt"]

        # Add neck joints
        for i in range(self.num_joints):
            joint_list.append(f"{self.module_id}_neck_{i + 1:02d}_jnt")

        # Delete any existing joints
        for joint in joint_list:
            if cmds.objExists(joint):
                cmds.delete(joint)

        # Clear the joints dictionary
        self.joints = {}

    def _create_controls(self):
        """Create the neck controls."""
        # Clear any existing controls
        self._clear_existing_controls()

        # 1. Create neck base control
        self._create_neck_base_control()

        # 2. Create mid-neck control if we have enough neck joints
        if self.num_joints >= 3:
            mid_idx = self.num_joints // 2
            mid_neck_name = f"neck_{mid_idx:02d}"
            if mid_neck_name in self.joints:
                self._create_mid_neck_control(mid_neck_name, mid_idx)

        # 3. Create top neck control for the last neck joint
        self._create_top_neck_control()

    def _clear_existing_controls(self):
        """Clear any existing neck controls."""
        # Build a list of potential control names
        control_names = [f"{self.module_id}_neck_base_ctrl", f"{self.module_id}_mid_neck_ctrl", f"{self.module_id}_top_neck_ctrl"]

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

    def _create_neck_base_control(self):
        """Create the neck base control."""
        if "neck_base" not in self.joints:
            return

        neck_base_joint = self.joints["neck_base"]
        pos = cmds.xform(neck_base_joint, query=True, translation=True, worldSpace=True)

        # Create circle control for neck base
        ctrl, ctrl_grp = create_control(
            f"{self.module_id}_neck_base_ctrl",
            "circle",
            8.0,  # Size
            CONTROL_COLORS["main"],  # Yellow
            normal=[1, 0, 0]  # X axis normal for proper orientation
        )

        # Position and orient to match joint
        cmds.xform(ctrl_grp, translation=pos, worldSpace=True)
        temp_constraint = cmds.orientConstraint(neck_base_joint, ctrl_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Parent to control group
        cmds.parent(ctrl_grp, self.control_grp)

        # Store reference
        self.controls["neck_base"] = ctrl

    def _create_mid_neck_control(self, mid_neck_name, index):
        """Create a mid-neck control for more flexible control."""
        if mid_neck_name not in self.joints:
            return

        mid_neck_joint = self.joints[mid_neck_name]
        pos = cmds.xform(mid_neck_joint, query=True, translation=True, worldSpace=True)

        # Create circle control for mid-neck
        ctrl, ctrl_grp = create_control(
            f"{self.module_id}_mid_neck_ctrl",
            "circle",
            7.0,  # Size (smaller than neck base)
            CONTROL_COLORS["main"],  # Yellow
            normal=[1, 0, 0]  # X axis normal for proper orientation
        )

        # Position and orient to match joint
        cmds.xform(ctrl_grp, translation=pos, worldSpace=True)
        temp_constraint = cmds.orientConstraint(mid_neck_joint, ctrl_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Parent to neck base control
        if "neck_base" in self.controls:
            cmds.parent(ctrl_grp, self.controls["neck_base"])
        else:
            cmds.parent(ctrl_grp, self.control_grp)

        # Store reference
        self.controls["mid_neck"] = ctrl

    def _create_top_neck_control(self):
        """Create a control for the top of the neck."""
        # Get the last neck joint
        last_neck_name = f"neck_{self.num_joints:02d}"

        if last_neck_name not in self.joints:
            return

        last_neck_joint = self.joints[last_neck_name]
        pos = cmds.xform(last_neck_joint, query=True, translation=True, worldSpace=True)

        # Create circle control for top neck
        ctrl, ctrl_grp = create_control(
            f"{self.module_id}_top_neck_ctrl",
            "circle",
            10.0,  # Size (smaller than mid-neck)
            CONTROL_COLORS["main"],  # Yellow
            normal=[1, 0, 0]  # X axis normal for proper orientation
        )

        # Position and orient to match joint
        cmds.xform(ctrl_grp, translation=pos, worldSpace=True)
        temp_constraint = cmds.orientConstraint(last_neck_joint, ctrl_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Parent to mid-neck or neck base control
        if "mid_neck" in self.controls:
            cmds.parent(ctrl_grp, self.controls["mid_neck"])
        elif "neck_base" in self.controls:
            cmds.parent(ctrl_grp, self.controls["neck_base"])
        else:
            cmds.parent(ctrl_grp, self.control_grp)

        # Store reference
        self.controls["top_neck"] = ctrl

    def _setup_constraints(self):
        """Set up constraints between controls and joints."""
        # Neck base control to neck base joint
        if "neck_base" in self.controls and "neck_base" in self.joints:
            cmds.parentConstraint(
                self.controls["neck_base"],
                self.joints["neck_base"],
                maintainOffset=True
            )

        # If we have mid-neck and top neck controls
        if self.num_joints >= 3 and "mid_neck" in self.controls and "top_neck" in self.controls:
            # Lower neck joints follow the neck base with decreasing weight
            mid_idx = self.num_joints // 2

            # First section: neck_base to mid_neck (inclusive)
            for i in range(1, mid_idx + 1):
                joint_key = f"neck_{i:02d}"
                if joint_key in self.joints:
                    # Calculate blend weight: 1.0 at neck_base, decreasing to 0 at mid_neck
                    weight = 1.0 - (i / mid_idx)

                    cmds.parentConstraint(
                        self.controls["neck_base"],
                        self.joints[joint_key],
                        maintainOffset=True,
                        weight=weight
                    )

                    cmds.parentConstraint(
                        self.controls["mid_neck"],
                        self.joints[joint_key],
                        maintainOffset=True,
                        weight=1.0 - weight
                    )

            # Second section: mid_neck to top_neck
            for i in range(mid_idx + 1, self.num_joints + 1):
                joint_key = f"neck_{i:02d}"
                if joint_key in self.joints:
                    # Calculate blend weight: 1.0 at mid_neck, decreasing to 0 at top_neck
                    remaining_joints = self.num_joints - mid_idx
                    weight = 1.0 - ((i - mid_idx) / remaining_joints)

                    cmds.parentConstraint(
                        self.controls["mid_neck"],
                        self.joints[joint_key],
                        maintainOffset=True,
                        weight=weight
                    )

                    cmds.parentConstraint(
                        self.controls["top_neck"],
                        self.joints[joint_key],
                        maintainOffset=True,
                        weight=1.0 - weight
                    )
        else:
            # Simple case: Blend from neck base to top neck control
            top_neck_ctrl = self.controls.get("top_neck")
            neck_base_ctrl = self.controls.get("neck_base")

            if top_neck_ctrl and neck_base_ctrl:
                for i in range(1, self.num_joints + 1):
                    joint_key = f"neck_{i:02d}"
                    if joint_key in self.joints:
                        # Calculate blend weight: 1.0 at neck_base, decreasing to 0 at top_neck
                        weight = 1.0 - (i / self.num_joints)

                        cmds.parentConstraint(
                            neck_base_ctrl,
                            self.joints[joint_key],
                            maintainOffset=True,
                            weight=weight
                        )

                        cmds.parentConstraint(
                            top_neck_ctrl,
                            self.joints[joint_key],
                            maintainOffset=True,
                            weight=1.0 - weight
                        )

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

    def update_neck_orientation(self):
        """
        Update the orientation of the neck joints.
        This can be called after the rig is built to fix orientation issues.
        """
        # Check if we have neck joints
        if not self.joints:
            print("No neck joints to update orientation")
            return False

        try:
            # Get the last neck joint
            last_neck_name = f"neck_{self.num_joints:02d}"
            neck_base_name = "neck_base"

            if last_neck_name not in self.joints or neck_base_name not in self.joints:
                print(f"Missing required joints for orientation update")
                return False

            # Get all neck joints in order
            neck_joints = [self.joints[neck_base_name]]
            for i in range(1, self.num_joints + 1):
                joint_key = f"neck_{i:02d}"
                if joint_key in self.joints:
                    neck_joints.append(self.joints[joint_key])

            # Check we have the expected number
            if len(neck_joints) != self.num_joints + 1:
                print(f"Expected {self.num_joints + 1} neck joints, found {len(neck_joints)}")
                return False

            # Before we do anything, check if there's a head module connected
            head_module = None
            if self.manager:
                for module_id, module in self.manager.modules.items():
                    if module.module_type == "head" and module.side == self.side:
                        head_module = module
                        break

            head_joint = None
            if head_module and "head_base" in head_module.joints:
                head_joint = head_module.joints["head_base"]

            # If we have a head connected, we need to temporarily disconnect it
            head_children = []
            if head_joint and cmds.objExists(head_joint):
                # Check if head is a child of the last neck joint
                head_parent = cmds.listRelatives(head_joint, parent=True)
                if head_parent and head_parent[0] == neck_joints[-1]:
                    # Store head children
                    head_children = cmds.listRelatives(head_joint, children=True) or []

                    # Unparent children from head
                    for child in head_children:
                        cmds.parent(child, world=True)

                    # Unparent head from neck
                    cmds.parent(head_joint, world=True)
                    print(f"Temporarily disconnected head {head_joint} from neck")

            # Get all neck joint children and disconnect them temporarily
            neck_joint_children = {}
            for joint in neck_joints:
                children = cmds.listRelatives(joint, children=True, type="joint") or []

                # Filter out joints that are part of our chain
                filtered_children = [child for child in children if child not in neck_joints]

                if filtered_children:
                    neck_joint_children[joint] = filtered_children
                    for child in filtered_children:
                        cmds.parent(child, world=True)
                        print(f"Temporarily disconnected {child} from {joint}")

            # Backup the current orientation values before changes
            original_orients = {}
            for joint in neck_joints:
                original_orients[joint] = cmds.getAttr(f"{joint}.jointOrient")[0]

            # Now update the orientation with zdown method
            try:
                # Select base joint and apply orientation
                cmds.select(neck_joints[0])
                cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="zdown",
                           children=True, zeroScaleOrient=True)
                print(f"Updated neck joint chain orientation with xyz/zdown")

                # Verify orientations were updated
                for joint in neck_joints:
                    new_orient = cmds.getAttr(f"{joint}.jointOrient")[0]
                    old_orient = original_orients[joint]
                    print(f"Joint {joint} orientation changed:")
                    print(f"  Before: {old_orient}")
                    print(f"  After: {new_orient}")
            except Exception as e:
                print(f"Error updating orientation: {str(e)}")
                # Restore original orients on failure
                for joint, orient in original_orients.items():
                    cmds.setAttr(f"{joint}.jointOrient", orient[0], orient[1], orient[2])

            # Reconnect children to their original parents
            for parent_joint, children in neck_joint_children.items():
                for child in children:
                    if cmds.objExists(child) and cmds.objExists(parent_joint):
                        cmds.parent(child, parent_joint)
                        print(f"Reconnected {child} to {parent_joint}")

            # If we had a head, reconnect it
            if head_joint and cmds.objExists(head_joint) and cmds.objExists(neck_joints[-1]):
                # Parent head back to last neck with matching orientation

                # First zero out rotations on both joints
                cmds.setAttr(f"{neck_joints[-1]}.rotate", 0, 0, 0)
                cmds.setAttr(f"{head_joint}.rotate", 0, 0, 0)

                # Get updated neck orientation
                neck_orient = cmds.getAttr(f"{neck_joints[-1]}.jointOrient")[0]

                # Apply same orientation to head for continuous chain
                cmds.setAttr(f"{head_joint}.jointOrient",
                             neck_orient[0], neck_orient[1], neck_orient[2])

                # Parent head to neck
                cmds.parent(head_joint, neck_joints[-1])
                print(f"Reconnected head {head_joint} to neck {neck_joints[-1]}")

                # Reconnect head children
                for child in head_children:
                    if cmds.objExists(child):
                        cmds.parent(child, head_joint)
                        print(f"Reconnected {child} to head {head_joint}")

            return True
        except Exception as e:
            import traceback
            print(f"Error in update_neck_orientation: {str(e)}")
            traceback.print_exc()
            return False

    def debug_joint_orientations(self):
        """Print detailed information about all neck joint orientations."""
        print("\n=== NECK MODULE JOINT ORIENTATION DEBUG ===")

        if not self.joints:
            print("No joints found in the neck module!")
            return

        # Check neck_base
        if "neck_base" in self.joints:
            joint = self.joints["neck_base"]

            # Get orientation and rotation
            orient = cmds.getAttr(f"{joint}.jointOrient")[0]
            rotate = cmds.getAttr(f"{joint}.rotate")[0]

            print(f"neck_base joint: {joint}")
            print(f"  jointOrient: {orient}")
            print(f"  rotate: {rotate}")

            # Get matrix to show axes direction
            matrix = cmds.xform(joint, query=True, matrix=True, worldSpace=True)

            # Extract axes (first 3 values of each row represent X, Y, Z axes)
            x_axis = [matrix[0], matrix[1], matrix[2]]  # First 3 values are X axis
            y_axis = [matrix[4], matrix[5], matrix[6]]  # Second row is Y axis
            z_axis = [matrix[8], matrix[9], matrix[10]]  # Third row is Z axis

            # Normalize for clarity
            length = (x_axis[0] ** 2 + x_axis[1] ** 2 + x_axis[2] ** 2) ** 0.5
            if length > 0.001:
                x_axis = [v / length for v in x_axis]

            length = (y_axis[0] ** 2 + y_axis[1] ** 2 + y_axis[2] ** 2) ** 0.5
            if length > 0.001:
                y_axis = [v / length for v in y_axis]

            length = (z_axis[0] ** 2 + z_axis[1] ** 2 + z_axis[2] ** 2) ** 0.5
            if length > 0.001:
                z_axis = [v / length for v in z_axis]

            print(f"  X axis (aim): {x_axis}")
            print(f"  Y axis (up): {y_axis}")
            print(f"  Z axis (side): {z_axis}")

        # Check all neck joints
        for i in range(1, self.num_joints + 1):
            joint_key = f"neck_{i:02d}"

            if joint_key in self.joints:
                joint = self.joints[joint_key]

                # Get orientation and rotation
                orient = cmds.getAttr(f"{joint}.jointOrient")[0]
                rotate = cmds.getAttr(f"{joint}.rotate")[0]

                print(f"\n{joint_key} joint: {joint}")
                print(f"  jointOrient: {orient}")
                print(f"  rotate: {rotate}")

                # Get matrix to show axes direction
                matrix = cmds.xform(joint, query=True, matrix=True, worldSpace=True)

                # Extract axes
                x_axis = [matrix[0], matrix[1], matrix[2]]  # First 3 values are X axis
                y_axis = [matrix[4], matrix[5], matrix[6]]  # Second row is Y axis
                z_axis = [matrix[8], matrix[9], matrix[10]]  # Third row is Z axis

                # Normalize
                length = (x_axis[0] ** 2 + x_axis[1] ** 2 + x_axis[2] ** 2) ** 0.5
                if length > 0.001:
                    x_axis = [v / length for v in x_axis]

                length = (y_axis[0] ** 2 + y_axis[1] ** 2 + y_axis[2] ** 2) ** 0.5
                if length > 0.001:
                    y_axis = [v / length for v in y_axis]

                length = (z_axis[0] ** 2 + z_axis[1] ** 2 + z_axis[2] ** 2) ** 0.5
                if length > 0.001:
                    z_axis = [v / length for v in z_axis]

                print(f"  X axis (aim): {x_axis}")
                print(f"  Y axis (up): {y_axis}")
                print(f"  Z axis (side): {z_axis}")

                # Check if next joint/guide exists to verify aim direction
                next_joint = None
                if i < self.num_joints:
                    next_key = f"neck_{i + 1:02d}"
                    if next_key in self.joints:
                        next_joint = self.joints[next_key]
                elif self.manager:
                    # If this is the last neck joint, check for head
                    for mod_id, module in self.manager.modules.items():
                        if module.module_type == "head" and module.side == self.side:
                            if "head_base" in module.joints:
                                next_joint = module.joints["head_base"]
                                break

                if next_joint:
                    # Calculate vector from this joint to next
                    this_pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)
                    next_pos = cmds.xform(next_joint, query=True, translation=True, worldSpace=True)

                    to_next = [
                        next_pos[0] - this_pos[0],
                        next_pos[1] - this_pos[1],
                        next_pos[2] - this_pos[2]
                    ]

                    # Normalize
                    length = (to_next[0] ** 2 + to_next[1] ** 2 + to_next[2] ** 2) ** 0.5
                    if length > 0.001:
                        to_next = [v / length for v in to_next]

                    # Compare with X axis (should be similar if properly oriented)
                    dot_product = x_axis[0] * to_next[0] + x_axis[1] * to_next[1] + x_axis[2] * to_next[2]
                    angle = math.acos(min(1.0, max(-1.0, dot_product))) * 180 / math.pi

                    print(f"  Vector to next joint: {to_next}")
                    print(f"  Angle between X axis and vector to next joint: {angle} degrees")
                    print(f"  ORIENTATION STATUS: {'GOOD' if angle < 45 else 'BAD'}")

        print("\n=== END OF NECK ORIENTATION DEBUG ===\n")