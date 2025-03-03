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
        """Create the leg joints with proper hierarchies and orientation."""
        # First, delete any existing joints that might cause conflicts
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

        # Get guide positions
        hip_pos = cmds.xform(self.guides["hip"], query=True, translation=True, worldSpace=True)
        knee_pos = cmds.xform(self.guides["knee"], query=True, translation=True, worldSpace=True)
        ankle_pos = cmds.xform(self.guides["ankle"], query=True, translation=True, worldSpace=True)
        foot_pos = cmds.xform(self.guides["foot"], query=True, translation=True, worldSpace=True)
        toe_pos = cmds.xform(self.guides["toe"], query=True, translation=True, worldSpace=True)

        print(f"Creating main joint chain for {self.module_id}")

        # ===== MAIN JOINT CHAIN =====
        # Create the main joint chain
        cmds.select(clear=True)
        main_hip = cmds.joint(name=f"{self.module_id}_hip_jnt", position=hip_pos)
        self.joints["hip"] = main_hip

        cmds.select(main_hip)
        main_knee = cmds.joint(name=f"{self.module_id}_knee_jnt", position=knee_pos)
        self.joints["knee"] = main_knee

        cmds.select(main_knee)
        main_ankle = cmds.joint(name=f"{self.module_id}_ankle_jnt", position=ankle_pos)
        self.joints["ankle"] = main_ankle

        cmds.select(main_ankle)
        main_foot = cmds.joint(name=f"{self.module_id}_foot_jnt", position=foot_pos)
        self.joints["foot"] = main_foot

        cmds.select(main_foot)
        main_toe = cmds.joint(name=f"{self.module_id}_toe_jnt", position=toe_pos)
        self.joints["toe"] = main_toe

        # Parent the main chain to the joint group
        cmds.parent(main_hip, self.joint_grp)

        # Orient the main joint chain
        cmds.select(main_hip)
        cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True)

        # Fix knee joint orientation for single axis rotation
        rotation = cmds.getAttr(f"{main_knee}.jointOrient")[0]
        z_rotation = rotation[2]  # Keep only Z rotation for proper bend
        cmds.setAttr(f"{main_knee}.jointOrient", 0, 0, z_rotation)

        print(f"Creating IK joint chain for {self.module_id}")

        # ===== IK JOINT CHAIN =====
        # Create the IK joint chain
        cmds.select(clear=True)
        ik_hip = cmds.joint(name=f"{self.module_id}_hip_ik_jnt", position=hip_pos)
        self.joints["ik_hip"] = ik_hip

        cmds.select(ik_hip)
        ik_knee = cmds.joint(name=f"{self.module_id}_knee_ik_jnt", position=knee_pos)
        self.joints["ik_knee"] = ik_knee

        cmds.select(ik_knee)
        ik_ankle = cmds.joint(name=f"{self.module_id}_ankle_ik_jnt", position=ankle_pos)
        self.joints["ik_ankle"] = ik_ankle

        cmds.select(ik_ankle)
        ik_foot = cmds.joint(name=f"{self.module_id}_foot_ik_jnt", position=foot_pos)
        self.joints["ik_foot"] = ik_foot

        cmds.select(ik_foot)
        ik_toe = cmds.joint(name=f"{self.module_id}_toe_ik_jnt", position=toe_pos)
        self.joints["ik_toe"] = ik_toe

        # Parent the IK chain to the joint group
        cmds.parent(ik_hip, self.joint_grp)

        # Orient the IK joint chain
        cmds.select(ik_hip)
        cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True)

        # Fix IK knee joint orientation
        cmds.setAttr(f"{ik_knee}.jointOrient", 0, 0, z_rotation)

        print(f"Creating FK joint chain for {self.module_id}")

        # ===== FK JOINT CHAIN =====
        # Create the FK joint chain
        cmds.select(clear=True)
        fk_hip = cmds.joint(name=f"{self.module_id}_hip_fk_jnt", position=hip_pos)
        self.joints["fk_hip"] = fk_hip

        cmds.select(fk_hip)
        fk_knee = cmds.joint(name=f"{self.module_id}_knee_fk_jnt", position=knee_pos)
        self.joints["fk_knee"] = fk_knee

        cmds.select(fk_knee)
        fk_ankle = cmds.joint(name=f"{self.module_id}_ankle_fk_jnt", position=ankle_pos)
        self.joints["fk_ankle"] = fk_ankle

        cmds.select(fk_ankle)
        fk_foot = cmds.joint(name=f"{self.module_id}_foot_fk_jnt", position=foot_pos)
        self.joints["fk_foot"] = fk_foot

        cmds.select(fk_foot)
        fk_toe = cmds.joint(name=f"{self.module_id}_toe_fk_jnt", position=toe_pos)
        self.joints["fk_toe"] = fk_toe

        # Parent the FK chain to the joint group
        cmds.parent(fk_hip, self.joint_grp)

        # Orient the FK joint chain
        cmds.select(fk_hip)
        cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True)

        # Fix FK knee joint orientation
        cmds.setAttr(f"{fk_knee}.jointOrient", 0, 0, z_rotation)

        print(f"Joint creation complete for {self.module_id}")

    def _create_ik_chain(self):
        """Create the IK chain - specifically only from shoulder to wrist."""
        print(f"Creating IK chain for {self.module_id}")

        if self.limb_type == "arm":
            # Delete any existing IK handle first
            ik_handle_name = f"{self.module_id}_arm_ikh"
            if cmds.objExists(ik_handle_name):
                cmds.delete(ik_handle_name)

            # Create IK handle from shoulder to wrist ONLY (not to hand)
            if "ik_shoulder" in self.joints and "ik_wrist" in self.joints:
                try:
                    # Create new IK handle
                    ik_handle, ik_effector = cmds.ikHandle(
                        name=ik_handle_name,
                        startJoint=self.joints["ik_shoulder"],
                        endEffector=self.joints["ik_wrist"],  # Stop at wrist, not hand
                        solver="ikRPsolver"
                    )
                    self.controls["ik_handle"] = ik_handle

                    # Create IK handle group
                    ik_handle_grp_name = f"{self.module_id}_arm_ikh_grp"
                    if cmds.objExists(ik_handle_grp_name):
                        cmds.delete(ik_handle_grp_name)

                    ik_handle_grp = cmds.group(ik_handle, name=ik_handle_grp_name)
                    cmds.parent(ik_handle_grp, self.control_grp)

                    print(f"Created IK handle: {ik_handle}")
                except Exception as e:
                    print(f"Error creating IK handle: {str(e)}")

        elif self.limb_type == "leg":
            # Similar logic for leg IK setup
            pass

    def _create_fk_chain(self):
        """Create the FK chain (mainly just joints, controls come later)."""
        # The FK chain is just the duplicate joints, no special setup needed here
        pass

    def _create_arm_controls(self):
        """Create the arm controls with proper orientations."""
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

        # === FK CONTROLS ===
        # Shoulder FK control
        shoulder_jnt = self.joints["fk_shoulder"]
        shoulder_pos = cmds.xform(shoulder_jnt, query=True, translation=True, worldSpace=True)
        shoulder_rot = cmds.xform(shoulder_jnt, query=True, rotation=True, worldSpace=True)

        shoulder_ctrl, shoulder_grp = create_control(
            f"{self.module_id}_shoulder_fk_ctrl",
            "circle",
            3.0,
            CONTROL_COLORS["fk"]
        )

        # Rotate the control shape to be perpendicular to the bone
        cmds.select(f"{shoulder_ctrl}Shape")
        cmds.rotate(0, 0, 90, relative=True)
        cmds.select(clear=True)

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
            2.5,
            CONTROL_COLORS["fk"]
        )

        # Rotate the control shape
        cmds.select(f"{elbow_ctrl}Shape")
        cmds.rotate(0, 0, 90, relative=True)
        cmds.select(clear=True)

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
            2.0,
            CONTROL_COLORS["fk"]
        )

        # Rotate the control shape
        cmds.select(f"{wrist_ctrl}Shape")
        cmds.rotate(0, 0, 90, relative=True)
        cmds.select(clear=True)

        # Position the control
        cmds.xform(wrist_grp, translation=wrist_pos, worldSpace=True)
        cmds.xform(wrist_grp, rotation=wrist_rot, worldSpace=True)
        cmds.parent(wrist_grp, self.controls["fk_elbow"])
        self.controls["fk_wrist"] = wrist_ctrl

        # Connect FK controls to FK joints - use orient constraints to control rotation only
        # This prevents issues with positions being disrupted
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
            2.5,
            CONTROL_COLORS["ik"]
        )

        # Position the control
        cmds.xform(wrist_ik_grp, translation=wrist_ik_pos, worldSpace=True)
        cmds.parent(wrist_ik_grp, self.control_grp)
        self.controls["ik_wrist"] = wrist_ik_ctrl

        # Pole vector control
        pole_pos = cmds.xform(self.guides["pole"], query=True, translation=True, worldSpace=True)

        pole_ctrl, pole_grp = create_control(
            f"{self.module_id}_pole_ctrl",
            "square",
            1.5,
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
        """
        Set up FK/IK blending for the limb.
        Uses 0=FK, 1=IK logic with dedicated switch control.
        """
        print(f"Setting up FK/IK blending for {self.module_id}")

        # First, remove any existing constraints on binding joints
        for joint_name in ["shoulder", "elbow", "wrist", "hand"]:
            if joint_name not in self.joints:
                continue

            joint = self.joints[joint_name]
            constraints = cmds.listConnections(joint, source=True, destination=True, type="constraint") or []
            for constraint in constraints:
                if cmds.objExists(constraint):
                    cmds.delete(constraint)

        # Get the FK/IK switch control
        switch_ctrl = self.controls.get("fkik_switch")
        if not switch_ctrl:
            print("Warning: No FK/IK switch control found")
            return

        # Create a reverse node for the switch
        reverse_node = cmds.createNode("reverse", name=f"{self.module_id}_fkik_reverse")
        cmds.connectAttr(f"{switch_ctrl}.FkIkBlend", f"{reverse_node}.inputX")

        # Set up constraints for each joint
        joint_pairs = [
            ("shoulder", "ik_shoulder", "fk_shoulder"),
            ("elbow", "ik_elbow", "fk_elbow"),
            ("wrist", "ik_wrist", "fk_wrist"),
            ("hand", "ik_hand", "fk_hand")
        ]

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

            # Connect weights:
            # - 0 = FK, so connect the reverse of FkIkBlend to the IK weight (to make it 0)
            # - 1 = IK, so connect FkIkBlend directly to the FK weight (to make it 1)
            cmds.connectAttr(f"{switch_ctrl}.FkIkBlend", f"{constraint}.{weights[0]}")  # IK weight
            cmds.connectAttr(f"{reverse_node}.outputX", f"{constraint}.{weights[1]}")  # FK weight

        # Set up visibility for controls based on FK/IK blend
        # Make sure to get FK joints visibility fixed

        # FK controls visible when blend = 0 (use reverse)
        for ctrl_name in ["fk_shoulder", "fk_elbow", "fk_wrist"]:
            if ctrl_name in self.controls:
                cmds.setAttr(f"{self.controls[ctrl_name]}.visibility", 1)  # Start visible
                cmds.connectAttr(f"{reverse_node}.outputX", f"{self.controls[ctrl_name]}.visibility")

        # IK controls visible when blend = 1 (use direct connection)
        for ctrl_name in ["ik_wrist", "pole"]:
            if ctrl_name in self.controls:
                cmds.setAttr(f"{self.controls[ctrl_name]}.visibility", 0)  # Start invisible
                cmds.connectAttr(f"{switch_ctrl}.FkIkBlend", f"{self.controls[ctrl_name]}.visibility")

        # Now fix the FK/IK joint visibility
        # For demonstration purposes, hide the IK and FK joints completely
        # Only the binding joints should be visible
        for prefix in ["ik_", "fk_"]:
            for suffix in ["shoulder", "elbow", "wrist", "hand"]:
                joint_name = f"{prefix}{suffix}"
                if joint_name in self.joints:
                    cmds.setAttr(f"{self.joints[joint_name]}.visibility", 0)

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
        """Create a dedicated FK/IK switch control."""
        print(f"Creating FK/IK switch for {self.module_id}")

        # Get the position of the wrist for placement
        wrist_pos = cmds.xform(self.joints["wrist"], query=True, translation=True, worldSpace=True)

        # Create a small control shape for the switch
        switch_ctrl, switch_grp = create_control(
            f"{self.module_id}_fkik_switch",
            "square",  # Use a square shape to distinguish it
            1.0,  # Small size
            [1, 1, 0]  # Yellow color
        )

        # Position the switch near the wrist
        # Offset it slightly so it doesn't overlap with other controls
        offset = 2.0  # Adjust based on your rig scale
        if self.side == "l":
            switch_pos = [wrist_pos[0], wrist_pos[1] - offset, wrist_pos[2]]
        else:
            switch_pos = [wrist_pos[0], wrist_pos[1] - offset, wrist_pos[2]]

        cmds.xform(switch_grp, translation=switch_pos, worldSpace=True)
        cmds.parent(switch_grp, self.control_grp)

        # Add the FK/IK blend attribute (0=FK, 1=IK)
        if not cmds.attributeQuery("FkIkBlend", node=switch_ctrl, exists=True):
            cmds.addAttr(switch_ctrl, longName="FkIkBlend", attributeType="float",
                         min=0, max=1, defaultValue=1, keyable=True)  # Default to IK

        # Store the switch control
        self.controls["fkik_switch"] = switch_ctrl

        # Set up point constraint to follow the wrist
        cmds.pointConstraint(self.joints["wrist"], switch_grp, maintainOffset=True)

        print(f"Created FK/IK switch control: {switch_ctrl}")
        return switch_ctrl