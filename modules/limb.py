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

    def _orient_joints(self, joint_chain):
        """
        Orient all joints properly with X down the bone, Y up.

        Args:
            joint_chain (list): List of joint names in the chain
        """
        # First, get the chain of actual joint names
        joints_to_orient = []
        for name in joint_chain:
            if name in self.joints:
                joints_to_orient.append(self.joints[name])

        if not joints_to_orient:
            return

        # Select the joints in order
        cmds.select(clear=True)
        cmds.select(joints_to_orient)

        # Orient the entire chain at once
        cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup",
                   children=True, zeroScaleOrient=True)

        # For the duplicate chains (IK and FK), orient them too
        for prefix in ["ik_", "fk_"]:
            dup_joints = []
            for name in joint_chain:
                key = f"{prefix}{name}"
                if key in self.joints:
                    dup_joints.append(self.joints[key])

            if dup_joints:
                cmds.select(clear=True)
                cmds.select(dup_joints)
                cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup",
                           children=True, zeroScaleOrient=True)

    def build(self):
        """Build the limb rig."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        print(f"Building {self.module_id} rig...")

        # Create joints
        self._create_joints()

        self._fix_joint_orientations()

        # Create IK chain
        self._create_ik_chain()

        # Create FK chain
        self._create_fk_chain()

        # Create controls
        if self.limb_type == "arm":
            self._create_arm_controls()
        elif self.limb_type == "leg":
            self._create_leg_controls()

        # Create FK/IK switch - add this call before blending
        self._create_fkik_switch()

        # Setup FK/IK blending
        self._setup_ikfk_blending()

        self._finalize_fkik_switch()

        print(f"Build complete for {self.module_id}")

    def _create_joints(self):
        """Create the limb joints."""
        if self.limb_type == "arm":
            self._create_arm_joints()
        elif self.limb_type == "leg":
            self._create_leg_joints()

    def _create_arm_joints(self):
        """Create arm joints with properly aligned orientations."""
        # First, clean up any existing joints for this module
        joint_list = [
            f"{self.module_id}_shoulder_jnt", f"{self.module_id}_elbow_jnt",
            f"{self.module_id}_wrist_jnt", f"{self.module_id}_hand_jnt",
            f"{self.module_id}_shoulder_ik_jnt", f"{self.module_id}_elbow_ik_jnt",
            f"{self.module_id}_wrist_ik_jnt", f"{self.module_id}_hand_ik_jnt",
            f"{self.module_id}_shoulder_fk_jnt", f"{self.module_id}_elbow_fk_jnt",
            f"{self.module_id}_wrist_fk_jnt", f"{self.module_id}_hand_fk_jnt"
        ]

        for joint in joint_list:
            if cmds.objExists(joint):
                cmds.delete(joint)

        # Clear the joints dictionary
        self.joints = {}

        # Get exact guide positions
        shoulder_pos = cmds.xform(self.guides["shoulder"], query=True, translation=True, worldSpace=True)
        elbow_pos = cmds.xform(self.guides["elbow"], query=True, translation=True, worldSpace=True)
        wrist_pos = cmds.xform(self.guides["wrist"], query=True, translation=True, worldSpace=True)
        hand_pos = cmds.xform(self.guides["hand"], query=True, translation=True, worldSpace=True)

        print(f"Guide positions: shoulder={shoulder_pos}, elbow={elbow_pos}, wrist={wrist_pos}, hand={hand_pos}")

        # ===== CREATE BINDING JOINT CHAIN =====
        cmds.select(clear=True)

        # Create the main joint chain
        shoulder_jnt = cmds.joint(name=f"{self.module_id}_shoulder_jnt", position=shoulder_pos)
        self.joints["shoulder"] = shoulder_jnt

        elbow_jnt = cmds.joint(name=f"{self.module_id}_elbow_jnt", position=elbow_pos)
        self.joints["elbow"] = elbow_jnt

        wrist_jnt = cmds.joint(name=f"{self.module_id}_wrist_jnt", position=wrist_pos)
        self.joints["wrist"] = wrist_jnt

        hand_jnt = cmds.joint(name=f"{self.module_id}_hand_jnt", position=hand_pos)
        self.joints["hand"] = hand_jnt

        # Orient the main joint chain
        cmds.joint(shoulder_jnt, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True,
                   zeroScaleOrient=True)

        # Parent to the joint group
        cmds.parent(shoulder_jnt, self.joint_grp)

        # ===== CREATE FK JOINT CHAIN =====
        # Create the FK joint chain manually (don't duplicate)
        cmds.select(clear=True)

        # FK shoulder
        fk_shoulder = cmds.joint(name=f"{self.module_id}_shoulder_fk_jnt", position=shoulder_pos)
        self.joints["fk_shoulder"] = fk_shoulder

        # FK elbow
        fk_elbow = cmds.joint(name=f"{self.module_id}_elbow_fk_jnt", position=elbow_pos)
        self.joints["fk_elbow"] = fk_elbow

        # FK wrist
        fk_wrist = cmds.joint(name=f"{self.module_id}_wrist_fk_jnt", position=wrist_pos)
        self.joints["fk_wrist"] = fk_wrist

        # FK hand
        fk_hand = cmds.joint(name=f"{self.module_id}_hand_fk_jnt", position=hand_pos)
        self.joints["fk_hand"] = fk_hand

        # Orient the FK joint chain
        cmds.joint(fk_shoulder, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True,
                   zeroScaleOrient=True)

        # Now parent the FK shoulder to the joint group
        cmds.parent(fk_shoulder, self.joint_grp)

        # ===== CREATE IK JOINT CHAIN =====
        # Create the IK joint chain manually (don't duplicate)
        cmds.select(clear=True)

        # IK shoulder
        ik_shoulder = cmds.joint(name=f"{self.module_id}_shoulder_ik_jnt", position=shoulder_pos)
        self.joints["ik_shoulder"] = ik_shoulder

        # IK elbow
        ik_elbow = cmds.joint(name=f"{self.module_id}_elbow_ik_jnt", position=elbow_pos)
        self.joints["ik_elbow"] = ik_elbow

        # IK wrist
        ik_wrist = cmds.joint(name=f"{self.module_id}_wrist_ik_jnt", position=wrist_pos)
        self.joints["ik_wrist"] = ik_wrist

        # IK hand
        ik_hand = cmds.joint(name=f"{self.module_id}_hand_ik_jnt", position=hand_pos)
        self.joints["ik_hand"] = ik_hand

        # Orient the IK joint chain
        cmds.joint(ik_shoulder, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True,
                   zeroScaleOrient=True)

        # Now parent the IK shoulder to the joint group
        cmds.parent(ik_shoulder, self.joint_grp)

        print(f"Created joint chains for {self.module_id}")

    def _create_leg_joints(self):
        """Create leg joints with properly aligned orientations."""
        # First, clean up any existing joints for this module
        joint_list = [
            f"{self.module_id}_hip_jnt", f"{self.module_id}_knee_jnt",
            f"{self.module_id}_ankle_jnt", f"{self.module_id}_foot_jnt", f"{self.module_id}_toe_jnt",
            f"{self.module_id}_hip_ik_jnt", f"{self.module_id}_knee_ik_jnt",
            f"{self.module_id}_ankle_ik_jnt", f"{self.module_id}_foot_ik_jnt", f"{self.module_id}_toe_ik_jnt",
            f"{self.module_id}_hip_fk_jnt", f"{self.module_id}_knee_fk_jnt",
            f"{self.module_id}_ankle_fk_jnt", f"{self.module_id}_foot_fk_jnt", f"{self.module_id}_toe_fk_jnt"
        ]

        for joint in joint_list:
            if cmds.objExists(joint):
                cmds.delete(joint)

        # Clear the joints dictionary
        self.joints = {}

        # Get exact guide positions
        hip_pos = cmds.xform(self.guides["hip"], query=True, translation=True, worldSpace=True)
        knee_pos = cmds.xform(self.guides["knee"], query=True, translation=True, worldSpace=True)
        ankle_pos = cmds.xform(self.guides["ankle"], query=True, translation=True, worldSpace=True)
        foot_pos = cmds.xform(self.guides["foot"], query=True, translation=True, worldSpace=True)
        toe_pos = cmds.xform(self.guides["toe"], query=True, translation=True, worldSpace=True)

        print(f"Guide positions: hip={hip_pos}, knee={knee_pos}, ankle={ankle_pos}, foot={foot_pos}, toe={toe_pos}")

        # ===== CREATE BINDING JOINT CHAIN =====
        cmds.select(clear=True)

        # Create the main joint chain
        hip_jnt = cmds.joint(name=f"{self.module_id}_hip_jnt", position=hip_pos)
        self.joints["hip"] = hip_jnt

        knee_jnt = cmds.joint(name=f"{self.module_id}_knee_jnt", position=knee_pos)
        self.joints["knee"] = knee_jnt

        ankle_jnt = cmds.joint(name=f"{self.module_id}_ankle_jnt", position=ankle_pos)
        self.joints["ankle"] = ankle_jnt

        foot_jnt = cmds.joint(name=f"{self.module_id}_foot_jnt", position=foot_pos)
        self.joints["foot"] = foot_jnt

        toe_jnt = cmds.joint(name=f"{self.module_id}_toe_jnt", position=toe_pos)
        self.joints["toe"] = toe_jnt

        # Orient the main joint chain
        cmds.joint(hip_jnt, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True,
                   zeroScaleOrient=True)

        # Parent to the joint group
        cmds.parent(hip_jnt, self.joint_grp)

        # ===== CREATE FK JOINT CHAIN =====
        # Create the FK joint chain manually
        cmds.select(clear=True)

        # FK hip
        fk_hip = cmds.joint(name=f"{self.module_id}_hip_fk_jnt", position=hip_pos)
        self.joints["fk_hip"] = fk_hip

        # FK knee
        fk_knee = cmds.joint(name=f"{self.module_id}_knee_fk_jnt", position=knee_pos)
        self.joints["fk_knee"] = fk_knee

        # FK ankle
        fk_ankle = cmds.joint(name=f"{self.module_id}_ankle_fk_jnt", position=ankle_pos)
        self.joints["fk_ankle"] = fk_ankle

        # FK foot
        fk_foot = cmds.joint(name=f"{self.module_id}_foot_fk_jnt", position=foot_pos)
        self.joints["fk_foot"] = fk_foot

        # FK toe
        fk_toe = cmds.joint(name=f"{self.module_id}_toe_fk_jnt", position=toe_pos)
        self.joints["fk_toe"] = fk_toe

        # Orient the FK joint chain
        cmds.joint(fk_hip, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)

        # Parent the FK hip to the joint group
        cmds.parent(fk_hip, self.joint_grp)

        # ===== CREATE IK JOINT CHAIN =====
        # Create the IK joint chain manually
        cmds.select(clear=True)

        # IK hip
        ik_hip = cmds.joint(name=f"{self.module_id}_hip_ik_jnt", position=hip_pos)
        self.joints["ik_hip"] = ik_hip

        # IK knee
        ik_knee = cmds.joint(name=f"{self.module_id}_knee_ik_jnt", position=knee_pos)
        self.joints["ik_knee"] = ik_knee

        # IK ankle
        ik_ankle = cmds.joint(name=f"{self.module_id}_ankle_ik_jnt", position=ankle_pos)
        self.joints["ik_ankle"] = ik_ankle

        # IK foot
        ik_foot = cmds.joint(name=f"{self.module_id}_foot_ik_jnt", position=foot_pos)
        self.joints["ik_foot"] = ik_foot

        # IK toe
        ik_toe = cmds.joint(name=f"{self.module_id}_toe_ik_jnt", position=toe_pos)
        self.joints["ik_toe"] = ik_toe

        # Orient the IK joint chain
        cmds.joint(ik_hip, edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)

        # Parent the IK hip to the joint group
        cmds.parent(ik_hip, self.joint_grp)

        print(f"Created joint chains for {self.module_id}")

    def _create_ik_chain(self):
        """Create IK chains for both arms and legs."""
        print(f"Creating IK chain for {self.module_id}")

        if self.limb_type == "arm":
            # Create IK handle from shoulder to wrist ONLY
            if "ik_shoulder" in self.joints and "ik_wrist" in self.joints:
                # Delete any existing IK handle
                ik_handle_name = f"{self.module_id}_arm_ikh"
                if cmds.objExists(ik_handle_name):
                    cmds.delete(ik_handle_name)

                # Create new IK handle
                ik_handle, ik_effector = cmds.ikHandle(
                    name=ik_handle_name,
                    startJoint=self.joints["ik_shoulder"],
                    endEffector=self.joints["ik_wrist"],  # Stop at wrist
                    solver="ikRPsolver"
                )
                self.controls["ik_handle"] = ik_handle

                # Create IK handle group
                ik_handle_grp_name = f"{self.module_id}_arm_ikh_grp"
                if cmds.objExists(ik_handle_grp_name):
                    cmds.delete(ik_handle_grp_name)

                ik_handle_grp = cmds.group(ik_handle, name=ik_handle_grp_name)
                cmds.parent(ik_handle_grp, self.control_grp)

                print(f"Created arm IK handle: {ik_handle}")

        elif self.limb_type == "leg":
            # Create IK handle from hip to ankle ONLY (not to foot/toe)
            if "ik_hip" in self.joints and "ik_ankle" in self.joints:
                # Delete any existing IK handle
                ik_handle_name = f"{self.module_id}_leg_ikh"
                if cmds.objExists(ik_handle_name):
                    cmds.delete(ik_handle_name)

                # Create new IK handle
                ik_handle, ik_effector = cmds.ikHandle(
                    name=ik_handle_name,
                    startJoint=self.joints["ik_hip"],
                    endEffector=self.joints["ik_ankle"],  # Stop at ankle
                    solver="ikRPsolver"
                )
                self.controls["ik_handle"] = ik_handle

                # Create IK handle group
                ik_handle_grp_name = f"{self.module_id}_leg_ikh_grp"
                if cmds.objExists(ik_handle_grp_name):
                    cmds.delete(ik_handle_grp_name)

                ik_handle_grp = cmds.group(ik_handle, name=ik_handle_grp_name)
                cmds.parent(ik_handle_grp, self.control_grp)

                print(f"Created leg IK handle: {ik_handle}")

                # Create foot roll system - ankle to foot and foot to toe
                if "ik_ankle" in self.joints and "ik_foot" in self.joints and "ik_toe" in self.joints:
                    print(f"Creating foot roll system for {self.module_id}")

                    # Delete any existing foot IK handles
                    ankle_foot_ik_name = f"{self.module_id}_ankle_foot_ikh"
                    foot_toe_ik_name = f"{self.module_id}_foot_toe_ikh"
                    foot_roll_grp_name = f"{self.module_id}_foot_roll_grp"

                    for name in [ankle_foot_ik_name, foot_toe_ik_name, foot_roll_grp_name]:
                        if cmds.objExists(name):
                            cmds.delete(name)

                    # Create ankle to foot IK handle
                    ankle_foot_ik, ankle_foot_eff = cmds.ikHandle(
                        name=ankle_foot_ik_name,
                        startJoint=self.joints["ik_ankle"],
                        endEffector=self.joints["ik_foot"],
                        solver="ikSCsolver"
                    )

                    # Create foot to toe IK handle
                    foot_toe_ik, foot_toe_eff = cmds.ikHandle(
                        name=foot_toe_ik_name,
                        startJoint=self.joints["ik_foot"],
                        endEffector=self.joints["ik_toe"],
                        solver="ikSCsolver"
                    )

                    # Get position data for reverse foot setup
                    ankle_pos = cmds.xform(self.joints["ik_ankle"], query=True, translation=True, worldSpace=True)
                    foot_pos = cmds.xform(self.joints["ik_foot"], query=True, translation=True, worldSpace=True)
                    toe_pos = cmds.xform(self.joints["ik_toe"], query=True, translation=True, worldSpace=True)

                    # Get heel position - it's a guide
                    heel_pos = cmds.xform(self.guides["heel"], query=True, translation=True, worldSpace=True)

                    # First, create a main foot roll group to contain everything
                    foot_roll_grp = cmds.group(empty=True, name=foot_roll_grp_name)
                    cmds.xform(foot_roll_grp, translation=[0, 0, 0], worldSpace=True)
                    cmds.parent(foot_roll_grp, self.control_grp)  # Parent to control group

                    # Create reverse foot groups hierarchy
                    heel_grp = cmds.group(empty=True, name=f"{self.module_id}_heel_pivot_grp")
                    cmds.xform(heel_grp, translation=heel_pos, worldSpace=True)
                    cmds.parent(heel_grp, foot_roll_grp)  # Parent to foot roll group

                    toe_grp = cmds.group(empty=True, name=f"{self.module_id}_toe_pivot_grp")
                    cmds.xform(toe_grp, translation=toe_pos, worldSpace=True)
                    cmds.parent(toe_grp, heel_grp)

                    ball_grp = cmds.group(empty=True, name=f"{self.module_id}_ball_pivot_grp")
                    cmds.xform(ball_grp, translation=foot_pos, worldSpace=True)
                    cmds.parent(ball_grp, toe_grp)

                    ankle_grp = cmds.group(empty=True, name=f"{self.module_id}_ankle_pivot_grp")
                    cmds.xform(ankle_grp, translation=ankle_pos, worldSpace=True)
                    cmds.parent(ankle_grp, ball_grp)

                    # Parent IK handles to appropriate groups
                    cmds.parent(foot_toe_ik, ball_grp)
                    cmds.parent(ankle_foot_ik, ankle_grp)

                    # Parent main leg IK handle to ankle group
                    cmds.parent(ik_handle, ankle_grp)

                    # Store references to the pivot groups
                    self.controls["foot_roll_grp"] = foot_roll_grp
                    self.controls["heel_pivot"] = heel_grp
                    self.controls["toe_pivot"] = toe_grp
                    self.controls["ball_pivot"] = ball_grp
                    self.controls["ankle_pivot"] = ankle_grp

                    # Store the foot IK handles
                    self.controls["ankle_foot_ik"] = ankle_foot_ik
                    self.controls["foot_toe_ik"] = foot_toe_ik

                    print(f"Created reverse foot pivot system for {self.module_id}")

    def _create_fk_chain(self):
        """Create the FK chain (mainly just joints, controls come later)."""
        # The FK chain is just the duplicate joints, no special setup needed here
        pass

    def _create_arm_controls(self):
        """Create the arm controls with properly oriented shapes and larger sizes."""
        print(f"Creating arm controls for {self.module_id}")

        # Clear any existing controls
        control_names = [
            f"{self.module_id}_shoulder_fk_ctrl", f"{self.module_id}_elbow_fk_ctrl", f"{self.module_id}_wrist_fk_ctrl",
            f"{self.module_id}_wrist_ik_ctrl", f"{self.module_id}_pole_ctrl"
        ]
        for control in control_names:
            if cmds.objExists(control):
                cmds.delete(control)

        # Store IK handle for later use
        ik_handle = self.controls.get("ik_handle", None)
        self.controls = {}
        if ik_handle:
            self.controls["ik_handle"] = ik_handle

        # === FK CONTROLS - WITH LARGER SIZES ===
        # Shoulder FK control - IMPORTANT: Create with normal=[1,0,0] to make circles face down X axis
        shoulder_jnt = self.joints["fk_shoulder"]
        shoulder_pos = cmds.xform(shoulder_jnt, query=True, translation=True, worldSpace=True)
        shoulder_rot = cmds.xform(shoulder_jnt, query=True, rotation=True, worldSpace=True)

        # Create the control with X axis normal
        shoulder_ctrl, shoulder_grp = create_control(
            f"{self.module_id}_shoulder_fk_ctrl",
            "circle",
            7.0,  # Larger size
            CONTROL_COLORS["fk"],
            normal=[1, 0, 0]  # This makes the circle face along X axis
        )

        # Position the control
        cmds.xform(shoulder_grp, translation=shoulder_pos, worldSpace=True)
        cmds.xform(shoulder_grp, rotation=shoulder_rot, worldSpace=True)

        cmds.parent(shoulder_grp, self.control_grp)
        self.controls["fk_shoulder"] = shoulder_ctrl

        # Elbow FK control
        elbow_jnt = self.joints["fk_elbow"]
        elbow_pos = cmds.xform(elbow_jnt, query=True, translation=True, worldSpace=True)
        elbow_rot = cmds.xform(elbow_jnt, query=True, rotation=True, worldSpace=True)

        elbow_ctrl, elbow_grp = create_control(
            f"{self.module_id}_elbow_fk_ctrl",
            "circle",
            7.0,  # Larger size
            CONTROL_COLORS["fk"],
            normal=[1, 0, 0]  # This makes the circle face along X axis
        )

        # Position the control
        cmds.xform(elbow_grp, translation=elbow_pos, worldSpace=True)
        cmds.xform(elbow_grp, rotation=elbow_rot, worldSpace=True)

        cmds.parent(elbow_grp, self.controls["fk_shoulder"])
        self.controls["fk_elbow"] = elbow_ctrl

        # Wrist FK control
        wrist_jnt = self.joints["fk_wrist"]
        wrist_pos = cmds.xform(wrist_jnt, query=True, translation=True, worldSpace=True)
        wrist_rot = cmds.xform(wrist_jnt, query=True, rotation=True, worldSpace=True)

        wrist_ctrl, wrist_grp = create_control(
            f"{self.module_id}_wrist_fk_ctrl",
            "circle",
            6.0,  # Larger size
            CONTROL_COLORS["fk"],
            normal=[1, 0, 0]  # This makes the circle face along X axis
        )

        # Position the control
        cmds.xform(wrist_grp, translation=wrist_pos, worldSpace=True)
        cmds.xform(wrist_grp, rotation=wrist_rot, worldSpace=True)

        cmds.parent(wrist_grp, self.controls["fk_elbow"])
        self.controls["fk_wrist"] = wrist_ctrl

        # Connect FK controls to FK joints
        for ctrl, jnt in [
            ("fk_shoulder", "fk_shoulder"),
            ("fk_elbow", "fk_elbow"),
            ("fk_wrist", "fk_wrist")
        ]:
            cmds.orientConstraint(self.controls[ctrl], self.joints[jnt], maintainOffset=True)
            cmds.pointConstraint(self.controls[ctrl], self.joints[jnt], maintainOffset=True)

        # === IK CONTROLS ===
        # Wrist IK control
        wrist_ik_jnt = self.joints["ik_wrist"]
        wrist_ik_pos = cmds.xform(wrist_ik_jnt, query=True, translation=True, worldSpace=True)

        wrist_ik_ctrl, wrist_ik_grp = create_control(
            f"{self.module_id}_wrist_ik_ctrl",
            "cube",
            3.5,  # Larger size
            CONTROL_COLORS["ik"]
        )

        # Position the control
        cmds.xform(wrist_ik_grp, translation=wrist_ik_pos, worldSpace=True)
        cmds.parent(wrist_ik_grp, self.control_grp)
        self.controls["ik_wrist"] = wrist_ik_ctrl

        # Pole vector control - use sphere
        pole_pos = cmds.xform(self.guides["pole"], query=True, translation=True, worldSpace=True)

        pole_ctrl, pole_grp = create_control(
            f"{self.module_id}_pole_ctrl",
            "sphere",  # Sphere shape
            2.5,  # Larger size
            CONTROL_COLORS["ik"]
        )

        # Position the control
        cmds.xform(pole_grp, translation=pole_pos, worldSpace=True)
        cmds.parent(pole_grp, self.control_grp)
        self.controls["pole"] = pole_ctrl

        # Connect IK controls to the IK handle
        if "ik_handle" in self.controls:
            ik_handle = self.controls["ik_handle"]

            # Clear any existing constraints
            constraints = cmds.listConnections(ik_handle, source=True, destination=True, type="constraint") or []
            for constraint in constraints:
                if cmds.objExists(constraint):
                    cmds.delete(constraint)

            # Point constrain IK handle to wrist control (position only)
            cmds.pointConstraint(self.controls["ik_wrist"], ik_handle, maintainOffset=True)

            # Add pole vector constraint
            cmds.poleVectorConstraint(self.controls["pole"], ik_handle)

        # Orient constraint for IK wrist - controls rotation independent of IK handle
        cmds.orientConstraint(self.controls["ik_wrist"], self.joints["ik_wrist"], maintainOffset=True)

        # Connect IK hand - make it follow the IK wrist joint explicitly
        cmds.parentConstraint(self.joints["ik_wrist"], self.joints["ik_hand"], maintainOffset=True)

        print("Arm controls creation complete")

    def _create_leg_controls(self):
        """Create the leg controls with properly oriented shapes and larger sizes."""
        print(f"Creating leg controls for {self.module_id}")

        # Clear any existing controls
        control_names = [
            f"{self.module_id}_hip_fk_ctrl", f"{self.module_id}_knee_fk_ctrl", f"{self.module_id}_ankle_fk_ctrl",
            f"{self.module_id}_ankle_ik_ctrl", f"{self.module_id}_pole_ctrl"
        ]
        for control in control_names:
            if cmds.objExists(control):
                cmds.delete(control)

        # Store IK handle for later use
        ik_handle = self.controls.get("ik_handle", None)
        ankle_foot_ik = self.controls.get("ankle_foot_ik", None)
        foot_toe_ik = self.controls.get("foot_toe_ik", None)

        # Store foot roll groups for later use
        foot_roll_grp = self.controls.get("foot_roll_grp", None)
        heel_pivot = self.controls.get("heel_pivot", None)
        toe_pivot = self.controls.get("toe_pivot", None)
        ball_pivot = self.controls.get("ball_pivot", None)
        ankle_pivot = self.controls.get("ankle_pivot", None)

        self.controls = {}

        # Restore IK handles
        if ik_handle:
            self.controls["ik_handle"] = ik_handle
        if ankle_foot_ik:
            self.controls["ankle_foot_ik"] = ankle_foot_ik
        if foot_toe_ik:
            self.controls["foot_toe_ik"] = foot_toe_ik

        # Restore foot roll groups
        if foot_roll_grp:
            self.controls["foot_roll_grp"] = foot_roll_grp
        if heel_pivot:
            self.controls["heel_pivot"] = heel_pivot
        if toe_pivot:
            self.controls["toe_pivot"] = toe_pivot
        if ball_pivot:
            self.controls["ball_pivot"] = ball_pivot
        if ankle_pivot:
            self.controls["ankle_pivot"] = ankle_pivot

        # === FK CONTROLS - WITH LARGER SIZES ===
        # Hip FK control
        hip_jnt = self.joints["fk_hip"]
        hip_pos = cmds.xform(hip_jnt, query=True, translation=True, worldSpace=True)
        hip_rot = cmds.xform(hip_jnt, query=True, rotation=True, worldSpace=True)

        # Create the control with X axis normal - same approach as arm FK controls
        hip_ctrl, hip_grp = create_control(
            f"{self.module_id}_hip_fk_ctrl",
            "circle",
            5.0,  # Larger size
            CONTROL_COLORS["fk"],
            normal=[1, 0, 0]  # This makes the circle face along X axis
        )

        # Position the control
        cmds.xform(hip_grp, translation=hip_pos, worldSpace=True)
        cmds.xform(hip_grp, rotation=hip_rot, worldSpace=True)

        cmds.parent(hip_grp, self.control_grp)
        self.controls["fk_hip"] = hip_ctrl

        # Knee FK control
        knee_jnt = self.joints["fk_knee"]
        knee_pos = cmds.xform(knee_jnt, query=True, translation=True, worldSpace=True)
        knee_rot = cmds.xform(knee_jnt, query=True, rotation=True, worldSpace=True)

        knee_ctrl, knee_grp = create_control(
            f"{self.module_id}_knee_fk_ctrl",
            "circle",
            4.0,  # Larger size
            CONTROL_COLORS["fk"],
            normal=[1, 0, 0]  # This makes the circle face along X axis
        )

        # Position the control
        cmds.xform(knee_grp, translation=knee_pos, worldSpace=True)
        cmds.xform(knee_grp, rotation=knee_rot, worldSpace=True)

        cmds.parent(knee_grp, self.controls["fk_hip"])
        self.controls["fk_knee"] = knee_ctrl

        # Ankle FK control
        ankle_jnt = self.joints["fk_ankle"]
        ankle_pos = cmds.xform(ankle_jnt, query=True, translation=True, worldSpace=True)
        ankle_rot = cmds.xform(ankle_jnt, query=True, rotation=True, worldSpace=True)

        ankle_ctrl, ankle_grp = create_control(
            f"{self.module_id}_ankle_fk_ctrl",
            "circle",
            3.0,  # Larger size
            CONTROL_COLORS["fk"],
            normal=[1, 0, 0]  # This makes the circle face along X axis
        )

        # Position the control
        cmds.xform(ankle_grp, translation=ankle_pos, worldSpace=True)
        cmds.xform(ankle_grp, rotation=ankle_rot, worldSpace=True)

        cmds.parent(ankle_grp, self.controls["fk_knee"])
        self.controls["fk_ankle"] = ankle_ctrl

        # Connect FK controls to FK joints
        for ctrl, jnt in [
            ("fk_hip", "fk_hip"),
            ("fk_knee", "fk_knee"),
            ("fk_ankle", "fk_ankle")
        ]:
            cmds.orientConstraint(self.controls[ctrl], self.joints[jnt], maintainOffset=True)
            cmds.pointConstraint(self.controls[ctrl], self.joints[jnt], maintainOffset=True)

        # Connect FK foot and toe to follow the FK ankle
        for jnt in ["fk_foot", "fk_toe"]:
            if jnt in self.joints:
                cmds.parentConstraint(self.controls["fk_ankle"], self.joints[jnt], maintainOffset=True)

        # === IK CONTROLS ===
        # IK ankle control (not foot!) - relocated to ankle position
        ankle_ik_jnt = self.joints["ik_ankle"]
        ankle_ik_pos = cmds.xform(ankle_ik_jnt, query=True, translation=True, worldSpace=True)

        ankle_ik_ctrl, ankle_ik_grp = create_control(
            f"{self.module_id}_ankle_ik_ctrl",
            "cube",
            3.5,  # Larger size
            CONTROL_COLORS["ik"]
        )

        # Position the control
        cmds.xform(ankle_ik_grp, translation=ankle_ik_pos, worldSpace=True)
        cmds.parent(ankle_ik_grp, self.control_grp)
        self.controls["ik_ankle"] = ankle_ik_ctrl

        # Add foot attributes
        for attr_name in ["roll", "tilt", "toe", "heel"]:
            if not cmds.attributeQuery(attr_name, node=ankle_ik_ctrl, exists=True):
                cmds.addAttr(ankle_ik_ctrl, longName=attr_name, attributeType="float", defaultValue=0, keyable=True)

        # Pole vector control - use sphere instead of square
        pole_pos = cmds.xform(self.guides["pole"], query=True, translation=True, worldSpace=True)

        pole_ctrl, pole_grp = create_control(
            f"{self.module_id}_pole_ctrl",
            "sphere",  # Changed to sphere
            2.5,  # Larger size
            CONTROL_COLORS["ik"]
        )

        # Position the control
        cmds.xform(pole_grp, translation=pole_pos, worldSpace=True)
        cmds.parent(pole_grp, self.control_grp)
        self.controls["pole"] = pole_ctrl

        # Connect IK controls to IK handle
        if "ik_handle" in self.controls:
            ik_handle = self.controls["ik_handle"]

            # Clear any existing constraints
            constraints = cmds.listConnections(ik_handle, source=True, destination=True, type="constraint") or []
            for constraint in constraints:
                if cmds.objExists(constraint):
                    cmds.delete(constraint)

            # Connect pole vector constraint
            cmds.poleVectorConstraint(self.controls["pole"], ik_handle)

        # Set up foot roll - using the pivot groups created in _create_ik_chain
        if all(key in self.controls for key in ["heel_pivot", "toe_pivot", "ball_pivot", "ankle_pivot"]):
            print(f"Setting up foot roll connections for {self.module_id}")

            # Create utility nodes for foot attributes
            roll_cond = cmds.createNode("condition", name=f"{self.module_id}_roll_condition")

            # Roll: +value = ball pivot (toe up), -value = heel pivot (heel up)
            cmds.setAttr(f"{roll_cond}.operation", 2)  # Greater than
            cmds.setAttr(f"{roll_cond}.colorIfFalseR", 0)
            cmds.setAttr(f"{roll_cond}.secondTerm", 0)

            # Toe pivot
            toe_mult = cmds.createNode("multiplyDivide", name=f"{self.module_id}_toe_mult")

            # Tilt: side-to-side rotation
            tilt_mult = cmds.createNode("multiplyDivide", name=f"{self.module_id}_tilt_mult")

            # Connect attributes
            # Roll - for positive values (toe up)
            cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{roll_cond}.firstTerm")
            cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{roll_cond}.colorIfTrueR")
            cmds.connectAttr(f"{roll_cond}.outColorR", f"{self.controls['ball_pivot']}.rotateX")

            # Roll - for negative values (heel up)
            neg_roll = cmds.createNode("multiplyDivide", name=f"{self.module_id}_neg_roll_mult")
            cmds.setAttr(f"{neg_roll}.input2X", -1)  # Negate the value
            cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{neg_roll}.input1X")

            heel_cond = cmds.createNode("condition", name=f"{self.module_id}_heel_condition")
            cmds.setAttr(f"{heel_cond}.operation", 4)  # Less than
            cmds.setAttr(f"{heel_cond}.colorIfFalseR", 0)
            cmds.setAttr(f"{heel_cond}.secondTerm", 0)
            cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{heel_cond}.firstTerm")
            cmds.connectAttr(f"{neg_roll}.outputX", f"{heel_cond}.colorIfTrueR")
            cmds.connectAttr(f"{heel_cond}.outColorR", f"{self.controls['heel_pivot']}.rotateX")

            # Toe
            cmds.connectAttr(f"{ankle_ik_ctrl}.toe", f"{toe_mult}.input1X")
            cmds.setAttr(f"{toe_mult}.input2X", 1.0)  # Full strength
            cmds.connectAttr(f"{toe_mult}.outputX", f"{self.controls['toe_pivot']}.rotateX")

            # Tilt - side-to-side
            cmds.connectAttr(f"{ankle_ik_ctrl}.tilt", f"{tilt_mult}.input1Z")
            cmds.setAttr(f"{tilt_mult}.input2Z", 1.0)  # Full strength
            cmds.connectAttr(f"{tilt_mult}.outputZ", f"{self.controls['ball_pivot']}.rotateZ")

            # Heel
            heel_mult = cmds.createNode("multiplyDivide", name=f"{self.module_id}_heel_mult")
            cmds.connectAttr(f"{ankle_ik_ctrl}.heel", f"{heel_mult}.input1Y")
            cmds.setAttr(f"{heel_mult}.input2Y", 1.0)  # Full strength
            cmds.connectAttr(f"{heel_mult}.outputY", f"{self.controls['heel_pivot']}.rotateY")

            print(f"Set up foot roll controls for {self.module_id}")
        else:
            print(f"WARNING: Missing foot pivot groups for {self.module_id} - foot roll will not work")

        # Orient constraint for IK ankle
        cmds.orientConstraint(self.controls["ik_ankle"], self.joints["ik_ankle"], maintainOffset=True)

        print("Leg controls creation complete")

    def _setup_ikfk_blending(self):
        """
        Set up FK/IK blending for the limb.
        Uses 0=FK, 1=IK logic with dedicated switch control.
        """
        print(f"Setting up FK/IK blending for {self.module_id}")

        # Determine which joints to blend based on limb type
        if self.limb_type == "arm":
            joint_pairs = [
                ("shoulder", "ik_shoulder", "fk_shoulder"),
                ("elbow", "ik_elbow", "fk_elbow"),
                ("wrist", "ik_wrist", "fk_wrist"),
                ("hand", "ik_hand", "fk_hand")
            ]
        else:  # leg
            joint_pairs = [
                ("hip", "ik_hip", "fk_hip"),
                ("knee", "ik_knee", "fk_knee"),
                ("ankle", "ik_ankle", "fk_ankle"),
                ("foot", "ik_foot", "fk_foot"),
                ("toe", "ik_toe", "fk_toe")
            ]

        # First, remove any existing constraints on binding joints
        for bind_joint, _, _ in joint_pairs:
            if bind_joint not in self.joints:
                continue

            joint = self.joints[bind_joint]
            constraints = cmds.listConnections(joint, source=True, destination=True, type="constraint") or []
            for constraint in constraints:
                if cmds.objExists(constraint):
                    cmds.delete(constraint)

        # Get the FK/IK switch control
        switch_ctrl = self.controls.get("fkik_switch")
        if not switch_ctrl:
            print(f"Warning: No FK/IK switch control found for {self.module_id}")
            return

        # Create a reverse node for the switch
        reverse_node = cmds.createNode("reverse", name=f"{self.module_id}_fkik_reverse")
        cmds.connectAttr(f"{switch_ctrl}.FkIkBlend", f"{reverse_node}.inputX")

        # Set up constraints for each joint
        for bind_joint, ik_joint, fk_joint in joint_pairs:
            if bind_joint not in self.joints or ik_joint not in self.joints or fk_joint not in self.joints:
                print(f"Warning: Missing joint for {bind_joint} blending")
                continue

            # Create the constraint - use parent constraint to match both position and rotation
            constraint = cmds.parentConstraint(
                self.joints[ik_joint],
                self.joints[fk_joint],
                self.joints[bind_joint],
                maintainOffset=True
            )[0]

            # Get weight attribute names
            weights = cmds.parentConstraint(constraint, query=True, weightAliasList=True)
            if len(weights) != 2:
                print(f"Warning: Expected 2 weights for {constraint}, got {len(weights)}")
                continue

            # Connect weights properly:
            # - For IK weight (index 0): Connect directly to the FkIkBlend attribute
            cmds.connectAttr(f"{switch_ctrl}.FkIkBlend", f"{constraint}.{weights[0]}")

            # - For FK weight (index 1): Connect to the reverse node output
            cmds.connectAttr(f"{reverse_node}.outputX", f"{constraint}.{weights[1]}")

        # Set up visibility control for FK and IK controls
        # Define all control groups to toggle visibility
        if self.limb_type == "arm":
            fk_controls = ["fk_shoulder", "fk_elbow", "fk_wrist"]
            ik_controls = ["ik_wrist", "pole"]
        else:  # leg
            fk_controls = ["fk_hip", "fk_knee", "fk_ankle"]
            ik_controls = ["ik_ankle", "pole"]

        # FK controls visible when FkIkBlend is 0 (reverse output is 1)
        for ctrl_name in fk_controls:
            if ctrl_name in self.controls:
                # Disconnect any existing connections to visibility
                connections = cmds.listConnections(f"{self.controls[ctrl_name]}.visibility",
                                                   source=True, destination=False, plugs=True) or []
                for connection in connections:
                    cmds.disconnectAttr(connection, f"{self.controls[ctrl_name]}.visibility")

                # Make sure visibility is on
                cmds.setAttr(f"{self.controls[ctrl_name]}.visibility", 1)

                # Connect reverse node to visibility (so 0 blend = visible FK)
                cmds.connectAttr(f"{reverse_node}.outputX", f"{self.controls[ctrl_name]}.visibility")

        # IK controls visible when FkIkBlend is 1 (direct connection)
        for ctrl_name in ik_controls:
            if ctrl_name in self.controls:
                # Disconnect any existing connections to visibility
                connections = cmds.listConnections(f"{self.controls[ctrl_name]}.visibility",
                                                   source=True, destination=False, plugs=True) or []
                for connection in connections:
                    cmds.disconnectAttr(connection, f"{self.controls[ctrl_name]}.visibility")

                # Make sure visibility is on
                cmds.setAttr(f"{self.controls[ctrl_name]}.visibility", 0)  # Start invisible

                # Connect switch directly to visibility (so 1 blend = visible IK)
                cmds.connectAttr(f"{switch_ctrl}.FkIkBlend", f"{self.controls[ctrl_name]}.visibility")

        # Hide IK and FK joints (keep only the binding joints visible)
        for prefix in ["ik_", "fk_"]:
            for joint_name in [pair[0] for pair in joint_pairs]:
                joint_key = f"{prefix}{joint_name}"
                if joint_key in self.joints:
                    cmds.setAttr(f"{self.joints[joint_key]}.visibility", 0)

        print("FK/IK blending setup complete")

    def _match_joint_orientations(self):
        """
        Copy joint orientations from main chain to IK and FK chains.
        This ensures all three chains have identical orientations.
        """
        print(f"Matching joint orientations for {self.module_id}")

        if self.limb_type == "arm":
            joint_list = ["shoulder", "elbow", "wrist", "hand"]
        elif self.limb_type == "leg":
            joint_list = ["hip", "knee", "ankle", "foot", "toe"]
        else:
            return

        # Get orientations from main chain and apply to IK and FK chains
        for joint in joint_list:
            if joint not in self.joints:
                continue

            # Get the main joint's orientation
            try:
                joint_orient = cmds.getAttr(f"{self.joints[joint]}.jointOrient")[0]
                joint_rot = cmds.getAttr(f"{self.joints[joint]}.rotate")[0]
                print(f"Main joint {joint} orientation: {joint_orient}")

                # Apply to IK joint
                ik_joint = f"ik_{joint}"
                if ik_joint in self.joints:
                    cmds.setAttr(f"{self.joints[ik_joint]}.jointOrient", *joint_orient)
                    cmds.setAttr(f"{self.joints[ik_joint]}.rotate", *joint_rot)
                    print(f"Applied to IK joint: {self.joints[ik_joint]}")

                # Apply to FK joint
                fk_joint = f"fk_{joint}"
                if fk_joint in self.joints:
                    cmds.setAttr(f"{self.joints[fk_joint]}.jointOrient", *joint_orient)
                    cmds.setAttr(f"{self.joints[fk_joint]}.rotate", *joint_rot)
                    print(f"Applied to FK joint: {self.joints[fk_joint]}")

            except Exception as e:
                print(f"Error matching orientation for {joint}: {str(e)}")

        print("Joint orientation matching complete")

    def _create_fkik_switch(self):
        """Create a dedicated FK/IK switch control that follows the binding joint."""
        print(f"Creating FK/IK switch for {self.module_id}")

        # Determine joint to follow based on limb type
        if self.limb_type == "arm":
            joint_to_follow = "wrist"
        else:  # leg
            joint_to_follow = "ankle"

        if joint_to_follow not in self.joints:
            print(f"Warning: '{joint_to_follow}' joint not found for FKIK switch")
            return None

        # Store the actual joint to follow
        follow_joint = self.joints[joint_to_follow]
        print(f"Using joint '{follow_joint}' for FKIK switch to follow")

        # Get position for placement
        joint_pos = cmds.xform(follow_joint, query=True, translation=True, worldSpace=True)

        # Create square control with Z-up normal for proper orientation
        # This makes the square face the Z axis by default
        square_points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (-1, 0, -1)]
        switch_ctrl = cmds.curve(
            name=f"{self.module_id}_fkik_switch",
            p=[(p[0] * 1.5, p[1] * 1.5, p[2] * 1.5) for p in square_points],
            degree=1
        )

        # Apply color (yellow)
        shapes = cmds.listRelatives(switch_ctrl, shapes=True)
        for shape in shapes:
            cmds.setAttr(f"{shape}.overrideEnabled", 1)
            cmds.setAttr(f"{shape}.overrideRGBColors", 1)
            cmds.setAttr(f"{shape}.overrideColorR", 1.0)
            cmds.setAttr(f"{shape}.overrideColorG", 1.0)
            cmds.setAttr(f"{shape}.overrideColorB", 0.0)

        # Create group
        switch_grp = cmds.group(switch_ctrl, name=f"{switch_ctrl}_grp")

        # Position the switch
        if self.limb_type == "arm":
            # For arms, position above the wrist
            offset = [0, 5.0, 0]  # Positive Y offset
        else:  # leg
            # For legs, position to the side of the ankle
            if self.side == "l":
                offset = [5.0, 0, 0]  # Positive X offset for left leg
            else:
                offset = [-5.0, 0, 0]  # Negative X offset for right leg

        switch_pos = [
            joint_pos[0] + offset[0],
            joint_pos[1] + offset[1],
            joint_pos[2] + offset[2]
        ]

        cmds.xform(switch_grp, translation=switch_pos, worldSpace=True)

        # Rotate the control to face forward (positive Z)
        # We need to rotate it 90 degrees around X
        cmds.xform(switch_grp, rotation=[90, 0, 0], relative=True)

        cmds.parent(switch_grp, self.control_grp)

        # Add the FK/IK blend attribute (0=FK, 1=IK)
        if not cmds.attributeQuery("FkIkBlend", node=switch_ctrl, exists=True):
            cmds.addAttr(switch_ctrl, longName="FkIkBlend", attributeType="float",
                         min=0, max=1, defaultValue=1, keyable=True)  # Default to IK

        # Store the switch control
        self.controls["fkik_switch"] = switch_ctrl

        # IMPORTANT: Make the switch follow the main binding joint
        # First, check if there are any existing constraints and delete them
        constraints = cmds.listConnections(switch_grp, source=True, destination=True, type="constraint") or []
        for constraint in constraints:
            if cmds.objExists(constraint):
                print(f"Deleting existing constraint: {constraint}")
                cmds.delete(constraint)

        # Create a point constraint explicitly using the joint object, not the dictionary key
        # This ensures the constraint is created even if there are lookup issues
        print(f"Creating point constraint from {follow_joint} to {switch_grp}")
        try:
            follow_constraint = cmds.pointConstraint(
                follow_joint,  # Use the actual joint object
                switch_grp,  # The switch group to be constrained
                maintainOffset=True,
                name=f"{switch_grp}_pointConstraint"
            )[0]

            # Verify the constraint was created
            if cmds.objExists(follow_constraint):
                print(f"Successfully created constraint: {follow_constraint}")
            else:
                print(f"ERROR: Failed to create constraint!")
        except Exception as e:
            print(f"ERROR creating constraint: {str(e)}")

        # Double-check that constraint exists
        new_constraints = cmds.listConnections(switch_grp, source=True, destination=False, type="constraint") or []
        if new_constraints:
            print(f"Verified constraints after creation: {new_constraints}")
        else:
            print(f"WARNING: No constraints found after creation attempt!")

        return switch_ctrl

    def _finalize_fkik_switch(self):
        """Ensure the FKIK switch properly follows the main joint.
        This method should be called at the very end of the build process.
        """
        # Check if FKIK switch exists
        if "fkik_switch" not in self.controls:
            print(f"Warning: No FKIK switch found for {self.module_id}")
            return

        switch_ctrl = self.controls["fkik_switch"]
        switch_grp = f"{switch_ctrl}_grp"

        if not cmds.objExists(switch_grp):
            print(f"Warning: FKIK switch group {switch_grp} does not exist")
            return

        # Determine the joint to follow
        if self.limb_type == "arm":
            joint_to_follow = "wrist"
        else:  # leg
            joint_to_follow = "ankle"

        if joint_to_follow not in self.joints:
            print(f"Warning: {joint_to_follow} joint not found for {self.module_id}")
            return

        follow_joint = self.joints[joint_to_follow]

        print(f"Finalizing FKIK switch connection for {self.module_id}")

        # Delete any existing constraints on the switch group
        # Use listRelatives to find constraints directly, more reliable than listConnections
        constraints = cmds.listRelatives(switch_grp, type="constraint") or []
        for constraint in constraints:
            print(f"Removing existing constraint: {constraint}")
            cmds.delete(constraint)

        # Use parentConstraint but skip rotate to only follow position
        # This is more reliable than pointConstraint in some situations
        print(f"Creating final constraint from {follow_joint} to {switch_grp}")
        try:
            constraint = cmds.parentConstraint(
                follow_joint,
                switch_grp,
                maintainOffset=True,
                skipRotate=["x", "y", "z"],  # Skip rotation - only follow position
                weight=1.0,  # Ensure full weight
                name=f"{switch_grp}_finalConstraint"
            )[0]

            # Set high constraint priority to ensure it's evaluated last
            cmds.setAttr(f"{constraint}.interpType", 2)  # No flip

            print(f"Successfully created final constraint: {constraint}")
        except Exception as e:
            print(f"ERROR creating constraint: {str(e)}")

    def _fix_joint_orientations(self):
        """
        Fix joint orientations using Maya's native joint orientation tool.
        This ensures proper X-down-the-bone, Y-up orientation for all joints.
        Also zeroes out any transform rotations.
        """
        print(f"Fixing joint orientations for {self.module_id} using Maya's native tool")

        # Determine which joints to orient based on limb type
        if self.limb_type == "arm":
            chains = [
                ["shoulder", "elbow", "wrist", "hand"],
                ["fk_shoulder", "fk_elbow", "fk_wrist", "fk_hand"],
                ["ik_shoulder", "ik_elbow", "ik_wrist", "ik_hand"]
            ]
        else:  # leg
            chains = [
                ["hip", "knee", "ankle", "foot", "toe"],
                ["fk_hip", "fk_knee", "fk_ankle", "fk_foot", "fk_toe"],
                ["ik_hip", "ik_knee", "ik_ankle", "ik_foot", "ik_toe"]
            ]

        # Store current selection to restore later
        current_selection = cmds.ls(selection=True)

        # Process each chain
        for chain in chains:
            # Get valid joints from the chain
            valid_joints = []
            for joint_name in chain:
                if joint_name in self.joints and cmds.objExists(self.joints[joint_name]):
                    valid_joints.append(self.joints[joint_name])

            if len(valid_joints) < 2:
                print(f"Skipping orientation for chain {chain} (insufficient valid joints)")
                continue

            print(f"Orienting joint chain: {valid_joints}")

            # Select the joints in order
            cmds.select(clear=True)
            cmds.select(valid_joints)

            # Orient joints using Maya's native command
            cmds.joint(
                edit=True,
                orientJoint="xyz",  # Primary axis X
                secondaryAxisOrient="yup",  # Secondary axis Y
                children=True,  # Apply to all children
                zeroScaleOrient=True  # Prevent scale from affecting orientation
            )

            # Zero out transform rotations for all joints in the chain
            for joint in valid_joints:
                cmds.setAttr(f"{joint}.rotateX", 0)
                cmds.setAttr(f"{joint}.rotateY", 0)
                cmds.setAttr(f"{joint}.rotateZ", 0)

                # Print out the resulting joint orient for debugging
                joint_orient = cmds.getAttr(f"{joint}.jointOrient")[0]
                print(f"  {joint} joint orientation: {joint_orient}")

        # Restore original selection
        cmds.select(clear=True)
        if current_selection:
            cmds.select(current_selection)

        print("Joint orientation fix complete")