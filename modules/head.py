"""
Modular Auto-Rig System
Head Module

This module contains the implementation of the head rig module.

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


class HeadModule(BaseModule):
    """
    Module for creating a head rig with improved orientation.
    """

    def __init__(self, side="c", module_name="head"):
        """
        Initialize the head module.

        Args:
            side (str): Side of the body (almost always "c" for center)
            module_name (str): Name of the module
        """
        super().__init__(side, module_name, "head")

        # Additional blade guide references for orientation
        self.blade_guides = {}

    def create_guides(self):
        """Create the head guides with orientation helpers."""
        self._create_module_groups()

        # Create head base guide (connects to neck or chest)
        self.guides["head_base"] = create_guide(f"{self.module_id}_head_base", (0, 21, 0), self.guide_grp)

        # Create head end guide (represents the top of the head)
        self.guides["head_end"] = create_guide(f"{self.module_id}_head_end", (0, 24, 0), self.guide_grp)

        # Create head up vector guide (for orientation)
        head_pos = cmds.xform(self.guides["head_base"], q=True, t=True, ws=True)
        self.blade_guides["upv_head"] = create_guide(
            f"{self.module_id}_upv_head",
            (head_pos[0], head_pos[1], head_pos[2] - 2),  # Behind head
            self.guide_grp,
            color=GUIDE_BLADE_COLOR
        )

        # Create visual connections between guides and their blade guides
        self._create_guide_connections()

    def _create_guide_connections(self):
        """Create visual curve connections between guides and their blade guides."""
        # Create connection to head up vector
        if "head_base" in self.guides and "upv_head" in self.blade_guides:
            # Create curve between guides
            points = [
                cmds.xform(self.guides["head_base"], q=True, t=True, ws=True),
                cmds.xform(self.blade_guides["upv_head"], q=True, t=True, ws=True)
            ]

            curve = cmds.curve(
                name=f"{self.module_id}_head_upv_connection",
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
            cmds.pointConstraint(self.guides["head_base"], cls1)

            cls2 = cmds.cluster(f"{curve}.cv[1]")[1]
            cmds.pointConstraint(self.blade_guides["upv_head"], cls2)

            # Hide clusters
            cmds.setAttr(f"{cls1}.visibility", 0)
            cmds.setAttr(f"{cls2}.visibility", 0)

    def build(self):
        """Build the head rig."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        # 1. Create joints with proper orientation
        self._create_joints_with_orientation()

        # 2. Create controls
        self._create_controls()

        # 3. Set up constraints
        self._setup_constraints()

        # 4. Check for neck module and connect if available
        self._connect_to_neck()

    def _connect_to_neck(self):
        """Find and connect to a neck module if one exists."""
        if not self.manager:
            return

        # Find a neck module in the same rig
        neck_module = None
        for module_id, module in self.manager.modules.items():
            if module.module_type == "neck" and module.side == self.side:
                neck_module = module
                break

        if not neck_module:
            print("No neck module found to connect to.")
            return

        # Get the last neck joint
        last_neck_joint = None
        last_neck_name = f"neck_{neck_module.num_joints:02d}"

        if last_neck_name in neck_module.joints:
            last_neck_joint = neck_module.joints[last_neck_name]
        else:
            print(f"Last neck joint ({last_neck_name}) not found in neck module.")
            return

        # Get the head base joint
        if "head_base" not in self.joints:
            print("Head base joint not found.")
            return

        head_base_joint = self.joints["head_base"]
        head_end_joint = self.joints.get("head_end")

        # Check if both joints exist
        if not cmds.objExists(last_neck_joint) or not cmds.objExists(head_base_joint):
            print(f"Required joints don't exist: neck={last_neck_joint}, head={head_base_joint}")
            return

        try:
            # Store original parents
            neck_parent = cmds.listRelatives(last_neck_joint, parent=True)
            head_parent = cmds.listRelatives(head_base_joint, parent=True)

            # Check if head is already a child of the neck
            if head_parent and head_parent[0] == last_neck_joint:
                print(f"Head joint {head_base_joint} is already connected to neck joint {last_neck_joint}")

                # Still connect the controls
                self._connect_controls_to_neck(neck_module)
                return

            # Save original head_end situation
            head_end_parent = None
            if head_end_joint and cmds.objExists(head_end_joint):
                head_end_parent = cmds.listRelatives(head_end_joint, parent=True)
                head_end_pos = cmds.xform(head_end_joint, query=True, translation=True, worldSpace=True)
                cmds.parent(head_end_joint, world=True)

            # Temporarily unparent head base
            if head_parent:
                cmds.parent(head_base_joint, world=True)

            # IMPORTANT: First ensure both joints have zero rotation
            cmds.setAttr(f"{last_neck_joint}.rotate", 0, 0, 0)
            cmds.setAttr(f"{head_base_joint}.rotate", 0, 0, 0)

            # Get orientation of last neck joint
            neck_orient = cmds.getAttr(f"{last_neck_joint}.jointOrient")[0]

            # Apply same orientation to head (for continuous chain)
            cmds.setAttr(f"{head_base_joint}.jointOrient", neck_orient[0], neck_orient[1], neck_orient[2])

            # Important: Apply the same position as original to avoid position shift
            head_pos = cmds.xform(head_base_joint, query=True, translation=True, worldSpace=True)

            # Now parent head to last neck joint
            cmds.parent(head_base_joint, last_neck_joint)

            # IMPORTANT: Zero out rotation to avoid compound twisting
            cmds.setAttr(f"{head_base_joint}.rotate", 0, 0, 0)

            # Double check position is maintained
            cmds.xform(head_base_joint, translation=head_pos, worldSpace=True)

            print(f"Connected {head_base_joint} to {last_neck_joint} with matching orientation")

            # Restore head_end
            if head_end_joint and cmds.objExists(head_end_joint):
                # Parent back to head_base
                cmds.parent(head_end_joint, head_base_joint)

                # Make sure head_end is at the exact guide position if available
                if "head_end" in self.guides:
                    guide_pos = cmds.xform(self.guides["head_end"], query=True, translation=True, worldSpace=True)
                    cmds.xform(head_end_joint, translation=guide_pos, worldSpace=True)
                else:
                    # Otherwise use the stored position
                    cmds.xform(head_end_joint, translation=head_end_pos, worldSpace=True)

                # Reset orientation
                cmds.setAttr(f"{head_end_joint}.jointOrient", 0, 0, 0)
                cmds.setAttr(f"{head_end_joint}.rotate", 0, 0, 0)

            # Now connect the controls
            self._connect_controls_to_neck(neck_module)

        except Exception as e:
            import traceback
            print(f"Error connecting head to neck: {str(e)}")
            traceback.print_exc()

            # Try to restore original hierarchy
            try:
                if 'head_parent' in locals() and head_parent:
                    if cmds.objExists(head_base_joint) and not cmds.listRelatives(head_base_joint, parent=True):
                        cmds.parent(head_base_joint, head_parent[0])

                if 'head_end_parent' in locals() and head_end_parent and head_end_joint:
                    if cmds.objExists(head_end_joint) and not cmds.listRelatives(head_end_joint, parent=True):
                        cmds.parent(head_end_joint, head_end_parent[0])
            except Exception as e2:
                print(f"Error restoring hierarchy: {str(e2)}")

    def _connect_controls_to_neck(self, neck_module):
        """Connect head controls to neck controls for proper hierarchy."""
        try:
            # Check if we have a head control
            if "head" not in self.controls:
                print("No head control found")
                return

            # Get the top neck control
            if "top_neck" not in neck_module.controls:
                print("No top_neck control found in neck module")
                return

            head_ctrl = self.controls["head"]
            head_ctrl_grp = f"{head_ctrl}_grp"
            neck_ctrl = neck_module.controls["top_neck"]

            if not cmds.objExists(head_ctrl_grp) or not cmds.objExists(neck_ctrl):
                print(f"Required controls don't exist: head_grp={head_ctrl_grp}, neck={neck_ctrl}")
                return

            # Check if already connected
            current_parent = cmds.listRelatives(head_ctrl_grp, parent=True)
            if current_parent and current_parent[0] == neck_ctrl:
                print(f"Head control {head_ctrl} already properly parented under neck control {neck_ctrl}")
                return

            # Parent the head control group under the neck control
            try:
                cmds.parent(head_ctrl_grp, neck_ctrl)
                print(f"Parented head control {head_ctrl} under neck control {neck_ctrl}")
            except Exception as e:
                print(f"Error parenting head control: {str(e)}")
        except Exception as e:
            print(f"Error in _connect_controls_to_neck: {str(e)}")

    def _create_joints_with_orientation(self):
        """Create head joints with proper hierarchy and orientation."""
        # First, clear any existing joints
        self._clear_existing_joints()

        # Get guide positions
        head_base_pos = None
        head_end_pos = None

        if "head_base" in self.guides:
            head_base_pos = cmds.xform(self.guides["head_base"], query=True, translation=True, worldSpace=True)
        else:
            print("Error: Head base guide not found")
            return

        if "head_end" in self.guides:
            head_end_pos = cmds.xform(self.guides["head_end"], query=True, translation=True, worldSpace=True)
        else:
            print("Error: Head end guide not found")
            return

        # Get up vector position for orientation
        up_vector_pos = None
        if "upv_head" in self.blade_guides:
            up_vector_pos = cmds.xform(self.blade_guides["upv_head"], query=True, translation=True, worldSpace=True)

        # Create the joints using Maya commands for maximum control
        cmds.select(clear=True)

        # Create head_base joint
        head_base_joint = cmds.joint(name=f"{self.module_id}_head_base_jnt", p=head_base_pos)
        cmds.parent(head_base_joint, self.joint_grp)
        self.joints["head_base"] = head_base_joint

        # Create head_end joint
        cmds.select(head_base_joint)
        head_end_joint = cmds.joint(name=f"{self.module_id}_head_end_jnt", p=head_end_pos)
        self.joints["head_end"] = head_end_joint

        # First do a basic orientation with standard Maya method
        cmds.joint(head_base_joint, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True,
                   zeroScaleOrient=True)

        # If we have an up vector, use it to fix the orientation more precisely
        if up_vector_pos:
            try:
                # Calculate vectors for manual orientation
                # Vector from head to head_end (primary X axis)
                aim_vector = [
                    head_end_pos[0] - head_base_pos[0],
                    head_end_pos[1] - head_base_pos[1],
                    head_end_pos[2] - head_base_pos[2]
                ]

                # Normalize aim vector
                aim_length = (aim_vector[0] ** 2 + aim_vector[1] ** 2 + aim_vector[2] ** 2) ** 0.5
                if aim_length > 0.001:
                    aim_vector = [v / aim_length for v in aim_vector]

                # Vector from head to up vector guide
                up_dir = [
                    up_vector_pos[0] - head_base_pos[0],
                    up_vector_pos[1] - head_base_pos[1],
                    up_vector_pos[2] - head_base_pos[2]
                ]

                # Make sure up vector is perpendicular to aim vector
                # Calculate dot product
                dot = (up_dir[0] * aim_vector[0] +
                       up_dir[1] * aim_vector[1] +
                       up_dir[2] * aim_vector[2])

                # Subtract the projection from up_dir
                up_dir[0] = up_dir[0] - dot * aim_vector[0]
                up_dir[1] = up_dir[1] - dot * aim_vector[1]
                up_dir[2] = up_dir[2] - dot * aim_vector[2]

                # Normalize
                up_length = (up_dir[0] ** 2 + up_dir[1] ** 2 + up_dir[2] ** 2) ** 0.5
                if up_length > 0.001:
                    up_dir = [v / up_length for v in up_dir]
                else:
                    # Default up vector if calculation fails
                    up_dir = [0, 1, 0]

                # Calculate third axis (Z) as cross product of X and Y
                # This gives us a properly orthogonal coordinate system
                cross = [
                    aim_vector[1] * up_dir[2] - aim_vector[2] * up_dir[1],
                    aim_vector[2] * up_dir[0] - aim_vector[0] * up_dir[2],
                    aim_vector[0] * up_dir[1] - aim_vector[1] * up_dir[0]
                ]

                # Create a temporary transform to help us convert this orientation to Euler angles
                temp_xform = cmds.createNode('transform', name=f"{self.module_id}_temp_orientation")

                # Set the matrix directly - construct a 4x4 matrix from our axes
                matrix = [
                    aim_vector[0], aim_vector[1], aim_vector[2], 0,
                    up_dir[0], up_dir[1], up_dir[2], 0,
                    cross[0], cross[1], cross[2], 0,
                    0, 0, 0, 1
                ]

                cmds.xform(temp_xform, matrix=matrix)

                # Get the Euler angles
                rotation = cmds.xform(temp_xform, query=True, rotation=True)

                # Temporarily unparent to set orientation
                head_end_joint_parent = cmds.listRelatives(head_end_joint, parent=True)[0]
                cmds.parent(head_end_joint, world=True)

                # Set the joint orientation (not rotation)
                cmds.setAttr(f"{head_base_joint}.jointOrient", rotation[0], rotation[1], rotation[2])
                cmds.setAttr(f"{head_base_joint}.rotate", 0, 0, 0)  # Zero out rotation

                # Reparent
                cmds.parent(head_end_joint, head_base_joint)

                # Now make sure head_end has zero orientation
                cmds.setAttr(f"{head_end_joint}.jointOrient", 0, 0, 0)
                cmds.setAttr(f"{head_end_joint}.rotate", 0, 0, 0)

                # Clean up temp node
                cmds.delete(temp_xform)

                print("Head joint creation complete with custom orientation")
            except Exception as e:
                print(f"Error applying custom orientation to head: {str(e)}")
                print("Using default orientation instead")
        else:
            print("Head joint creation complete with standard orientation")

    def _clear_existing_joints(self):
        """Clear any existing head joints before creating new ones."""
        # List of potential joint names
        joint_list = [f"{self.module_id}_head_base_jnt", f"{self.module_id}_head_end_jnt"]

        # Delete any existing joints
        for joint in joint_list:
            if cmds.objExists(joint):
                cmds.delete(joint)

        # Clear the joints dictionary
        self.joints = {}

    def _create_controls(self):
        """Create the head control."""
        # Clear any existing controls
        self._clear_existing_controls()

        # Create head control
        self._create_head_control()

    def _clear_existing_controls(self):
        """Clear any existing head controls."""
        # List of potential control names
        control_names = [f"{self.module_id}_head_ctrl"]

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

    def _create_head_control(self):
        """Create the head control."""
        if "head_base" not in self.joints:
            return

        head_joint = self.joints["head_base"]
        pos = cmds.xform(head_joint, query=True, translation=True, worldSpace=True)

        # Create circle control for head
        ctrl, ctrl_grp = create_control(
            f"{self.module_id}_head_ctrl",
            "circle",
            7.0,  # Size (larger than neck controls)
            CONTROL_COLORS["main"],  # Yellow
            normal=[1, 0, 0]  # X axis normal for proper orientation
        )

        # Position and orient to match joint
        cmds.xform(ctrl_grp, translation=pos, worldSpace=True)
        temp_constraint = cmds.orientConstraint(head_joint, ctrl_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Parent to control group
        cmds.parent(ctrl_grp, self.control_grp)

        # Store reference
        self.controls["head"] = ctrl

    def _setup_constraints(self):
        """Set up constraints between controls and joints."""
        # Head control to head joints
        if "head" in self.controls:
            if "head_base" in self.joints:
                cmds.parentConstraint(
                    self.controls["head"],
                    self.joints["head_base"],
                    maintainOffset=True
                )

            # For head_end, use point constraint only to maintain its position
            # while allowing it to follow head_base orientation
            if "head_end" in self.joints:
                # First verify that head_end is at guide position
                if "head_end" in self.guides:
                    head_end_guide_pos = cmds.xform(self.guides["head_end"], query=True, translation=True,
                                                    worldSpace=True)
                    cmds.xform(self.joints["head_end"], translation=head_end_guide_pos, worldSpace=True)

                # Now use parent constraint to maintain position and follow orientation of head_base
                cmds.parentConstraint(
                    self.joints["head_base"],
                    self.joints["head_end"],
                    maintainOffset=True
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