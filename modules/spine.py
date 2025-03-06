"""
Modular Auto-Rig System
Spine Module

This module contains the implementation of the spine rig module.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
from autorig.core.module_base import BaseModule
from autorig.core.utils import create_guide, create_joint, create_control, CONTROL_COLORS


class SpineModule(BaseModule):
    """
    Module for creating a spine rig.
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

    def create_guides(self):
        """Create the spine guides."""
        self._create_module_groups()

        # Create cog guide (renamed from root)
        self.guides["cog"] = create_guide(f"{self.module_id}_cog", (0, 0, 0), self.guide_grp)

        # Create pelvis guide (renamed from hip)
        self.guides["pelvis"] = create_guide(f"{self.module_id}_pelvis", (0, 10, 0), self.guide_grp)

        # Create spine guides with proper padding
        step = 10.0 / (self.num_joints - 1) if self.num_joints > 1 else 0
        for i in range(self.num_joints):
            # Use 2-digit padding for spine numbers
            name = f"{self.module_id}_spine_{i + 1:02d}"
            pos = (0, step * i, 0)
            self.guides[f"spine_{i + 1:02d}"] = create_guide(name, pos, self.guide_grp)

        # Create chest guide
        self.guides["chest"] = create_guide(f"{self.module_id}_chest", (0, step * (self.num_joints - 1), 0),
                                            self.guide_grp)

    def build(self):
        """Build the spine rig."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        # Create spine joints
        self._create_spine_joints()

        # Fix joint orientations
        self._fix_joint_orientations()

        # Create spine controls
        self._create_spine_controls()

        # Set up spine constraints
        self._setup_spine_constraints()

    def _create_spine_joints(self):
        """Create the spine joints."""
        # Get guide positions
        cog_pos = cmds.xform(self.guides["cog"], query=True, translation=True, worldSpace=True)

        # Create cog joint (renamed from root)
        self.joints["cog"] = create_joint(f"{self.module_id}_cog_jnt", cog_pos)
        cmds.parent(self.joints["cog"], self.joint_grp)

        # Create spine joints with padding
        parent_joint = self.joints["cog"]
        for i in range(self.num_joints):
            # Use 2-digit padding
            guide_name = f"spine_{i + 1:02d}"
            if guide_name in self.guides:
                pos = cmds.xform(self.guides[guide_name], query=True, translation=True, worldSpace=True)
                joint_name = f"{self.module_id}_spine_{i + 1:02d}_jnt"

                self.joints[guide_name] = create_joint(joint_name, pos, parent_joint)
                parent_joint = self.joints[guide_name]

        # Create chest joint (final joint in chain)
        if "chest" in self.guides:
            chest_pos = cmds.xform(self.guides["chest"], query=True, translation=True, worldSpace=True)
            self.joints["chest"] = create_joint(f"{self.module_id}_chest_jnt", chest_pos, parent_joint)

    def _fix_joint_orientations(self):
        """
        Fix joint orientations to ensure X points down the bone and Y points up.
        Special handling for chest joint to ensure it follows the last spine joint's orientation.
        """
        print(f"Fixing joint orientations for spine")

        # Store current selection to restore later
        current_selection = cmds.ls(selection=True)

        # First, orient the main spine chain (excluding chest)
        spine_chain = []

        # Add the cog
        if "cog" in self.joints:
            spine_chain.append(self.joints["cog"])

        # Add all spine joints in order
        for i in range(self.num_joints):
            guide_name = f"spine_{i + 1:02d}"
            if guide_name in self.joints:
                spine_chain.append(self.joints[guide_name])

        # Skip if we don't have enough joints
        if len(spine_chain) < 2:
            print(f"Not enough joints to orient in spine")
            return

        # Orient the main spine chain
        cmds.select(clear=True)
        cmds.select(spine_chain)

        cmds.joint(
            edit=True,
            orientJoint="xyz",  # Primary axis X
            secondaryAxisOrient="yup",  # Secondary axis Y up
            children=True,  # Apply to all children
            zeroScaleOrient=True  # Prevent scale from affecting orientation
        )

        # Now handle the chest joint separately
        if "chest" in self.joints and self.num_joints > 0:
            # Get the last spine joint
            last_spine_name = f"spine_{self.num_joints:02d}"
            if last_spine_name in self.joints:
                last_spine_joint = self.joints[last_spine_name]
                chest_joint = self.joints["chest"]

                # Get the orientation of the last spine joint
                last_spine_orient = cmds.getAttr(f"{last_spine_joint}.jointOrient")[0]

                # Apply this orientation to the chest joint
                cmds.setAttr(f"{chest_joint}.jointOrient", *last_spine_orient)

                print(f"Set chest joint orientation to match {last_spine_name}")

        # Zero out rotations for all joints
        all_joints = spine_chain.copy()
        if "chest" in self.joints:
            all_joints.append(self.joints["chest"])

        for joint in all_joints:
            try:
                cmds.setAttr(f"{joint}.rotateX", 0)
                cmds.setAttr(f"{joint}.rotateY", 0)
                cmds.setAttr(f"{joint}.rotateZ", 0)
            except Exception as e:
                print(f"Error zeroing rotations for {joint}: {str(e)}")

        # Restore original selection
        cmds.select(clear=True)
        if current_selection:
            cmds.select(current_selection)

        print("Spine joint orientation fix complete")

    def _create_spine_controls(self):
        """Create the spine controls with proper orientations.
        spine_01_ctrl is flat to the floor while matching orientation.
        Other controls match their joint orientations correctly.
        """
        # Set up for first control (spine_01)
        first_spine = f"spine_{1:02d}"
        first_spine_pos = cmds.xform(self.guides[first_spine], query=True, translation=True, worldSpace=True)

        # Get spine_01 joint orientation
        first_spine_jnt = self.joints[first_spine]
        joint_orient = cmds.getAttr(f"{first_spine_jnt}.jointOrient")[0]

        # Create the first spine control
        ctrl, ctrl_grp = create_control(
            f"{self.module_id}_{first_spine}_ctrl",
            "circle",
            20.0,
            CONTROL_COLORS["main"],
            normal=[1, 0, 0]
        )

        # Position at joint location
        cmds.xform(ctrl_grp, translation=first_spine_pos, worldSpace=True)

        # Apply orientation but zero out Y to keep it flat to floor
        cmds.rotate(joint_orient[0], 0, joint_orient[2], ctrl_grp, objectSpace=True)

        # Parent to control group
        cmds.parent(ctrl_grp, self.control_grp)
        self.controls[first_spine] = ctrl

        # Remember the previous control for parenting
        prev_control = ctrl

        # Create controls for remaining spine joints (2 through N)
        for i in range(2, self.num_joints + 1):
            guide_name = f"spine_{i:02d}"
            if guide_name in self.guides and guide_name in self.joints:
                # Get the joint's position
                joint = self.joints[guide_name]
                spine_pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)

                # Create control
                ctrl, ctrl_grp = create_control(
                    f"{self.module_id}_{guide_name}_ctrl",
                    "circle",
                    20.0,
                    CONTROL_COLORS["main"],
                    normal=[1, 0, 0]
                )

                # Position the control
                cmds.xform(ctrl_grp, translation=spine_pos, worldSpace=True)

                # Match to joint's world rotation
                spine_rot = cmds.xform(joint, query=True, rotation=True, worldSpace=True)
                cmds.xform(ctrl_grp, rotation=spine_rot, worldSpace=True)

                # Parent to previous control
                cmds.parent(ctrl_grp, prev_control)
                self.controls[guide_name] = ctrl
                prev_control = ctrl

        # Create chest control
        if "chest" in self.guides and "chest" in self.joints:
            # Get chest joint position
            chest_joint = self.joints["chest"]
            chest_pos = cmds.xform(chest_joint, query=True, translation=True, worldSpace=True)

            # Create chest control
            ctrl, ctrl_grp = create_control(
                f"{self.module_id}_chest_ctrl",
                "circle",
                20.5,
                CONTROL_COLORS["main"],
                normal=[1, 0, 0]
            )

            # Position the control
            cmds.xform(ctrl_grp, translation=chest_pos, worldSpace=True)

            # Match to chest joint's world rotation
            chest_rot = cmds.xform(chest_joint, query=True, rotation=True, worldSpace=True)
            cmds.xform(ctrl_grp, rotation=chest_rot, worldSpace=True)

            # Parent to last spine control
            cmds.parent(ctrl_grp, prev_control)
            self.controls["chest"] = ctrl

    def _setup_spine_constraints(self):
        """Set up the spine constraints.
        Since we no longer have controls for cog and pelvis, we'll handle those specially.
        """
        # Connect first spine control to cog and pelvis joints
        # (since they're all at the same position)
        first_spine = f"spine_{1:02d}"
        if first_spine in self.controls:
            if "cog" in self.joints:
                cmds.parentConstraint(self.controls[first_spine], self.joints["cog"], maintainOffset=True)

            # Since the first spine joint is the starting point for our controls
            # connect it to the corresponding joint
            if first_spine in self.joints:
                cmds.parentConstraint(self.controls[first_spine], self.joints[first_spine], maintainOffset=True)

        # Connect remaining spine controls to their respective joints
        for i in range(2, self.num_joints + 1):
            spine_name = f"spine_{i:02d}"
            if spine_name in self.controls and spine_name in self.joints:
                cmds.parentConstraint(self.controls[spine_name], self.joints[spine_name], maintainOffset=True)

        # Connect chest control to chest joint
        if "chest" in self.controls and "chest" in self.joints:
            cmds.parentConstraint(self.controls["chest"], self.joints["chest"], maintainOffset=True)