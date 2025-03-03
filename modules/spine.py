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

        # Create root guide
        self.guides["root"] = create_guide(f"{self.module_id}_root", (0, 0, 0), self.guide_grp)

        # Create hip guide
        self.guides["hip"] = create_guide(f"{self.module_id}_hip", (0, 10, 0), self.guide_grp)

        # Create spine guides
        step = 10.0 / (self.num_joints - 1) if self.num_joints > 1 else 0
        for i in range(self.num_joints):
            name = f"{self.module_id}_spine_{i + 1}"
            pos = (0, step * i, 0)
            self.guides[f"spine_{i + 1}"] = create_guide(name, pos, self.guide_grp)

        # Create chest guide
        self.guides["chest"] = create_guide(f"{self.module_id}_chest", (0, step * (self.num_joints - 1), 0),
                                            self.guide_grp)

    def build(self):
        """Build the spine rig."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        # Create spine joints
        self._create_spine_joints()

        # Create spine controls
        self._create_spine_controls()

        # Set up spine constraints
        self._setup_spine_constraints()

    def _create_spine_joints(self):
        """Create the spine joints."""
        # Get guide positions
        root_pos = cmds.xform(self.guides["root"], query=True, translation=True, worldSpace=True)

        # Create root joint
        self.joints["root"] = create_joint(f"{self.module_id}_root_jnt", root_pos)
        cmds.parent(self.joints["root"], self.joint_grp)

        # Create spine joints
        parent_joint = self.joints["root"]
        for i in range(self.num_joints):
            guide_name = f"spine_{i + 1}"
            if guide_name in self.guides:
                pos = cmds.xform(self.guides[guide_name], query=True, translation=True, worldSpace=True)
                joint_name = f"{self.module_id}_spine_{i + 1}_jnt"

                self.joints[guide_name] = create_joint(joint_name, pos, parent_joint)
                parent_joint = self.joints[guide_name]

        # Create chest joint
        if "chest" in self.guides:
            chest_pos = cmds.xform(self.guides["chest"], query=True, translation=True, worldSpace=True)
            self.joints["chest"] = create_joint(f"{self.module_id}_chest_jnt", chest_pos, parent_joint)

    def _create_spine_controls(self):
        """Create the spine controls."""
        # Create root control
        root_pos = cmds.xform(self.guides["root"], query=True, translation=True, worldSpace=True)
        ctrl, ctrl_grp = create_control(f"{self.module_id}_root_ctrl", "cube", 3.0, CONTROL_COLORS["main"])
        cmds.xform(ctrl_grp, translation=root_pos, worldSpace=True)
        cmds.parent(ctrl_grp, self.control_grp)
        self.controls["root"] = ctrl

        # Create hip control
        hip_pos = cmds.xform(self.guides["hip"], query=True, translation=True, worldSpace=True)
        ctrl, ctrl_grp = create_control(f"{self.module_id}_hip_ctrl", "cube", 2.5, CONTROL_COLORS["main"])
        cmds.xform(ctrl_grp, translation=hip_pos, worldSpace=True)
        cmds.parent(ctrl_grp, self.controls["root"])
        self.controls["hip"] = ctrl

        # Create chest control
        chest_pos = cmds.xform(self.guides["chest"], query=True, translation=True, worldSpace=True)
        ctrl, ctrl_grp = create_control(f"{self.module_id}_chest_ctrl", "cube", 2.5, CONTROL_COLORS["main"])
        cmds.xform(ctrl_grp, translation=chest_pos, worldSpace=True)
        cmds.parent(ctrl_grp, self.controls["hip"])
        self.controls["chest"] = ctrl

    def _setup_spine_constraints(self):
        """Set up the spine constraints."""
        # Connect root control to root joint
        cmds.parentConstraint(self.controls["root"], self.joints["root"], maintainOffset=True)

        # Connect hip control to appropriate joints
        if self.num_joints > 2:
            mid_index = self.num_joints // 2
            start_joint = self.joints[f"spine_1"]
            mid_joint = self.joints[f"spine_{mid_index}"]

            cmds.parentConstraint(self.controls["hip"], start_joint, maintainOffset=True)

            # Set up intermediate joint constraints
            for i in range(2, mid_index + 1):
                joint = self.joints[f"spine_{i}"]
                weight = (i - 1) / (mid_index - 1) if mid_index > 1 else 1

                hip_constraint = cmds.parentConstraint(self.controls["hip"], joint, maintainOffset=True)[0]
                chest_constraint = cmds.parentConstraint(self.controls["chest"], joint, maintainOffset=True)[0]

                # Set constraint weights
                cmds.setAttr(f"{hip_constraint}.{self.controls['hip']}W0", 1 - weight)
                cmds.setAttr(f"{hip_constraint}.{self.controls['chest']}W1", weight)

        # Connect chest control to chest joint
        cmds.parentConstraint(self.controls["chest"], self.joints["chest"], maintainOffset=True)