"""
Modular Auto-Rig System
Limb Module

This module contains the implementation of the limb rig module (arms and legs).

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import math
from autorig.core.module_base import BaseModule
from autorig.core.utils import create_guide, create_joint, create_control, CONTROL_COLORS


class LimbModule(BaseModule):
    """
    Module for creating arm or leg rigs with IK/FK capabilities.
    """

    def __init__(self, side, module_name, limb_type="arm"):
        """
        Initialize the limb module.

        Args:
            side (str): Side of the body ('l', 'r')
            module_name (str): Name of the module (usually 'arm' or 'leg')
            limb_type (str): Type of limb ('arm' or 'leg')
        """
        super().__init__(side, module_name, limb_type)
        self.limb_type = limb_type

        # Set default positions based on limb type
        self.default_positions = self._get_default_positions()

    def _get_default_positions(self):
        """
        Get default guide positions based on limb type.

        Returns:
            dict: Default guide positions
        """
        if self.limb_type == "arm":
            return {
                "shoulder": (5 if self.side == "l" else -5, 15, 0),
                "elbow": (10 if self.side == "l" else -10, 15, -2),
                "wrist": (15 if self.side == "l" else -15, 15, 0),
                "pole": (10 if self.side == "l" else -10, 15, 5),
                "hand": (16 if self.side == "l" else -16, 15, 0)
            }
        elif self.limb_type == "leg":
            return {
                "hip": (2.5 if self.side == "l" else -2.5, 10, 0),
                "knee": (3 if self.side == "l" else -3, 5, 1),
                "ankle": (3 if self.side == "l" else -3, 1, 0),
                "pole": (3 if self.side == "l" else -3, 5, 5),
                "foot": (3 if self.side == "l" else -3, 0, 3),
                "toe": (3 if self.side == "l" else -3, 0, 5),
                "heel": (3 if self.side == "l" else -3, 0, -1)
            }
        return {}

    def create_guides(self):
        """Create the limb guides."""
        self._create_module_groups()

        if self.limb_type == "arm":
            self._create_arm_guides()
        elif self.limb_type == "leg":
            self._create_leg_guides()

    def _create_arm_guides(self):
        """Create guides for an arm rig."""
        # Create shoulder guide
        pos = self.default_positions.get("shoulder", (0, 0, 0))
        self.guides["shoulder"] = create_guide(f"{self.module_id}_shoulder", pos, self.guide_grp)

        # Create elbow guide
        pos = self.default_positions.get("elbow", (0, 0, 0))
        self.guides["elbow"] = create_guide(f"{self.module_id}_elbow", pos, self.guide_grp)

        # Create wrist guide
        pos = self.default_positions.get("wrist", (0, 0, 0))
        self.guides["wrist"] = create_guide(f"{self.module_id}_wrist", pos, self.guide_grp)

        # Create pole vector guide
        pos = self.default_positions.get("pole", (0, 0, 0))
        self.guides["pole"] = create_guide(f"{self.module_id}_pole", pos, self.guide_grp)

        # Create hand guide
        pos = self.default_positions.get("hand", (0, 0, 0))
        self.guides["hand"] = create_guide(f"{self.module_id}_hand", pos, self.guide_grp)

    def _create_leg_guides(self):
        """Create guides for a leg rig."""
        # Create hip guide
        pos = self.default_positions.get("hip", (0, 0, 0))
        self.guides["hip"] = create_guide(f"{self.module_id}_hip", pos, self.guide_grp)

        # Create knee guide
        pos = self.default_positions.get("knee", (0, 0, 0))
        self.guides["knee"] = create_guide(f"{self.module_id}_knee", pos, self.guide_grp)

        # Create ankle guide
        pos = self.default_positions.get("ankle", (0, 0, 0))
        self.guides["ankle"] = create_guide(f"{self.module_id}_ankle", pos, self.guide_grp)

        # Create pole vector guide
        pos = self.default_positions.get("pole", (0, 0, 0))
        self.guides["pole"] = create_guide(f"{self.module_id}_pole", pos, self.guide_grp)

        # Create foot, toe, and heel guides
        for part in ["foot", "toe", "heel"]:
            pos = self.default_positions.get(part, (0, 0, 0))
            self.guides[part] = create_guide(f"{self.module_id}_{part}", pos, self.guide_grp)

    def build(self):
        """Build the limb rig."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        # Create joints
        self._create_joints()

        # Create IK chain
        self._create_ik_chain()

        # Create FK chain
        self._create_fk_chain()

        # Create controls
        if self.limb_type == "arm":
            self._create_arm_controls()
        elif self.limb_type == "leg":
            self._create_leg_controls()

        # Setup IK/FK blending
        self._setup_ikfk_blending()

    def _create_joints(self):
        """Create the limb joints."""
        if self.limb_type == "arm":
            self._create_arm_joints()
        elif self.limb_type == "leg":
            self._create_leg_joints()

    def _create_arm_joints(self):
        """Create the arm joints."""
        # Get guide positions
        shoulder_pos = cmds.xform(self.guides["shoulder"], query=True, translation=True, worldSpace=True)
        elbow_pos = cmds.xform(self.guides["elbow"], query=True, translation=True, worldSpace=True)
        wrist_pos = cmds.xform(self.guides["wrist"], query=True, translation=True, worldSpace=True)
        hand_pos = cmds.xform(self.guides["hand"], query=True, translation=True, worldSpace=True)

        # Create main joints
        self.joints["shoulder"] = create_joint(f"{self.module_id}_shoulder_jnt", shoulder_pos)
        cmds.parent(self.joints["shoulder"], self.joint_grp)

        self.joints["elbow"] = create_joint(f"{self.module_id}_elbow_jnt", elbow_pos, self.joints["shoulder"])
        self.joints["wrist"] = create_joint(f"{self.module_id}_wrist_jnt", wrist_pos, self.joints["elbow"])
        self.joints["hand"] = create_joint(f"{self.module_id}_hand_jnt", hand_pos, self.joints["wrist"])

        # Create duplicate joints for IK chain
        self.joints["ik_shoulder"] = cmds.duplicate(self.joints["shoulder"], name=f"{self.module_id}_shoulder_ik_jnt")[
            0]
        self.joints["ik_elbow"] = cmds.duplicate(self.joints["elbow"], name=f"{self.module_id}_elbow_ik_jnt")[0]
        self.joints["ik_wrist"] = cmds.duplicate(self.joints["wrist"], name=f"{self.module_id}_wrist_ik_jnt")[0]

        # Create duplicate joints for FK chain
        self.joints["fk_shoulder"] = cmds.duplicate(self.joints["shoulder"], name=f"{self.module_id}_shoulder_fk_jnt")[
            0]
        self.joints["fk_elbow"] = cmds.duplicate(self.joints["elbow"], name=f"{self.module_id}_elbow_fk_jnt")[0]
        self.joints["fk_wrist"] = cmds.duplicate(self.joints["wrist"], name=f"{self.module_id}_wrist_fk_jnt")[0]

        # Parent the duplicate chains properly
        for prefix in ["ik", "fk"]:
            cmds.parent(self.joints[f"{prefix}_shoulder"], self.joint_grp)

            # Clean up hierarchy
            children = cmds.listRelatives(self.joints[f"{prefix}_wrist"], children=True, type="joint")
            if children:
                cmds.delete(children)

    def _create_leg_joints(self):
        """Create the leg joints."""
        # Get guide positions
        hip_pos = cmds.xform(self.guides["hip"], query=True, translation=True, worldSpace=True)
        knee_pos = cmds.xform(self.guides["knee"], query=True, translation=True, worldSpace=True)
        ankle_pos = cmds.xform(self.guides["ankle"], query=True, translation=True, worldSpace=True)
        foot_pos = cmds.xform(self.guides["foot"], query=True, translation=True, worldSpace=True)
        toe_pos = cmds.xform(self.guides["toe"], query=True, translation=True, worldSpace=True)

        # Create main joints
        self.joints["hip"] = create_joint(f"{self.module_id}_hip_jnt", hip_pos)
        cmds.parent(self.joints["hip"], self.joint_grp)

        self.joints["knee"] = create_joint(f"{self.module_id}_knee_jnt", knee_pos, self.joints["hip"])
        self.joints["ankle"] = create_joint(f"{self.module_id}_ankle_jnt", ankle_pos, self.joints["knee"])
        self.joints["foot"] = create_joint(f"{self.module_id}_foot_jnt", foot_pos, self.joints["ankle"])
        self.joints["toe"] = create_joint(f"{self.module_id}_toe_jnt", toe_pos, self.joints["foot"])

        # Create duplicate joints for IK chain
        self.joints["ik_hip"] = cmds.duplicate(self.joints["hip"], name=f"{self.module_id}_hip_ik_jnt")[0]
        self.joints["ik_knee"] = cmds.duplicate(self.joints["knee"], name=f"{self.module_id}_knee_ik_jnt")[0]
        self.joints["ik_ankle"] = cmds.duplicate(self.joints["ankle"], name=f"{self.module_id}_ankle_ik_jnt")[0]

        # Create duplicate joints for FK chain
        self.joints["fk_hip"] = cmds.duplicate(self.joints["hip"], name=f"{self.module_id}_hip_fk_jnt")[0]
        self.joints["fk_knee"] = cmds.duplicate(self.joints["knee"], name=f"{self.module_id}_knee_fk_jnt")[0]
        self.joints["fk_ankle"] = cmds.duplicate(self.joints["ankle"], name=f"{self.module_id}_ankle_fk_jnt")[0]

        # Parent the duplicate chains properly
        for prefix in ["ik", "fk"]:
            cmds.parent(self.joints[f"{prefix}_hip"], self.joint_grp)

            # Clean up hierarchy
            children = cmds.listRelatives(self.joints[f"{prefix}_ankle"], children=True, type="joint")
            if children:
                cmds.delete(children)

    def _create_ik_chain(self):
        """Create the IK chain."""
        if self.limb_type == "arm":
            # Create IK handle
            if "ik_shoulder" in self.joints and "ik_wrist" in self.joints:
                ik_handle, ik_effector = cmds.ikHandle(
                    name=f"{self.module_id}_arm_ikh",
                    startJoint=self.joints["ik_shoulder"],
                    endEffector=self.joints["ik_wrist"],
                    solver="ikRPsolver"
                )
                self.controls["ik_handle"] = ik_handle

                # Create IK handle group
                ik_handle_grp = cmds.group(ik_handle, name=f"{self.module_id}_arm_ikh_grp")
                cmds.parent(ik_handle_grp, self.control_grp)

        elif self.limb_type == "leg":
            # Create IK handle from hip to ankle
            if "ik_hip" in self.joints and "ik_ankle" in self.joints:
                ik_handle, ik_effector = cmds.ikHandle(
                    name=f"{self.module_id}_leg_ikh",
                    startJoint=self.joints["ik_hip"],
                    endEffector=self.joints["ik_ankle"],
                    solver="ikRPsolver"
                )
                self.controls["ik_handle"] = ik_handle

                # Create IK handle group
                ik_handle_grp = cmds.group(ik_handle, name=f"{self.module_id}_leg_ikh_grp")
                cmds.parent(ik_handle_grp, self.control_grp)

            # Create foot IK handles
            if "foot" in self.joints and "toe" in self.joints:
                # Ankle to foot IK
                ankle_foot_ik, ankle_foot_eff = cmds.ikHandle(
                    name=f"{self.module_id}_ankle_foot_ikh",
                    startJoint=self.joints["ankle"],
                    endEffector=self.joints["foot"],
                    solver="ikSCsolver"
                )

                # Foot to toe IK
                foot_toe_ik, foot_toe_eff = cmds.ikHandle(
                    name=f"{self.module_id}_foot_toe_ikh",
                    startJoint=self.joints["foot"],
                    endEffector=self.joints["toe"],
                    solver="ikSCsolver"
                )

                # Group the foot IK handles
                foot_ik_grp = cmds.group([ankle_foot_ik, foot_toe_ik], name=f"{self.module_id}_foot_ik_grp")
                cmds.parent(foot_ik_grp, self.control_grp)

                self.controls["ankle_foot_ik"] = ankle_foot_ik
                self.controls["foot_toe_ik"] = foot_toe_ik

    def _create_fk_chain(self):
        """Create the FK chain (mainly just joints, controls come later)."""
        # The FK chain is just the duplicate joints, no special setup needed here
        pass

    def _create_arm_controls(self):
        """Create the arm controls."""
        # Create FK Controls
        # Shoulder FK control
        shoulder_pos = cmds.xform(self.joints["fk_shoulder"], query=True, translation=True, worldSpace=True)
        shoulder_rot = cmds.xform(self.joints["fk_shoulder"], query=True, rotation=True, worldSpace=True)
        shoulder_ctrl, shoulder_grp = create_control(
            f"{self.module_id}_shoulder_fk_ctrl",
            "circle",
            2.0,
            CONTROL_COLORS["fk"]
        )
        cmds.xform(shoulder_grp, translation=shoulder_pos, worldSpace=True)
        cmds.xform(shoulder_grp, rotation=shoulder_rot, worldSpace=True)
        cmds.parent(shoulder_grp, self.control_grp)
        self.controls["fk_shoulder"] = shoulder_ctrl

        # Elbow FK control
        elbow_pos = cmds.xform(self.joints["fk_elbow"], query=True, translation=True, worldSpace=True)
        elbow_rot = cmds.xform(self.joints["fk_elbow"], query=True, rotation=True, worldSpace=True)
        elbow_ctrl, elbow_grp = create_control(
            f"{self.module_id}_elbow_fk_ctrl",
            "circle",
            1.5,
            CONTROL_COLORS["fk"]
        )
        cmds.xform(elbow_grp, translation=elbow_pos, worldSpace=True)
        cmds.xform(elbow_grp, rotation=elbow_rot, worldSpace=True)
        cmds.parent(elbow_grp, self.controls["fk_shoulder"])
        self.controls["fk_elbow"] = elbow_ctrl

        # Wrist FK control
        wrist_pos = cmds.xform(self.joints["fk_wrist"], query=True, translation=True, worldSpace=True)
        wrist_rot = cmds.xform(self.joints["fk_wrist"], query=True, rotation=True, worldSpace=True)
        wrist_ctrl, wrist_grp = create_control(
            f"{self.module_id}_wrist_fk_ctrl",
            "circle",
            1.0,
            CONTROL_COLORS["fk"]
        )
        cmds.xform(wrist_grp, translation=wrist_pos, worldSpace=True)
        cmds.xform(wrist_grp, rotation=wrist_rot, worldSpace=True)
        cmds.parent(wrist_grp, self.controls["fk_elbow"])
        self.controls["fk_wrist"] = wrist_ctrl

        # Connect FK controls to FK joints
        cmds.parentConstraint(self.controls["fk_shoulder"], self.joints["fk_shoulder"], maintainOffset=False)
        cmds.parentConstraint(self.controls["fk_elbow"], self.joints["fk_elbow"], maintainOffset=False)
        cmds.parentConstraint(self.controls["fk_wrist"], self.joints["fk_wrist"], maintainOffset=False)

        # Create IK Controls
        # Wrist IK control
        wrist_pos = cmds.xform(self.joints["ik_wrist"], query=True, translation=True, worldSpace=True)
        wrist_ctrl, wrist_grp = create_control(
            f"{self.module_id}_wrist_ik_ctrl",
            "cube",
            1.5,
            CONTROL_COLORS["ik"]
        )
        cmds.xform(wrist_grp, translation=wrist_pos, worldSpace=True)
        cmds.parent(wrist_grp, self.control_grp)
        self.controls["ik_wrist"] = wrist_ctrl

        # Add custom attributes for IK control
        cmds.addAttr(wrist_ctrl, longName="ikFkBlend", attributeType="float", min=0, max=1, defaultValue=0,
                     keyable=True)

        # Pole vector control
        pole_pos = cmds.xform(self.guides["pole"], query=True, translation=True, worldSpace=True)
        pole_ctrl, pole_grp = create_control(
            f"{self.module_id}_pole_ctrl",
            "square",
            0.5,
            CONTROL_COLORS["ik"]
        )
        cmds.xform(pole_grp, translation=pole_pos, worldSpace=True)
        cmds.parent(pole_grp, self.control_grp)
        self.controls["pole"] = pole_ctrl

        # Connect IK controls
        cmds.pointConstraint(self.controls["ik_wrist"], self.controls["ik_handle"], maintainOffset=False)
        cmds.orientConstraint(self.controls["ik_wrist"], self.joints["ik_wrist"], maintainOffset=False)

        # Create pole vector constraint
        cmds.poleVectorConstraint(self.controls["pole"], self.controls["ik_handle"])

    def _create_leg_controls(self):
        """Create the leg controls."""
        # Create FK Controls
        # Hip FK control
        hip_pos = cmds.xform(self.joints["fk_hip"], query=True, translation=True, worldSpace=True)
        hip_rot = cmds.xform(self.joints["fk_hip"], query=True, rotation=True, worldSpace=True)
        hip_ctrl, hip_grp = create_control(
            f"{self.module_id}_hip_fk_ctrl",
            "circle",
            2.0,
            CONTROL_COLORS["fk"]
        )
        cmds.xform(hip_grp, translation=hip_pos, worldSpace=True)
        cmds.xform(hip_grp, rotation=hip_rot, worldSpace=True)
        cmds.parent(hip_grp, self.control_grp)
        self.controls["fk_hip"] = hip_ctrl

        # Knee FK control
        knee_pos = cmds.xform(self.joints["fk_knee"], query=True, translation=True, worldSpace=True)
        knee_rot = cmds.xform(self.joints["fk_knee"], query=True, rotation=True, worldSpace=True)
        knee_ctrl, knee_grp = create_control(
            f"{self.module_id}_knee_fk_ctrl",
            "circle",
            1.5,
            CONTROL_COLORS["fk"]
        )
        cmds.xform(knee_grp, translation=knee_pos, worldSpace=True)
        cmds.xform(knee_grp, rotation=knee_rot, worldSpace=True)
        cmds.parent(knee_grp, self.controls["fk_hip"])
        self.controls["fk_knee"] = knee_ctrl

        # Ankle FK control
        ankle_pos = cmds.xform(self.joints["fk_ankle"], query=True, translation=True, worldSpace=True)
        ankle_rot = cmds.xform(self.joints["fk_ankle"], query=True, rotation=True, worldSpace=True)
        ankle_ctrl, ankle_grp = create_control(
            f"{self.module_id}_ankle_fk_ctrl",
            "circle",
            1.0,
            CONTROL_COLORS["fk"]
        )
        cmds.xform(ankle_grp, translation=ankle_pos, worldSpace=True)
        cmds.xform(ankle_grp, rotation=ankle_rot, worldSpace=True)
        cmds.parent(ankle_grp, self.controls["fk_knee"])
        self.controls["fk_ankle"] = ankle_ctrl

        # Connect FK controls to FK joints
        cmds.parentConstraint(self.controls["fk_hip"], self.joints["fk_hip"], maintainOffset=False)
        cmds.parentConstraint(self.controls["fk_knee"], self.joints["fk_knee"], maintainOffset=False)
        cmds.parentConstraint(self.controls["fk_ankle"], self.joints["fk_ankle"], maintainOffset=False)

        # Create IK Controls
        # Foot IK control
        foot_pos = cmds.xform(self.guides["foot"], query=True, translation=True, worldSpace=True)
        foot_ctrl, foot_grp = create_control(
            f"{self.module_id}_foot_ik_ctrl",
            "cube",
            1.5,
            CONTROL_COLORS["ik"]
        )
        cmds.xform(foot_grp, translation=foot_pos, worldSpace=True)
        cmds.parent(foot_grp, self.control_grp)
        self.controls["ik_foot"] = foot_ctrl

        # Add custom attributes for foot control
        cmds.addAttr(foot_ctrl, longName="ikFkBlend", attributeType="float", min=0, max=1, defaultValue=0, keyable=True)
        cmds.addAttr(foot_ctrl, longName="roll", attributeType="float", defaultValue=0, keyable=True)
        cmds.addAttr(foot_ctrl, longName="tilt", attributeType="float", defaultValue=0, keyable=True)
        cmds.addAttr(foot_ctrl, longName="toe", attributeType="float", defaultValue=0, keyable=True)
        cmds.addAttr(foot_ctrl, longName="heel", attributeType="float", defaultValue=0, keyable=True)

        # Pole vector control
        pole_pos = cmds.xform(self.guides["pole"], query=True, translation=True, worldSpace=True)
        pole_ctrl, pole_grp = create_control(
            f"{self.module_id}_pole_ctrl",
            "square",
            0.5,
            CONTROL_COLORS["ik"]
        )
        cmds.xform(pole_grp, translation=pole_pos, worldSpace=True)
        cmds.parent(pole_grp, self.control_grp)
        self.controls["pole"] = pole_ctrl

        # Connect IK controls
        cmds.pointConstraint(self.controls["ik_foot"], self.controls["ik_handle"], maintainOffset=False)
        cmds.orientConstraint(self.controls["ik_foot"], self.joints["ik_ankle"], maintainOffset=False)

        # Create pole vector constraint
        cmds.poleVectorConstraint(self.controls["pole"], self.controls["ik_handle"])

        # Set up foot roll
        if "foot_toe_ik" in self.controls:
            # Create utility nodes for foot attributes
            roll_mult = cmds.createNode("multiplyDivide", name=f"{self.module_id}_roll_mult")
            toe_mult = cmds.createNode("multiplyDivide", name=f"{self.module_id}_toe_mult")

            # Connect foot roll attributes
            cmds.connectAttr(f"{foot_ctrl}.roll", f"{roll_mult}.input1X")
            cmds.connectAttr(f"{foot_ctrl}.toe", f"{toe_mult}.input1X")

            # Set multiplier values
            cmds.setAttr(f"{roll_mult}.input2X", 0.1)
            cmds.setAttr(f"{toe_mult}.input2X", 0.1)

            # Connect to foot IK rotations
            cmds.connectAttr(f"{roll_mult}.outputX", f"{self.controls['ankle_foot_ik']}.rotateX")
            cmds.connectAttr(f"{toe_mult}.outputX", f"{self.controls['foot_toe_ik']}.rotateX")

    def _setup_ikfk_blending(self):
        """Setup IK/FK blending."""
        # Create blend color nodes for each joint
        if self.limb_type == "arm":
            blend_attr = f"{self.controls['ik_wrist']}.ikFkBlend"
            joints = ["shoulder", "elbow", "wrist"]
        elif self.limb_type == "leg":
            blend_attr = f"{self.controls['ik_foot']}.ikFkBlend"
            joints = ["hip", "knee", "ankle"]

        for joint in joints:
            blend_node = cmds.createNode("blendColors", name=f"{self.module_id}_{joint}_blend")
            cmds.connectAttr(blend_attr, f"{blend_node}.blender")

            # Connect translate
            for axis in ["X", "Y", "Z"]:
                cmds.connectAttr(f"{self.joints[f'ik_{joint}']}.translate{axis}", f"{blend_node}.color1{axis}")
                cmds.connectAttr(f"{self.joints[f'fk_{joint}']}.translate{axis}", f"{blend_node}.color2{axis}")
                cmds.connectAttr(f"{blend_node}.output{axis}", f"{self.joints[joint]}.translate{axis}")

            # Connect rotate
            rotate_blend = cmds.createNode("blendColors", name=f"{self.module_id}_{joint}_rotate_blend")
            cmds.connectAttr(blend_attr, f"{rotate_blend}.blender")

            for axis in ["X", "Y", "Z"]:
                cmds.connectAttr(f"{self.joints[f'ik_{joint}']}.rotate{axis}", f"{rotate_blend}.color1{axis}")
                cmds.connectAttr(f"{self.joints[f'fk_{joint}']}.rotate{axis}", f"{rotate_blend}.color2{axis}")
                cmds.connectAttr(f"{rotate_blend}.output{axis}", f"{self.joints[joint]}.rotate{axis}")

        # Create visibility connections
        if self.limb_type == "arm":
            # Create reverse node for blend attribute
            reverse = cmds.createNode("reverse", name=f"{self.module_id}_ikfk_reverse")
            cmds.connectAttr(blend_attr, f"{reverse}.inputX")

            # Connect blend attribute to FK control visibility (visible when blender is 1/FK)
            for ctrl in ["fk_shoulder", "fk_elbow", "fk_wrist"]:
                if ctrl in self.controls:
                    cmds.connectAttr(blend_attr, f"{self.controls[ctrl]}.visibility")

            # Connect reverse of blend attribute to IK control visibility (visible when blender is 0/IK)
            for ctrl in ["ik_wrist", "pole"]:
                if ctrl in self.controls:
                    cmds.connectAttr(f"{reverse}.outputX", f"{self.controls[ctrl]}.visibility")

        elif self.limb_type == "leg":
            # Create reverse node for blend attribute
            reverse = cmds.createNode("reverse", name=f"{self.module_id}_ikfk_reverse")
            cmds.connectAttr(blend_attr, f"{reverse}.inputX")

            # Connect blend attribute to FK control visibility (visible when blender is 1/FK)
            for ctrl in ["fk_hip", "fk_knee", "fk_ankle"]:
                if ctrl in self.controls:
                    cmds.connectAttr(blend_attr, f"{self.controls[ctrl]}.visibility")

            # Connect reverse of blend attribute to IK control visibility (visible when blender is 0/IK)
            for ctrl in ["ik_foot", "pole"]:
                if ctrl in self.controls:
                    cmds.connectAttr(f"{reverse}.outputX", f"{self.controls[ctrl]}.visibility")