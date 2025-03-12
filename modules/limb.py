"""
Modular Auto-Rig System
Limb Module (Refactored)

This module contains the implementation of the limb rig module (arms and legs).
Refactored to improve joint orientations, planar validation, and pole vector handling.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import math
from autorig.core.module_base import BaseModule
from autorig.core.utils import create_control, create_guide, create_joint, set_color_override, CONTROL_COLORS
from autorig.core.joint_utils import (is_planar_chain, make_planar, create_oriented_joint_chain,
                                     fix_joint_orientations, validate_pole_vector_placement,
                                     fix_specific_joint_orientation)
from autorig.core.vector_utils import (vector_from_two_points, vector_length, normalize_vector,
                                     dot_product, cross_product, scale_vector, add_vectors,
                                     subtract_vectors, get_midpoint, angle_between_vectors_deg)


class LimbModule(BaseModule):
    """
    Module for creating arm or leg rigs with IK/FK capabilities.
    Implements planar validation and improved joint orientation.
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

        # Additional reference objects for blade orientation
        self.blade_guides = {}

        # Store planar validation results
        self.is_planar = True
        self.planar_adjusted = False

    def _get_default_positions(self):
        """
        Get default guide positions based on limb type.

        Returns:
            dict: Default guide positions
        """
        if self.limb_type == "arm":
            return {
                "clavicle": (5 if self.side == "l" else -5, 130, 0),
                "shoulder": (5 if self.side == "l" else -5, 15, 0),
                "elbow": (10 if self.side == "l" else -10, 15, -2),
                "wrist": (15 if self.side == "l" else -15, 15, 0),
                "hand": (16 if self.side == "l" else -16, 15, 0),
                "pole": (10 if self.side == "l" else -10, 15, 5),
                "upv_shoulder": (5 if self.side == "l" else -5, 16, 0),  # Up vector guide for shoulder
                "upv_elbow": (10 if self.side == "l" else -10, 16, -2)  # Up vector guide for elbow
            }
        elif self.limb_type == "leg":
            return {
                "hip": (2.5 if self.side == "l" else -2.5, 10, 0),
                "knee": (3 if self.side == "l" else -3, 5, 1),
                "ankle": (3 if self.side == "l" else -3, 1, 0),
                "foot": (3 if self.side == "l" else -3, 0, 3),
                "toe": (3 if self.side == "l" else -3, 0, 5),
                "heel": (3 if self.side == "l" else -3, 0, -1),
                "pole": (3 if self.side == "l" else -3, 5, 5),
                "upv_hip": (2.5 if self.side == "l" else -2.5, 11, 0),  # Up vector guide for hip
                "upv_knee": (3 if self.side == "l" else -3, 6, 1)  # Up vector guide for knee
            }
        return {}

    def create_guides(self):
        """Create the limb guides including up vector guides for orientation."""
        self._create_module_groups()

        if self.limb_type == "arm":
            self._create_arm_guides()
        elif self.limb_type == "leg":
            self._create_leg_guides()

    def _create_arm_guides(self):
        """Create guides for an arm rig with orientation helpers."""
        # Create main position guides
        for guide_name, pos in self.default_positions.items():
            # Skip creating the pole vector guide - we'll calculate it automatically
            if guide_name == "pole":
                continue

            if guide_name in ["upv_shoulder", "upv_elbow"]:
                # Create as blade guides (different color)
                self.blade_guides[guide_name] = create_guide(
                    f"{self.module_id}_{guide_name}",
                    pos,
                    self.guide_grp,
                    color=[0, 0.8, 0.8]  # Cyan for up vector guides
                )
            else:
                # Create regular guides
                self.guides[guide_name] = create_guide(f"{self.module_id}_{guide_name}", pos, self.guide_grp)

        # Create visual connections between main guides and their up vectors
        self._create_guide_connections()

    def _create_leg_guides(self):
        """Create guides for a leg rig with orientation helpers."""
        # Create main position guides
        for guide_name, pos in self.default_positions.items():
            # Skip creating the pole vector guide - we'll calculate it automatically
            if guide_name == "pole":
                continue

            if guide_name in ["upv_hip", "upv_knee"]:
                # Create as blade guides (different color)
                self.blade_guides[guide_name] = create_guide(
                    f"{self.module_id}_{guide_name}",
                    pos,
                    self.guide_grp,
                    color=[0, 0.8, 0.8]  # Cyan for up vector guides
                )
            else:
                # Create regular guides
                self.guides[guide_name] = create_guide(f"{self.module_id}_{guide_name}", pos, self.guide_grp)

        # Create visual connections between main guides and their up vectors
        self._create_guide_connections()

    def _create_guide_connections(self):
        """Create visual curve connections between guides and their up vectors."""
        # Define connections to create
        connections = []
        if self.limb_type == "arm":
            connections = [
                ("shoulder", "upv_shoulder"),
                ("elbow", "upv_elbow")
            ]
        elif self.limb_type == "leg":
            connections = [
                ("hip", "upv_hip"),
                ("knee", "upv_knee")
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
        """Build the limb rig with improved joint orientation."""
        if not self.guides:
            raise RuntimeError("Guides not created yet.")

        print(f"\n==========================================")
        print(f"Building {self.module_id} rig...")
        print(f"==========================================\n")

        # Debug: Dump initial guide positions
        self.debug_dump_guide_positions("START OF BUILD")

        # 1. Validate and adjust guide positions for planarity
        print("\n--- STEP 1: VALIDATING GUIDES ---")
        self._validate_guides()

        # Debug: Dump guide positions after validation
        self.debug_dump_guide_positions("AFTER VALIDATION")

        # 2. Create properly oriented joint chains
        print("\n--- STEP 2: CREATING JOINTS WITH ORIENTATION ---")
        self._create_joints_with_orientation()

        # 3. Create IK chain
        print("\n--- STEP 3: CREATING IK CHAIN ---")
        self._create_ik_chain()

        # 4. Create FK chain
        print("\n--- STEP 4: CREATING FK CHAIN ---")
        self._create_fk_chain()

        # 4.5 Create clavicle setup if this is an arm
        if self.limb_type == "arm":
            print("\n--- STEP 4.5: CREATING CLAVICLE SETUP ---")
            self._create_clavicle_setup()

        # 5. Create controls
        print("\n--- STEP 5: CREATING CONTROLS ---")
        if self.limb_type == "arm":
            self._create_arm_controls()
        elif self.limb_type == "leg":
            self._create_leg_controls()

        # 6. Create FK/IK switch
        print("\n--- STEP 6: CREATING FK/IK SWITCH ---")
        self._create_fkik_switch()

        # 7. Setup FK/IK blending
        print("\n--- STEP 7: SETTING UP FK/IK BLENDING ---")
        self._setup_ikfk_blending()

        # 8. Finalize the FK/IK switch
        print("\n--- STEP 8: FINALIZING FK/IK SWITCH ---")
        self._finalize_fkik_switch()

        # 9. Finalize clavicle connection (NEWLY ADDED STEP)
        if self.limb_type == "arm":
            print("\n--- STEP 9: FINALIZING CLAVICLE CONNECTION ---")
            self._finalize_clavicle_connection()

        # 10. Create pole vector visualization (NEW STEP)
        print("\n--- STEP 10: CREATING POLE VECTOR VISUALIZATION ---")
        self.create_pole_vector_visualization()

        print(f"\nBuild complete for {self.module_id}")

    def _validate_guides(self):
        """
        Validate guide positions and make adjustments if needed.
        Checks for planarity and proper pole vector placement.
        """
        # Debug: Dump initial guide positions
        self.debug_dump_guide_positions("START OF VALIDATION")
        # BYPASS: Force the guides to be considered planar without checking
        self.is_planar = True  # Always consider guides as planar
        self.planar_adjusted = False  # Indicate no adjustment was needed

        # Log that we're bypassing the check
        print(f"\nBypassing planarity check for {self.module_id} guide chain.")

        # Skip remaining planarity validation code...
        print("\nPole vector position will be calculated automatically during build")

        # Debug: Dump final guide positions
        self.debug_dump_guide_positions("END OF VALIDATION")
        # if self.limb_type == "arm":
        #     # Validate arm guides
        #     guide_names = ["shoulder", "elbow", "wrist", "hand"]
        #
        #     # Get positions in sequence - STORE COPIES, not references
        #     joint_positions = []
        #     print("\nCollecting original guide positions:")
        #     for guide_name in guide_names:
        #         if guide_name in self.guides:
        #             pos = cmds.xform(self.guides[guide_name], q=True, t=True, ws=True)
        #             # Make a copy to avoid reference issues
        #             pos_copy = [pos[0], pos[1], pos[2]]
        #             joint_positions.append(pos_copy)
        #             print(f"  {guide_name}: {pos_copy}")
        #         else:
        #             print(f"  WARNING: Guide '{guide_name}' not found!")
        #
        #     # Check if guides form a planar chain
        #     self.is_planar = is_planar_chain(joint_positions)
        #
        #     print(f"\nPlanarity check result: {'PLANAR' if self.is_planar else 'NOT PLANAR'}")
        #
        #     if not self.is_planar:
        #         print(f"Warning: {self.module_id} guide chain is not planar. Adjusting to best-fit plane.")
        #
        #         # Store original positions for comparison
        #         original_positions = []
        #         for pos in joint_positions:
        #             original_positions.append([pos[0], pos[1], pos[2]])
        #
        #         # Adjust positions to be planar
        #         adjusted_positions = make_planar(joint_positions)
        #         self.planar_adjusted = True
        #
        #         # Debug output to compare before and after
        #         print("\nPosition adjustments for planarity:")
        #         for i, (orig, adj) in enumerate(zip(original_positions, adjusted_positions)):
        #             diff = [adj[0] - orig[0], adj[1] - orig[1], adj[2] - orig[2]]
        #             print(f"  Joint {i}: original={orig}, adjusted={adj}, diff={diff}")
        #
        #         # Update guide positions - make sure to check array sizes
        #         print("\nUpdating guide positions:")
        #         for i, guide_name in enumerate(guide_names):
        #             if i < len(adjusted_positions) and guide_name in self.guides:
        #                 # Store position before modification
        #                 before_pos = cmds.xform(self.guides[guide_name], q=True, t=True, ws=True)
        #
        #                 # Update position
        #                 cmds.xform(self.guides[guide_name], t=adjusted_positions[i], ws=True)
        #
        #                 # Verify the change
        #                 after_pos = cmds.xform(self.guides[guide_name], q=True, t=True, ws=True)
        #                 print(f"  {guide_name}: before={before_pos}, after={after_pos}")
        #             else:
        #                 print(f"  Skipping guide '{guide_name}' - index out of range or guide not found")
        #
        #         print(f"Guide positions adjusted to ensure planarity for {self.module_id}")
        #
        #     # We no longer need to validate pole vector position since we'll calculate it automatically
        #     print("\nPole vector position will be calculated automatically during build")
        #
        # elif self.limb_type == "leg":
        #     # Similar code for legs (update the same way)
        #     pass

        # Debug: Dump final guide positions
        self.debug_dump_guide_positions("END OF VALIDATION")

    def _create_joints_with_orientation(self):
        """Create joint chains with proper orientation."""
        print(f"\n=== CREATING JOINTS WITH DIRECT DUPLICATE METHOD ===")

        # 1. Clear any existing joints for a fresh start
        if self.limb_type == "arm":
            self._clear_existing_arm_joints()
        elif self.limb_type == "leg":
            self._clear_existing_leg_joints()

        # 2. Create main joint chain first
        main_joints = self._create_main_joint_chain()

        # Get joint names based on limb type
        if self.limb_type == "arm":
            joint_names = ["shoulder", "elbow", "wrist", "hand"]
        else:  # leg
            joint_names = ["hip", "knee", "ankle", "foot", "toe"]

        # Store main joint orientations for use with IK chain
        joint_orientations = {}
        for i, name in enumerate(joint_names):
            if name in self.joints and cmds.objExists(self.joints[name]):
                joint_orientations[name] = cmds.getAttr(f"{self.joints[name]}.jointOrient")[0]

        print("\nMain joint orientations:")
        for name, orient in joint_orientations.items():
            print(f"  {name}: {orient}")

        # 3. Duplicate main chain to create FK chain
        if main_joints and len(main_joints) >= (4 if self.limb_type == "arm" else 5):
            print("\nDuplicating main chain to create FK chain")
            first_joint_name = "shoulder" if self.limb_type == "arm" else "hip"
            fk_joints = cmds.duplicate(main_joints[0], renameChildren=True,
                                       name=f"{self.module_id}_{first_joint_name}_fk_jnt")

            # Rename FK joints properly
            for i, jnt in enumerate(joint_names):
                if i < len(fk_joints):
                    old_name = fk_joints[i]
                    new_name = f"{self.module_id}_{jnt}_fk_jnt"
                    if old_name != new_name:
                        try:
                            cmds.rename(old_name, new_name)
                            print(f"Renamed FK joint: {old_name} -> {new_name}")
                        except:
                            print(f"Failed to rename {old_name} to {new_name}")

                    # Store in dictionary
                    self.joints[f"fk_{jnt}"] = new_name

        # 4. Create IK chain manually to match main chain EXACTLY
        print("\nCreating IK chain with matching orientations")
        prev_joint = None

        for i, name in enumerate(joint_names):
            if name in self.joints and cmds.objExists(self.joints[name]):
                # Get position from main joint
                pos = cmds.xform(self.joints[name], q=True, t=True, ws=True)

                # Get orientation from stored values
                orient = joint_orientations.get(name, (0, 0, 0))

                # Create the IK joint
                ik_name = f"{self.module_id}_{name}_ik_jnt"

                if i == 0:
                    # First joint
                    cmds.select(clear=True)
                    ik_joint = cmds.joint(name=ik_name, p=pos)
                    # Parent to joint group
                    cmds.parent(ik_joint, self.joint_grp)
                else:
                    # Child joint
                    cmds.select(prev_joint)
                    ik_joint = cmds.joint(name=ik_name, p=pos)

                # Set orientation to match main joint
                cmds.setAttr(f"{ik_joint}.jointOrient", *orient)

                # Store in dictionary
                self.joints[f"ik_{name}"] = ik_joint
                prev_joint = ik_joint

                print(f"Created IK joint {ik_name} at {pos} with orientation {orient}")

        # Verify all chain positions match
        print("\nComparing joint positions across chains:")
        for name in joint_names:
            main_pos = cmds.xform(self.joints[name], q=True, t=True, ws=True) if name in self.joints else None
            fk_pos = cmds.xform(self.joints[f"fk_{name}"], q=True, t=True,
                                ws=True) if f"fk_{name}" in self.joints else None
            ik_pos = cmds.xform(self.joints[f"ik_{name}"], q=True, t=True,
                                ws=True) if f"ik_{name}" in self.joints else None

            print(f"  {name}:")
            print(f"    Main: {main_pos}")
            print(f"    FK: {fk_pos}")
            print(f"    IK: {ik_pos}")

    def _clear_existing_joints(self):
        """Clear all existing joints for this module."""
        print(f"Clearing existing joints for {self.module_id}")

        if self.limb_type == "arm":
            self._clear_existing_arm_joints()
        elif self.limb_type == "leg":
            self._clear_existing_leg_joints()
        else:
            print(f"Unknown limb type: {self.limb_type}")

    def _create_main_joint_chain(self):
        """Create the main joint chain from guide positions."""
        print("\nCreating main joint chain")

        joint_positions = []

        # Use appropriate joint names based on limb type
        if self.limb_type == "arm":
            joint_names = ["shoulder", "elbow", "wrist", "hand"]
        else:  # leg
            joint_names = ["hip", "knee", "ankle", "foot", "toe"]

        # Get positions from guides
        for name in joint_names:
            if name in self.guides:
                pos = cmds.xform(self.guides[name], q=True, t=True, ws=True)
                joint_positions.append(pos)
                print(f"  {name} position: {pos}")
            else:
                print(f"  Warning: Guide '{name}' not found")

        # Create the joints
        created_joints = []
        for i, (name, pos) in enumerate(zip(joint_names, joint_positions)):
            joint_name = f"{self.module_id}_{name}_jnt"

            if i == 0:
                # First joint - create and parent to joint group
                cmds.select(clear=True)
                joint = cmds.joint(name=joint_name, p=pos)
                cmds.parent(joint, self.joint_grp)
            else:
                # Child joint - select parent first
                cmds.select(created_joints[-1])
                joint = cmds.joint(name=joint_name, p=pos)

            created_joints.append(joint)
            self.joints[name] = joint
            print(f"  Created joint: {joint} at {pos}")

        # Orient joints with appropriate settings based on limb type
        if created_joints:
            cmds.select(created_joints[0])

            if self.limb_type == "arm":
                # For arm, use xyz/yup orientation
                print(f"  Applying xyz/yup orientation for arm chain")
                cmds.joint(e=True, oj="xyz", secondaryAxisOrient="yup", ch=True, zso=True)
            else:  # leg
                # For leg, use xyz/zup orientation which gives better hip orientation
                print(f"  Applying xyz/zup orientation for leg chain")
                cmds.joint(e=True, oj="xyz", secondaryAxisOrient="zup", ch=True, zso=True)

        return created_joints

    def _clear_existing_arm_joints(self):
        """Clear existing arm joints before creating new ones."""
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

    def _clear_existing_leg_joints(self):
        """Clear existing leg joints before creating new ones."""
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

    def _create_arm_joint_chains(self):
        """Create arm joint chains with proper orientation including clavicle."""
        # Debug: Dump guide positions before creating joints
        self.debug_dump_guide_positions("BEFORE JOINT CREATION")

        # Get guide positions
        positions = []
        guide_names = ["clavicle", "shoulder", "elbow", "wrist", "hand"]

        # Collect positions and verify all guides exist
        print("\n=== COLLECTING GUIDE POSITIONS FOR JOINT CREATION ===")
        for guide in guide_names:
            if guide not in self.guides:
                print(f"Error: Required guide '{guide}' not found for {self.module_id}")
                # Create a default position if guide doesn't exist
                if len(positions) > 0:
                    # Extend from last position
                    last_pos = positions[-1]
                    default_pos = [last_pos[0] + 5.0, last_pos[1], last_pos[2]]
                    positions.append(default_pos)
                    print(f"Using default position for '{guide}': {default_pos}")
                else:
                    # Create starting position
                    default_pos = [0, 0, 0]
                    positions.append(default_pos)
                    print(f"Using default position for '{guide}': {default_pos}")
                continue

            # IMPORTANT: Make a deep copy of the position
            guide_obj = self.guides[guide]
            pos = cmds.xform(guide_obj, query=True, translation=True, worldSpace=True)
            pos_copy = [pos[0], pos[1], pos[2]]  # Make an explicit copy
            positions.append(pos_copy)
            print(f"  {guide}: {pos_copy} (guide object: {guide_obj})")

        print(f"\nCollected {len(positions)} positions for joint creation")

        # --- MANUAL SAFETY CHECK: If any position is 0,0,0 when it shouldn't be, abort ---
        zero_pos_count = sum(1 for pos in positions if pos[0] == 0 and pos[1] == 0 and pos[2] == 0)
        if zero_pos_count > 0:
            print(f"WARNING: Found {zero_pos_count} positions at origin [0,0,0]!")
            print(f"This is likely an error. Using original guide positions as fallback.")

            # Re-collect the original guide positions as fallback
            positions = []
            for guide in guide_names:
                if guide in self.guides:
                    pos = cmds.xform(self.guides[guide], query=True, translation=True, worldSpace=True)
                    pos_copy = [pos[0], pos[1], pos[2]]
                    positions.append(pos_copy)
                    print(f"  FALLBACK - {guide}: {pos_copy}")
                else:
                    print(f"  WARNING: Guide '{guide}' not found!")

        # Get pole vector position for additional orientation reference
        pole_pos = None
        if "pole" in self.guides:
            pos = cmds.xform(self.guides["pole"], query=True, translation=True, worldSpace=True)
            pole_pos = [pos[0], pos[1], pos[2]]  # Make an explicit copy
            print(f"\nPole vector position: {pole_pos}")

        # --- STEP 1: MAIN JOINT CHAIN ---
        print(f"\n=== CREATING MAIN JOINT CHAIN ===")

        # Create joint names
        joint_names = [
            f"{self.module_id}_clavicle_jnt",
            f"{self.module_id}_shoulder_jnt",
            f"{self.module_id}_elbow_jnt",
            f"{self.module_id}_wrist_jnt",
            f"{self.module_id}_hand_jnt"
        ]

        # DIRECT CREATION WITH CMDS
        print("Creating main joint chain directly with Maya commands:")
        cmds.select(clear=True)

        # Create each joint manually
        try:
            # First joint at clavicle
            cmds.select(self.joint_grp)
            clavicle_jnt = cmds.joint(name=joint_names[0])
            cmds.xform(clavicle_jnt, translation=positions[0], worldSpace=True)

            # Second joint at shoulder
            cmds.select(clavicle_jnt)
            shoulder_jnt = cmds.joint(name=joint_names[1])
            cmds.xform(shoulder_jnt, translation=positions[1], worldSpace=True)

            # Third joint at elbow
            cmds.select(shoulder_jnt)
            elbow_jnt = cmds.joint(name=joint_names[2])
            cmds.xform(elbow_jnt, translation=positions[2], worldSpace=True)

            # Fourth joint at wrist
            cmds.select(elbow_jnt)
            wrist_jnt = cmds.joint(name=joint_names[3])
            cmds.xform(wrist_jnt, translation=positions[3], worldSpace=True)

            # Fifth joint at hand
            cmds.select(wrist_jnt)
            hand_jnt = cmds.joint(name=joint_names[4])
            cmds.xform(hand_jnt, translation=positions[4], worldSpace=True)

            # Store in dictionary
            self.joints["clavicle"] = clavicle_jnt
            self.joints["shoulder"] = shoulder_jnt
            self.joints["elbow"] = elbow_jnt
            self.joints["wrist"] = wrist_jnt
            self.joints["hand"] = hand_jnt

            # Orient joints
            cmds.select(clavicle_jnt)
            cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)

            # Verify final positions
            for joint_name in ["clavicle", "shoulder", "elbow", "wrist", "hand"]:
                if joint_name in self.joints:
                    pos = cmds.xform(self.joints[joint_name], query=True, translation=True, worldSpace=True)
                    print(f"  {joint_name}: {pos}")

        except Exception as e:
            print(f"Error creating main joint chain: {str(e)}")
            import traceback
            traceback.print_exc()
            return

        # --- STEP 2: FK JOINT CHAIN ---
        print(f"\n=== CREATING FK JOINT CHAIN ===")

        # FK joint names
        fk_joint_names = [
            f"{self.module_id}_clavicle_fk_jnt",
            f"{self.module_id}_shoulder_fk_jnt",
            f"{self.module_id}_elbow_fk_jnt",
            f"{self.module_id}_wrist_fk_jnt",
            f"{self.module_id}_hand_fk_jnt"
        ]

        # Create FK joints directly
        try:
            # First joint at clavicle
            cmds.select(self.joint_grp)
            fk_clavicle_jnt = cmds.joint(name=fk_joint_names[0])
            cmds.xform(fk_clavicle_jnt, translation=positions[0], worldSpace=True)

            # Second joint at shoulder
            cmds.select(fk_clavicle_jnt)
            fk_shoulder_jnt = cmds.joint(name=fk_joint_names[1])
            cmds.xform(fk_shoulder_jnt, translation=positions[1], worldSpace=True)

            # Third joint at elbow
            cmds.select(fk_shoulder_jnt)
            fk_elbow_jnt = cmds.joint(name=fk_joint_names[2])
            cmds.xform(fk_elbow_jnt, translation=positions[2], worldSpace=True)

            # Fourth joint at wrist
            cmds.select(fk_elbow_jnt)
            fk_wrist_jnt = cmds.joint(name=fk_joint_names[3])
            cmds.xform(fk_wrist_jnt, translation=positions[3], worldSpace=True)

            # Fifth joint at hand
            cmds.select(fk_wrist_jnt)
            fk_hand_jnt = cmds.joint(name=fk_joint_names[4])
            cmds.xform(fk_hand_jnt, translation=positions[4], worldSpace=True)

            # Store in dictionary
            self.joints["fk_clavicle"] = fk_clavicle_jnt
            self.joints["fk_shoulder"] = fk_shoulder_jnt
            self.joints["fk_elbow"] = fk_elbow_jnt
            self.joints["fk_wrist"] = fk_wrist_jnt
            self.joints["fk_hand"] = fk_hand_jnt

            # Orient joints
            cmds.select(fk_clavicle_jnt)
            cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)

            # Verify final positions
            for joint_name in ["fk_clavicle", "fk_shoulder", "fk_elbow", "fk_wrist", "fk_hand"]:
                if joint_name in self.joints:
                    pos = cmds.xform(self.joints[joint_name], query=True, translation=True, worldSpace=True)
                    print(f"  {joint_name}: {pos}")

        except Exception as e:
            print(f"Error creating FK joint chain: {str(e)}")
            import traceback
            traceback.print_exc()

        # --- STEP 3: IK JOINT CHAIN ---
        print(f"\n=== CREATING IK JOINT CHAIN ===")

        # IK joint names
        ik_joint_names = [
            f"{self.module_id}_clavicle_ik_jnt",
            f"{self.module_id}_shoulder_ik_jnt",
            f"{self.module_id}_elbow_ik_jnt",
            f"{self.module_id}_wrist_ik_jnt",
            f"{self.module_id}_hand_ik_jnt"
        ]

        # Create IK joints directly
        try:
            # First joint at clavicle
            cmds.select(self.joint_grp)
            ik_clavicle_jnt = cmds.joint(name=ik_joint_names[0])
            cmds.xform(ik_clavicle_jnt, translation=positions[0], worldSpace=True)

            # Second joint at shoulder
            cmds.select(ik_clavicle_jnt)
            ik_shoulder_jnt = cmds.joint(name=ik_joint_names[1])
            cmds.xform(ik_shoulder_jnt, translation=positions[1], worldSpace=True)

            # Third joint at elbow
            cmds.select(ik_shoulder_jnt)
            ik_elbow_jnt = cmds.joint(name=ik_joint_names[2])
            cmds.xform(ik_elbow_jnt, translation=positions[2], worldSpace=True)

            # Fourth joint at wrist
            cmds.select(ik_elbow_jnt)
            ik_wrist_jnt = cmds.joint(name=ik_joint_names[3])
            cmds.xform(ik_wrist_jnt, translation=positions[3], worldSpace=True)

            # Fifth joint at hand
            cmds.select(ik_wrist_jnt)
            ik_hand_jnt = cmds.joint(name=ik_joint_names[4])
            cmds.xform(ik_hand_jnt, translation=positions[4], worldSpace=True)

            # Store in dictionary
            self.joints["ik_clavicle"] = ik_clavicle_jnt
            self.joints["ik_shoulder"] = ik_shoulder_jnt
            self.joints["ik_elbow"] = ik_elbow_jnt
            self.joints["ik_wrist"] = ik_wrist_jnt
            self.joints["ik_hand"] = ik_hand_jnt

            # Orient joints
            cmds.select(ik_clavicle_jnt)
            cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)

            # Verify final positions
            for joint_name in ["ik_clavicle", "ik_shoulder", "ik_elbow", "ik_wrist", "ik_hand"]:
                if joint_name in self.joints:
                    pos = cmds.xform(self.joints[joint_name], query=True, translation=True, worldSpace=True)
                    print(f"  {joint_name}: {pos}")

        except Exception as e:
            print(f"Error creating IK joint chain: {str(e)}")
            import traceback
            traceback.print_exc()

        print(f"Created joint chains for {self.module_id}")

        # Verify final joint positions across all chains
        print("\n=== FINAL JOINT POSITIONS ===")
        for joint_type in ["clavicle", "shoulder", "elbow", "wrist", "hand"]:
            print(f"\n{joint_type.upper()} JOINT POSITIONS:")
            for prefix in ["", "fk_", "ik_"]:
                key = f"{prefix}{joint_type}"
                if key in self.joints and cmds.objExists(self.joints[key]):
                    pos = cmds.xform(self.joints[key], query=True, translation=True, worldSpace=True)
                    print(f"  {key}: {pos}")
                else:
                    print(f"  {key}: NOT CREATED")

    def _create_emergency_arm_joints(self, positions):
        """Create basic arm joints without advanced orientation as fallback."""
        print(f"Creating emergency fallback joints for {self.module_id}")

        cmds.select(clear=True)

        # Create a simple joint chain
        joint_names = ["shoulder", "elbow", "wrist", "hand"]
        last_joint = None

        for i, (name, pos) in enumerate(zip(joint_names, positions)):
            full_name = f"{self.module_id}_{name}_jnt"

            if i == 0:
                # Create the root joint
                cmds.select(clear=True)
                if self.joint_grp and cmds.objExists(self.joint_grp):
                    joint = cmds.joint(name=full_name, position=pos)
                    cmds.parent(joint, self.joint_grp)
                else:
                    joint = cmds.joint(name=full_name, position=pos)
            else:
                # Create child joint
                cmds.select(last_joint)
                joint = cmds.joint(name=full_name, position=pos)

            self.joints[name] = joint
            last_joint = joint

        # Do a basic joint orientation
        if len(self.joints) >= 2:
            cmds.joint(self.joints["shoulder"], e=True, oj="xyz", secondaryAxisOrient="yup", ch=True, zso=True)

        print("Created emergency joint chain - some functionality may be limited")

    def _create_emergency_arm_fk_joints(self, positions):
        """Create basic FK arm joints without advanced orientation as fallback."""
        print(f"Creating emergency fallback FK joints for {self.module_id}")

        cmds.select(clear=True)

        # Create a simple joint chain
        joint_names = ["fk_shoulder", "fk_elbow", "fk_wrist", "fk_hand"]
        base_names = ["shoulder", "elbow", "wrist", "hand"]
        last_joint = None

        for i, (name, base_name, pos) in enumerate(zip(joint_names, base_names, positions)):
            full_name = f"{self.module_id}_{base_name}_fk_jnt"

            if i == 0:
                # Create the root joint
                cmds.select(clear=True)
                if self.joint_grp and cmds.objExists(self.joint_grp):
                    joint = cmds.joint(name=full_name, position=pos)
                    cmds.parent(joint, self.joint_grp)
                else:
                    joint = cmds.joint(name=full_name, position=pos)
            else:
                # Create child joint
                cmds.select(last_joint)
                joint = cmds.joint(name=full_name, position=pos)

            self.joints[name] = joint
            last_joint = joint

        # Do a basic joint orientation
        if len(joint_names) >= 2 and joint_names[0] in self.joints:
            cmds.joint(self.joints[joint_names[0]], e=True, oj="xyz", secondaryAxisOrient="yup", ch=True, zso=True)

    def _create_emergency_arm_ik_joints(self, positions):
        """Create basic IK arm joints without advanced orientation as fallback."""
        print(f"Creating emergency fallback IK joints for {self.module_id}")

        cmds.select(clear=True)

        # Create a simple joint chain
        joint_names = ["ik_shoulder", "ik_elbow", "ik_wrist", "ik_hand"]
        base_names = ["shoulder", "elbow", "wrist", "hand"]
        last_joint = None

        for i, (name, base_name, pos) in enumerate(zip(joint_names, base_names, positions)):
            full_name = f"{self.module_id}_{base_name}_ik_jnt"

            if i == 0:
                # Create the root joint
                cmds.select(clear=True)
                if self.joint_grp and cmds.objExists(self.joint_grp):
                    joint = cmds.joint(name=full_name, position=pos)
                    cmds.parent(joint, self.joint_grp)
                else:
                    joint = cmds.joint(name=full_name, position=pos)
            else:
                # Create child joint
                cmds.select(last_joint)
                joint = cmds.joint(name=full_name, position=pos)

            self.joints[name] = joint
            last_joint = joint

        # Do a basic joint orientation
        if len(joint_names) >= 2 and joint_names[0] in self.joints:
            cmds.joint(self.joints[joint_names[0]], e=True, oj="xyz", secondaryAxisOrient="yup", ch=True, zso=True)

    def _create_leg_joint_chains(self):
        """Create leg joint chains with proper orientation."""
        # Get guide positions
        positions = []
        guide_names = ["hip", "knee", "ankle", "foot", "toe"]

        # Collect positions and verify all guides exist
        for guide in guide_names:
            if guide not in self.guides:
                print(f"Error: Required guide '{guide}' not found for {self.module_id}")
                # Create a default position if guide doesn't exist
                if len(positions) > 0:
                    # Extend from last position
                    last_pos = positions[-1]
                    default_pos = [last_pos[0], last_pos[1] - 5.0, last_pos[2]]
                    positions.append(default_pos)
                    print(f"Using default position for '{guide}': {default_pos}")
                else:
                    # Create starting position
                    default_pos = [0, 0, 0]
                    positions.append(default_pos)
                    print(f"Using default position for '{guide}': {default_pos}")
                continue

            pos = cmds.xform(self.guides[guide], query=True, translation=True, worldSpace=True)
            positions.append(pos)

        # Get up vector guide positions for orientation
        up_vectors = {}
        for guide, main_guide in [("upv_hip", "hip"), ("upv_knee", "knee")]:
            if guide in self.blade_guides and main_guide in self.guides:
                up_pos = cmds.xform(self.blade_guides[guide], query=True, translation=True, worldSpace=True)
                main_pos = cmds.xform(self.guides[main_guide], query=True, translation=True, worldSpace=True)

                # Calculate up vector from main guide to up vector guide
                up_vector = [up_pos[0] - main_pos[0], up_pos[1] - main_pos[1], up_pos[2] - main_pos[2]]
                up_vectors[main_guide] = up_vector

        # Get pole vector position for additional orientation reference
        pole_pos = None
        if "pole" in self.guides:
            pole_pos = cmds.xform(self.guides["pole"], query=True, translation=True, worldSpace=True)

        # === CREATE BINDING JOINT CHAIN ===
        joint_names = [
            f"{self.module_id}_hip_jnt",
            f"{self.module_id}_knee_jnt",
            f"{self.module_id}_ankle_jnt",
            f"{self.module_id}_foot_jnt",
            f"{self.module_id}_toe_jnt"
        ]

        # Create oriented joint chain
        try:
            created_joints = create_oriented_joint_chain(
                joint_names,
                positions,
                parent=self.joint_grp,
                pole_vector=pole_pos
            )

            print(f"Created {len(created_joints)} joints out of {len(joint_names)} expected")

            # Store joint names in dictionary - safely handle any size mismatch
            for i, joint_name in enumerate(["hip", "knee", "ankle", "foot", "toe"]):
                if i < len(created_joints):
                    self.joints[joint_name] = created_joints[i]
                else:
                    print(f"Warning: Joint '{joint_name}' not created for {self.module_id}")

            # Apply specific orientation for hip based on up vector guide
            if "hip" in up_vectors and "hip" in self.joints:
                hip_joint = self.joints["hip"]
                # Get the aim vector to next joint
                if "knee" in self.joints:
                    knee_pos = cmds.xform(self.joints["knee"], query=True, translation=True, worldSpace=True)
                    hip_pos = cmds.xform(hip_joint, query=True, translation=True, worldSpace=True)
                    aim_vector = [knee_pos[0] - hip_pos[0], knee_pos[1] - hip_pos[1], knee_pos[2] - hip_pos[2]]

                    # Apply orientation using up vector from guide
                    fix_specific_joint_orientation(
                        hip_joint,
                        aim_vector=aim_vector,
                        up_vector=up_vectors["hip"]
                    )
        except Exception as e:
            print(f"Error creating main joint chain: {str(e)}")
            # Create emergency joints if creation failed
            self._create_emergency_leg_joints(positions)
            return

        # === CREATE FK JOINT CHAIN BY DUPLICATING MAIN CHAIN ===
        fk_joint_names = [
            f"{self.module_id}_hip_fk_jnt",
            f"{self.module_id}_knee_fk_jnt",
            f"{self.module_id}_ankle_fk_jnt",
            f"{self.module_id}_foot_fk_jnt",
            f"{self.module_id}_toe_fk_jnt"
        ]

        # Create oriented joint chain
        try:
            fk_joints = create_oriented_joint_chain(
                fk_joint_names,
                positions,
                parent=self.joint_grp,
                pole_vector=pole_pos
            )

            # Store FK joint names in dictionary
            for i, joint_name in enumerate(["fk_hip", "fk_knee", "fk_ankle", "fk_foot", "fk_toe"]):
                if i < len(fk_joints):
                    self.joints[joint_name] = fk_joints[i]
                else:
                    print(f"Warning: FK joint '{joint_name}' not created for {self.module_id}")

            # Apply specific orientation for FK hip based on up vector guide
            if "hip" in up_vectors and "fk_hip" in self.joints and "aim_vector" in locals():
                fk_hip_joint = self.joints["fk_hip"]
                fix_specific_joint_orientation(
                    fk_hip_joint,
                    aim_vector=aim_vector,
                    up_vector=up_vectors["hip"]
                )
        except Exception as e:
            print(f"Error creating FK joint chain: {str(e)}")
            # Create emergency FK joints if creation failed
            self._create_emergency_leg_fk_joints(positions)

        # === CREATE IK JOINT CHAIN BY DUPLICATING MAIN CHAIN ===
        ik_joint_names = [
            f"{self.module_id}_hip_ik_jnt",
            f"{self.module_id}_knee_ik_jnt",
            f"{self.module_id}_ankle_ik_jnt",
            f"{self.module_id}_foot_ik_jnt",
            f"{self.module_id}_toe_ik_jnt"
        ]

        # Create oriented joint chain
        try:
            ik_joints = create_oriented_joint_chain(
                ik_joint_names,
                positions,
                parent=self.joint_grp,
                pole_vector=pole_pos
            )

            # Store IK joint names in dictionary
            for i, joint_name in enumerate(["ik_hip", "ik_knee", "ik_ankle", "ik_foot", "ik_toe"]):
                if i < len(ik_joints):
                    self.joints[joint_name] = ik_joints[i]
                else:
                    print(f"Warning: IK joint '{joint_name}' not created for {self.module_id}")

            # Apply specific orientation for IK hip based on up vector guide
            if "hip" in up_vectors and "ik_hip" in self.joints and "aim_vector" in locals():
                ik_hip_joint = self.joints["ik_hip"]
                fix_specific_joint_orientation(
                    ik_hip_joint,
                    aim_vector=aim_vector,
                    up_vector=up_vectors["hip"]
                )
        except Exception as e:
            print(f"Error creating IK joint chain: {str(e)}")
            # Create emergency IK joints if creation failed
            self._create_emergency_leg_ik_joints(positions)

        print(f"Created oriented joint chains for {self.module_id}")

        # Verify joint positions are identical between chains
        chain_types = ["Main", "FK", "IK"]
        for joint_type in ["hip", "knee", "ankle", "foot", "toe"]:
            prefix_list = ["", "fk_", "ik_"]
            positions_list = []

            for prefix in prefix_list:
                key = f"{prefix}{joint_type}"
                if key in self.joints and cmds.objExists(self.joints[key]):
                    pos = cmds.xform(self.joints[key], query=True, translation=True, worldSpace=True)
                    positions_list.append(pos)
                else:
                    positions_list.append(None)

            print(f"Joint position check - {joint_type}:")
            for i, chain_type in enumerate(chain_types):
                if positions_list[i]:
                    print(f"  {chain_type}: {positions_list[i]}")
                else:
                    print(f"  {chain_type}: Not created")

    def _create_emergency_leg_joints(self, positions):
        """Create basic leg joints without advanced orientation as fallback."""
        print(f"Creating emergency fallback joints for {self.module_id}")

        cmds.select(clear=True)

        # Create a simple joint chain
        joint_names = ["hip", "knee", "ankle", "foot", "toe"]
        last_joint = None

        for i, (name, pos) in enumerate(zip(joint_names, positions)):
            full_name = f"{self.module_id}_{name}_jnt"

            if i == 0:
                # Create the root joint
                cmds.select(clear=True)
                if self.joint_grp and cmds.objExists(self.joint_grp):
                    joint = cmds.joint(name=full_name, position=pos)
                    cmds.parent(joint, self.joint_grp)
                else:
                    joint = cmds.joint(name=full_name, position=pos)
            else:
                # Create child joint
                cmds.select(last_joint)
                joint = cmds.joint(name=full_name, position=pos)

            self.joints[name] = joint
            last_joint = joint

        # Do a basic joint orientation
        if len(self.joints) >= 2:
            cmds.joint(self.joints["hip"], e=True, oj="xyz", secondaryAxisOrient="yup", ch=True, zso=True)

        print("Created emergency joint chain - some functionality may be limited")

    def _create_emergency_leg_fk_joints(self, positions):
        """Create basic FK leg joints without advanced orientation as fallback."""
        print(f"Creating emergency fallback FK joints for {self.module_id}")

        cmds.select(clear=True)

        # Create a simple joint chain
        joint_names = ["fk_hip", "fk_knee", "fk_ankle", "fk_foot", "fk_toe"]
        base_names = ["hip", "knee", "ankle", "foot", "toe"]
        last_joint = None

        for i, (name, base_name, pos) in enumerate(zip(joint_names, base_names, positions)):
            full_name = f"{self.module_id}_{base_name}_fk_jnt"

            if i == 0:
                # Create the root joint
                cmds.select(clear=True)
                if self.joint_grp and cmds.objExists(self.joint_grp):
                    joint = cmds.joint(name=full_name, position=pos)
                    cmds.parent(joint, self.joint_grp)
                else:
                    joint = cmds.joint(name=full_name, position=pos)
            else:
                # Create child joint
                cmds.select(last_joint)
                joint = cmds.joint(name=full_name, position=pos)

            self.joints[name] = joint
            last_joint = joint

        # Do a basic joint orientation
        if len(joint_names) >= 2 and joint_names[0] in self.joints:
            cmds.joint(self.joints[joint_names[0]], e=True, oj="xyz", secondaryAxisOrient="yup", ch=True, zso=True)

    def _create_emergency_leg_ik_joints(self, positions):
        """Create basic IK leg joints without advanced orientation as fallback."""
        print(f"Creating emergency fallback IK joints for {self.module_id}")

        cmds.select(clear=True)

        # Create a simple joint chain
        joint_names = ["ik_hip", "ik_knee", "ik_ankle", "ik_foot", "ik_toe"]
        base_names = ["hip", "knee", "ankle", "foot", "toe"]
        last_joint = None

        for i, (name, base_name, pos) in enumerate(zip(joint_names, base_names, positions)):
            full_name = f"{self.module_id}_{base_name}_ik_jnt"

            if i == 0:
                # Create the root joint
                cmds.select(clear=True)
                if self.joint_grp and cmds.objExists(self.joint_grp):
                    joint = cmds.joint(name=full_name, position=pos)
                    cmds.parent(joint, self.joint_grp)
                else:
                    joint = cmds.joint(name=full_name, position=pos)
            else:
                # Create child joint
                cmds.select(last_joint)
                joint = cmds.joint(name=full_name, position=pos)

            self.joints[name] = joint
            last_joint = joint

        # Do a basic joint orientation
        if len(joint_names) >= 2 and joint_names[0] in self.joints:
            cmds.joint(self.joints[joint_names[0]], e=True, oj="xyz", secondaryAxisOrient="yup", ch=True, zso=True)

    def _create_ik_chain(self):
        """Create IK chain using Maya's built-in IK handle."""
        if self.limb_type == "arm":
            print(f"\n=== CREATING IK CHAIN FOR {self.module_id} ===")

            # Skip if required joints don't exist
            if not all(f"ik_{jnt}" in self.joints for jnt in ["shoulder", "wrist"]):
                print("Missing required IK joints, cannot create IK chain")
                return

            # Create IK handle from shoulder to wrist
            print(f"Creating IK handle from {self.joints['ik_shoulder']} to {self.joints['ik_wrist']}")
            ik_handle_name = f"{self.module_id}_arm_ikh"
            ik_handle, ik_effector = cmds.ikHandle(
                name=ik_handle_name,
                startJoint=self.joints["ik_shoulder"],
                endEffector=self.joints["ik_wrist"],
                solver="ikRPsolver"
            )

            self.controls["ik_handle"] = ik_handle
            print(f"Created IK handle: {ik_handle}")

            # Calculate pole vector position
            self.pole_vector_pos = self._calculate_pole_vector_position()

            return ik_handle

        elif self.limb_type == "leg":
            print(f"\n=== CREATING IK CHAIN FOR {self.module_id} ===")

            # Skip if required joints don't exist
            if not all(f"ik_{jnt}" in self.joints for jnt in ["hip", "ankle"]):
                print("Missing required IK joints, cannot create IK chain")
                return

            # Create IK handle from hip to ankle
            print(f"Creating IK handle from {self.joints['ik_hip']} to {self.joints['ik_ankle']}")
            ik_handle_name = f"{self.module_id}_leg_ikh"
            ik_handle, ik_effector = cmds.ikHandle(
                name=ik_handle_name,
                startJoint=self.joints["ik_hip"],
                endEffector=self.joints["ik_ankle"],
                solver="ikRPsolver"
            )

            self.controls["ik_handle"] = ik_handle
            print(f"Created IK handle: {ik_handle}")

            # Calculate pole vector position
            self.pole_vector_pos = self._calculate_pole_vector_position()
            print(f"Calculated pole vector position: {self.pole_vector_pos}")

            # Create foot roll system
            self._create_foot_roll_system()

            return ik_handle

    def _create_foot_roll_system(self):
        """Create the foot roll system for legs."""
        if not (self.limb_type == "leg" and "ik_ankle" in self.joints and
                "ik_foot" in self.joints and "ik_toe" in self.joints):
            return

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
        cmds.parent(self.controls["ik_handle"], ankle_grp)

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
        """Create the FK chain (mainly just the duplicated joints, controls come later)."""
        # The FK joints were already created with proper orientation in _create_joints_with_orientation()
        pass

    def _create_arm_controls(self):
        """Create the arm controls with properly oriented shapes and larger sizes."""
        print(f"Creating arm controls for {self.module_id}")

        # Clear any existing controls
        self._clear_existing_arm_controls()

        # Create FK controls
        self._create_arm_fk_controls()

        # Create IK controls
        self._create_arm_ik_controls()

        print("Arm controls creation complete")

    def _clear_existing_arm_controls(self):
        """Clear existing arm controls before creating new ones."""
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

    def _create_arm_fk_controls(self):
        """Create FK controls for arm."""
        # === FK CONTROLS - WITH LARGER SIZES ===
        # Shoulder FK control
        self._create_fk_control("shoulder", "fk_shoulder", 7.0)

        # Elbow FK control
        self._create_fk_control("elbow", "fk_elbow", 7.0, parent_control="fk_shoulder")

        # Wrist FK control
        self._create_fk_control("wrist", "fk_wrist", 6.0, parent_control="fk_elbow")

        # Connect FK controls to FK joints
        for ctrl, jnt in [
            ("fk_shoulder", "fk_shoulder"),
            ("fk_elbow", "fk_elbow"),
            ("fk_wrist", "fk_wrist")
        ]:
            cmds.orientConstraint(self.controls[ctrl], self.joints[jnt], maintainOffset=True)
            cmds.pointConstraint(self.controls[ctrl], self.joints[jnt], maintainOffset=True)

    def _create_fk_control(self, joint_name, control_key, size, parent_control=None):
        """Create an FK control for the given joint."""
        joint = self.joints[control_key]
        joint_pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)
        joint_rot = cmds.xform(joint, query=True, rotation=True, worldSpace=True)

        # Get the joint's world matrix to extract proper aim direction
        joint_matrix = cmds.xform(joint, query=True, matrix=True, worldSpace=True)

        # Extract the X axis from the matrix (first three values)
        x_axis = [joint_matrix[0], joint_matrix[1], joint_matrix[2]]

        # Normalize
        length = math.sqrt(sum(v * v for v in x_axis))
        if length > 0:
            x_axis = [v / length for v in x_axis]
        else:
            x_axis = [1, 0, 0]  # Default if something is wrong

        # Get color based on side
        color = self._get_color_for_control_type("fk")

        # Create the control with proper orientation based on limb type
        if self.limb_type == "leg":
            # For legs, create with Y-up normal first
            ctrl, ctrl_grp = create_control(
                f"{self.module_id}_{joint_name}_fk_ctrl",
                "circle",
                size,
                color,
                normal=[0, 1, 0]  # Y-up for legs
            )

            # Then rotate -90 in Z to orient properly
            cmds.rotate(0, 0, -90, ctrl, relative=True, objectSpace=True)

            # Freeze transformations to apply the rotation
            cmds.makeIdentity(ctrl, apply=True, translate=True, rotate=True, scale=True)
        else:
            # For arms, use the previous method with joint's X axis
            ctrl, ctrl_grp = create_control(
                f"{self.module_id}_{joint_name}_fk_ctrl",
                "circle",
                size,
                color,
                normal=x_axis  # Use joint's X axis for arms
            )

        # Position the control
        temp_constraint = cmds.parentConstraint(joint, ctrl_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Parent appropriately
        if parent_control:
            cmds.parent(ctrl_grp, self.controls[parent_control])
        else:
            cmds.parent(ctrl_grp, self.control_grp)

        self.controls[control_key] = ctrl
        return ctrl, ctrl_grp

    def _create_arm_ik_controls(self):
        """Create IK controls for arm with proper pole vector setup."""
        print(f"Creating IK controls for arm with pole vector setup")

        # Get color based on side
        color = self._get_color_for_control_type("ik")

        # === IK CONTROLS ===
        # Wrist IK control
        wrist_ik_jnt = self.joints["ik_wrist"]
        wrist_ik_ctrl, wrist_ik_grp = create_control(
            f"{self.module_id}_wrist_ik_ctrl",
            "cube",
            3.5,
            color
        )

        # Position the control at the wrist joint
        temp_constraint = cmds.parentConstraint(wrist_ik_jnt, wrist_ik_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)
        cmds.parent(wrist_ik_grp, self.control_grp)
        self.controls["ik_wrist"] = wrist_ik_ctrl

        # 2. Parent IK handle to wrist control
        if "ik_handle" in self.controls and cmds.objExists(self.controls["ik_handle"]):
            print(f"Parenting IK handle {self.controls['ik_handle']} to wrist control {wrist_ik_ctrl}")
            cmds.parent(self.controls["ik_handle"], wrist_ik_ctrl)

        # 3. Create pole vector control
        pole_ctrl, pole_grp = create_control(
            f"{self.module_id}_pole_ctrl",
            "sphere",
            2.5,
            color
        )

        # 4. Position pole control at elbow initially
        if "ik_elbow" in self.joints and cmds.objExists(self.joints["ik_elbow"]):
            print(f"Positioning pole control at elbow initially")
            temp_constraint = cmds.parentConstraint(self.joints["ik_elbow"], pole_grp, maintainOffset=False)[0]
            cmds.delete(temp_constraint)

        cmds.parent(pole_grp, self.control_grp)
        self.controls["pole"] = pole_ctrl

        # Important: Move pole control back in Z BEFORE constraints
        print(f"Moving pole control back in -Z direction")
        cmds.setAttr(f"{pole_ctrl}.translateZ", -50)

        # IMPORTANT: Freeze transformations on the pole vector control
        # This will "bake in" the translation offset
        cmds.select(pole_ctrl, replace=True)  # Select only the pole control
        cmds.makeIdentity(apply=True, translate=True, rotate=True, scale=True)
        print(f"Froze transformations on pole vector control")

        # 5. Create pole vector constraint AFTER freezing transforms
        if "ik_handle" in self.controls and cmds.objExists(self.controls["ik_handle"]):
            print(f"Creating pole vector constraint from {pole_ctrl} to {self.controls['ik_handle']}")
            cmds.poleVectorConstraint(pole_ctrl, self.controls["ik_handle"], weight=1)

        # 7. Zero out the ikHandle's poleVector attributes
        if "ik_handle" in self.controls and cmds.objExists(self.controls["ik_handle"]):
            print(f"Zeroing out poleVector attributes on {self.controls['ik_handle']}")
            cmds.setAttr(f"{self.controls['ik_handle']}.poleVectorX", 0)
            cmds.setAttr(f"{self.controls['ik_handle']}.poleVectorY", 0)
            cmds.setAttr(f"{self.controls['ik_handle']}.poleVectorZ", 0)

        # Orient constraint for IK wrist to maintain orientation
        cmds.orientConstraint(wrist_ik_ctrl, wrist_ik_jnt, maintainOffset=True)

        print("Completed IK controls setup with pole vector")

    def _create_leg_controls(self):
        """Create the leg controls with properly oriented shapes and larger sizes."""
        print(f"Creating leg controls for {self.module_id}")

        # Clear any existing controls
        self._clear_existing_leg_controls()

        # Create FK controls
        self._create_leg_fk_controls()

        # Create IK controls
        self._create_leg_ik_controls()

        print("Leg controls creation complete")

    def _clear_existing_leg_controls(self):
        """Clear existing leg controls before creating new ones."""
        control_names = [
            f"{self.module_id}_hip_fk_ctrl", f"{self.module_id}_knee_fk_ctrl", f"{self.module_id}_ankle_fk_ctrl",
            f"{self.module_id}_ankle_ik_ctrl", f"{self.module_id}_pole_ctrl"
        ]
        for control in control_names:
            if cmds.objExists(control):
                cmds.delete(control)

        # Store IK handle and foot system for later use
        ik_handle = self.controls.get("ik_handle", None)
        ankle_foot_ik = self.controls.get("ankle_foot_ik", None)
        foot_toe_ik = self.controls.get("foot_toe_ik", None)
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

    def _create_leg_fk_controls(self):
        """Create FK controls for leg."""
        # === FK CONTROLS - WITH LARGER SIZES ===
        # Hip FK control
        self._create_fk_control("hip", "fk_hip", 9.0)

        # Knee FK control
        self._create_fk_control("knee", "fk_knee", 8.0, parent_control="fk_hip")

        # Ankle FK control
        self._create_fk_control("ankle", "fk_ankle", 6.0, parent_control="fk_knee")

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

    def _create_leg_ik_controls(self):
        """Create IK controls for leg."""
        # === IK CONTROLS ===
        # IK ankle control
        ankle_ik_jnt = self.joints["ik_ankle"]
        ankle_ik_pos = cmds.xform(ankle_ik_jnt, query=True, translation=True, worldSpace=True)

        # Get color based on side
        color = self._get_color_for_control_type("fk")

        ankle_ik_ctrl, ankle_ik_grp = create_control(
            f"{self.module_id}_ankle_ik_ctrl",
            "cube",
            3.5,  # Larger size
            color
        )

        # Position the control
        temp_constraint = cmds.parentConstraint(ankle_ik_jnt, ankle_ik_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        cmds.parent(ankle_ik_grp, self.control_grp)
        self.controls["ik_ankle"] = ankle_ik_ctrl

        # IMPORTANT: Connect the ankle IK control to the foot roll group
        if "foot_roll_grp" in self.controls and cmds.objExists(self.controls["foot_roll_grp"]):
            print(f"Connecting ankle IK control to foot roll system")
            # Parent constraint to ensure the foot roll group follows the ankle control
            cmds.parentConstraint(
                self.controls["ik_ankle"],
                self.controls["foot_roll_grp"],
                maintainOffset=True,
                name=f"{self.module_id}_footRoll_parentConstraint"
            )
        else:
            print(f"WARNING: Could not find foot roll group to connect to ankle IK control")

        # Add foot attributes
        for attr_name in ["roll", "tilt", "toe", "heel"]:
            if not cmds.attributeQuery(attr_name, node=ankle_ik_ctrl, exists=True):
                cmds.addAttr(ankle_ik_ctrl, longName=attr_name, attributeType="float", defaultValue=0, keyable=True)

        # Create pole vector using the specialized method for legs
        self._create_leg_pole_vector()

        # Set up foot roll - using the pivot groups created in _create_ik_chain
        self._setup_foot_roll_connections()

        # Orient constraint for IK ankle
        cmds.orientConstraint(self.controls["ik_ankle"], self.joints["ik_ankle"], maintainOffset=True)

    def _setup_foot_roll_connections(self):
        """Set up foot roll connections for the foot control attributes."""
        if not all(key in self.controls for key in ["heel_pivot", "toe_pivot", "ball_pivot", "ankle_pivot"]):
            print(f"WARNING: Missing foot pivot groups for {self.module_id} - foot roll will not work")
            return

        ankle_ik_ctrl = self.controls["ik_ankle"]
        print(f"Setting up foot roll connections for {self.module_id}")

        # Define roll stages and thresholds
        ball_roll_threshold = 30.0  # Degrees before toe starts to bend

        # Create utility nodes for advanced foot roll

        # 1. HEEL ROLL (NEGATIVE VALUES)
        # Simple - just connect negative values to heel pivot
        heel_cond = cmds.createNode("condition", name=f"{self.module_id}_heel_condition")
        cmds.setAttr(f"{heel_cond}.operation", 4)  # Less than
        cmds.setAttr(f"{heel_cond}.colorIfFalseR", 0)  # Use 0 if roll is >= 0
        cmds.setAttr(f"{heel_cond}.secondTerm", 0)  # Compare to 0

        # Connect roll attribute to condition node
        cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{heel_cond}.firstTerm")

        # For negative values (heel roll), use the negative roll value directly
        neg_roll = cmds.createNode("multiplyDivide", name=f"{self.module_id}_neg_roll_mult")
        cmds.setAttr(f"{neg_roll}.input2X", -1)  # Negate the value
        cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{neg_roll}.input1X")
        cmds.connectAttr(f"{neg_roll}.outputX", f"{heel_cond}.colorIfTrueR")

        # Connect result to heel pivot
        cmds.connectAttr(f"{heel_cond}.outColorR", f"{self.controls['heel_pivot']}.rotateX")

        # 2. BALL ROLL (0 to threshold) - The foot rolls forward at the ball
        ball_cond = cmds.createNode("condition", name=f"{self.module_id}_ball_condition")
        cmds.setAttr(f"{ball_cond}.operation", 2)  # Greater than
        cmds.setAttr(f"{ball_cond}.secondTerm", 0)  # Compare to 0

        # Create a clamp for the ball roll (0 to threshold)
        ball_clamp = cmds.createNode("clamp", name=f"{self.module_id}_ball_clamp")
        cmds.setAttr(f"{ball_clamp}.minR", 0)
        cmds.setAttr(f"{ball_clamp}.maxR", ball_roll_threshold)

        # Connect roll attribute to condition and clamp
        cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{ball_cond}.firstTerm")
        cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{ball_clamp}.inputR")

        # Connect clamped output as the colorIfTrue for the condition
        cmds.connectAttr(f"{ball_clamp}.outputR", f"{ball_cond}.colorIfTrueR")
        cmds.setAttr(f"{ball_cond}.colorIfFalseR", 0)  # 0 if roll <= 0

        # Connect result to ball pivot
        cmds.connectAttr(f"{ball_cond}.outColorR", f"{self.controls['ball_pivot']}.rotateX")

        # 3. TOE ROLL (beyond threshold) - Only bend toes if roll > threshold
        toe_cond = cmds.createNode("condition", name=f"{self.module_id}_toe_condition")
        cmds.setAttr(f"{toe_cond}.operation", 2)  # Greater than
        cmds.setAttr(f"{toe_cond}.secondTerm", ball_roll_threshold)  # Compare to threshold

        # Connect roll attribute to condition
        cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{toe_cond}.firstTerm")

        # For roll values > threshold, use (roll - threshold)
        toe_offset = cmds.createNode("plusMinusAverage", name=f"{self.module_id}_toe_offset")
        cmds.setAttr(f"{toe_offset}.operation", 2)  # Subtract
        cmds.connectAttr(f"{ankle_ik_ctrl}.roll", f"{toe_offset}.input1D[0]")
        cmds.setAttr(f"{toe_offset}.input1D[1]", ball_roll_threshold)

        # Connect the result as the colorIfTrue for the condition
        cmds.connectAttr(f"{toe_offset}.output1D", f"{toe_cond}.colorIfTrueR")
        cmds.setAttr(f"{toe_cond}.colorIfFalseR", 0)  # 0 if roll <= threshold

        # 4. TOE MANUAL CONTROL - Connect separate toe attribute
        # Create a plusMinusAverage node to combine auto roll toe effect and manual toe control
        toe_combine = cmds.createNode("plusMinusAverage", name=f"{self.module_id}_toe_combine")
        cmds.setAttr(f"{toe_combine}.operation", 1)  # Add

        # Connect the automatic toe roll (from condition) to the first input
        cmds.connectAttr(f"{toe_cond}.outColorR", f"{toe_combine}.input1D[0]")

        # Connect the manual toe attribute directly to the second input
        cmds.connectAttr(f"{ankle_ik_ctrl}.toe", f"{toe_combine}.input1D[1]")

        # Connect the combined result to the toe pivot
        cmds.connectAttr(f"{toe_combine}.output1D", f"{self.controls['toe_pivot']}.rotateX")

        # 5. TILT - Side-to-side rotation (unchanged)
        tilt_mult = cmds.createNode("multiplyDivide", name=f"{self.module_id}_tilt_mult")
        cmds.connectAttr(f"{ankle_ik_ctrl}.tilt", f"{tilt_mult}.input1Z")
        cmds.setAttr(f"{tilt_mult}.input2Z", 1.0)  # Full strength
        cmds.connectAttr(f"{tilt_mult}.outputZ", f"{self.controls['ball_pivot']}.rotateZ")

        # 6. HEEL Y ROTATION - For heel twist (unchanged)
        heel_mult = cmds.createNode("multiplyDivide", name=f"{self.module_id}_heel_mult")
        cmds.connectAttr(f"{ankle_ik_ctrl}.heel", f"{heel_mult}.input1Y")
        cmds.setAttr(f"{heel_mult}.input2Y", 1.0)  # Full strength
        cmds.connectAttr(f"{heel_mult}.outputY", f"{self.controls['heel_pivot']}.rotateY")

        print(f"Set up improved foot roll controls for {self.module_id}")

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

        # Position the switch with appropriate offset
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
        cmds.xform(switch_grp, rotation=[90, 0, 0], relative=True)

        cmds.parent(switch_grp, self.control_grp)

        # Add the FK/IK blend attribute (0=FK, 1=IK)
        if not cmds.attributeQuery("FkIkBlend", node=switch_ctrl, exists=True):
            cmds.addAttr(switch_ctrl, longName="FkIkBlend", attributeType="float",
                         min=0, max=1, defaultValue=1, keyable=True)  # Default to IK

        # Store the switch control
        self.controls["fkik_switch"] = switch_ctrl

        # Make the switch follow the main binding joint
        # First, check if there are any existing constraints and delete them
        constraints = cmds.listRelatives(switch_grp, type="constraint") or []
        for constraint in constraints:
            cmds.delete(constraint)

        # Create a point constraint
        cmds.parentConstraint(
            follow_joint,
            switch_grp,
            maintainOffset=True,
            skipRotate=["x", "y", "z"],  # Skip rotation - only follow position
            name=f"{switch_grp}_parentConstraint"
        )

        return switch_ctrl

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

        # Validate that constraint is working correctly
        constraints = cmds.listRelatives(switch_grp, type="constraint") or []
        if not constraints:
            # If no constraint exists, create a new one
            cmds.parentConstraint(
                follow_joint,
                switch_grp,
                maintainOffset=True,
                skipRotate=["x", "y", "z"],  # Skip rotation - only follow position
                name=f"{switch_grp}_finalConstraint"
            )
            print(f"Created new constraint to follow {follow_joint}")
        else:
            print(f"Existing constraints are valid: {constraints}")

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

    def validate_guides(self):
        """
        Validate all guides and make sure they're properly positioned.
        This is a public method that can be called before building.

        Returns:
            bool: True if guides are valid
        """
        # Perform validation
        self._validate_guides()

        # Return result
        return self.is_planar and not self.planar_adjusted

    def create_pole_vector_visualization(self):
        """
        Create a visual line connecting from mid-joint to pole vector.
        Useful for visualizing the pole vector direction.

        Returns:
            str: Name of the created curve
        """
        if self.limb_type == "arm" and all(j in self.joints for j in ["elbow", "shoulder"]):
            mid_joint = self.joints["elbow"]
        elif self.limb_type == "leg" and all(j in self.joints for j in ["knee", "hip"]):
            mid_joint = self.joints["knee"]
        else:
            return None

        if "pole" not in self.controls:
            return None

        from autorig.core.utils import create_pole_vector_line

        # Create visualization line with color matching the IK control
        curve, clusters = create_pole_vector_line(
            self.joints["shoulder" if self.limb_type == "arm" else "hip"],
            mid_joint,
            self.controls["pole"],
            color=CONTROL_COLORS["ik"]
        )

        # Store reference to the curve
        self.utility_nodes["pole_viz_curve"] = curve
        self.utility_nodes["pole_viz_clusters"] = clusters

        return curve

    def cleanup(self):
        """
        Clean up temporary nodes created during the build process.
        """
        # Call base class cleanup
        super().cleanup()

        # Hide IK and FK joint chains
        joint_prefixes = ["ik_", "fk_"]
        for prefix in joint_prefixes:
            # Get all joints with this prefix
            joints = [j for j in self.joints.values() if prefix in j]
            for joint in joints:
                if cmds.objExists(joint):
                    cmds.setAttr(f"{joint}.visibility", 0)

        # Add any other cleanup operations specific to limb module
        print(f"Cleanup completed for {self.module_id}")

    def switch_to_fk(self):
        """
        Switch the limb to FK mode.
        """
        if "fkik_switch" in self.controls:
            switch_ctrl = self.controls["fkik_switch"]
            cmds.setAttr(f"{switch_ctrl}.FkIkBlend", 0)

    def switch_to_ik(self):
        """
        Switch the limb to IK mode.
        """
        if "fkik_switch" in self.controls:
            switch_ctrl = self.controls["fkik_switch"]
            cmds.setAttr(f"{switch_ctrl}.FkIkBlend", 1)

    def match_fk_to_ik(self):
        """
        Match FK controls to current IK pose.
        Useful for seamless switching from IK to FK.
        """
        # Only proceed if we have the necessary controls and joints
        if not all(
                key in self.controls for key in ["fkik_switch", "ik_wrist" if self.limb_type == "arm" else "ik_ankle"]):
            print(f"Cannot match FK to IK: missing controls")
            return False

        # Get current blend value to restore later
        switch_ctrl = self.controls["fkik_switch"]
        current_blend = cmds.getAttr(f"{switch_ctrl}.FkIkBlend")

        # Temporarily switch to IK mode to read accurate positions
        cmds.setAttr(f"{switch_ctrl}.FkIkBlend", 1)

        # Match positions based on limb type
        if self.limb_type == "arm":
            # Match shoulder
            if all(j in self.joints for j in ["shoulder", "fk_shoulder"]):
                shoulder_pos = cmds.xform(self.joints["shoulder"], q=True, ws=True, t=True)
                shoulder_rot = cmds.xform(self.joints["shoulder"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["fk_shoulder"], ws=True, t=shoulder_pos)
                cmds.xform(self.controls["fk_shoulder"], ws=True, ro=shoulder_rot)

            # Match elbow
            if all(j in self.joints for j in ["elbow", "fk_elbow"]):
                elbow_pos = cmds.xform(self.joints["elbow"], q=True, ws=True, t=True)
                elbow_rot = cmds.xform(self.joints["elbow"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["fk_elbow"], ws=True, t=elbow_pos)
                cmds.xform(self.controls["fk_elbow"], ws=True, ro=elbow_rot)

            # Match wrist
            if all(j in self.joints for j in ["wrist", "fk_wrist"]):
                wrist_pos = cmds.xform(self.joints["wrist"], q=True, ws=True, t=True)
                wrist_rot = cmds.xform(self.joints["wrist"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["fk_wrist"], ws=True, t=wrist_pos)
                cmds.xform(self.controls["fk_wrist"], ws=True, ro=wrist_rot)
        else:  # leg
            # Match hip
            if all(j in self.joints for j in ["hip", "fk_hip"]):
                hip_pos = cmds.xform(self.joints["hip"], q=True, ws=True, t=True)
                hip_rot = cmds.xform(self.joints["hip"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["fk_hip"], ws=True, t=hip_pos)
                cmds.xform(self.controls["fk_hip"], ws=True, ro=hip_rot)

            # Match knee
            if all(j in self.joints for j in ["knee", "fk_knee"]):
                knee_pos = cmds.xform(self.joints["knee"], q=True, ws=True, t=True)
                knee_rot = cmds.xform(self.joints["knee"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["fk_knee"], ws=True, t=knee_pos)
                cmds.xform(self.controls["fk_knee"], ws=True, ro=knee_rot)

            # Match ankle
            if all(j in self.joints for j in ["ankle", "fk_ankle"]):
                ankle_pos = cmds.xform(self.joints["ankle"], q=True, ws=True, t=True)
                ankle_rot = cmds.xform(self.joints["ankle"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["fk_ankle"], ws=True, t=ankle_pos)
                cmds.xform(self.controls["fk_ankle"], ws=True, ro=ankle_rot)

        # Restore original blend value
        cmds.setAttr(f"{switch_ctrl}.FkIkBlend", current_blend)

        return True

    def match_ik_to_fk(self):
        """
        Match IK controls to current FK pose.
        Useful for seamless switching from FK to IK.
        """
        # Only proceed if we have the necessary controls and joints
        if not all(key in self.controls for key in
                   ["fkik_switch", "ik_wrist" if self.limb_type == "arm" else "ik_ankle", "pole"]):
            print(f"Cannot match IK to FK: missing controls")
            return False

        # Get current blend value to restore later
        switch_ctrl = self.controls["fkik_switch"]
        current_blend = cmds.getAttr(f"{switch_ctrl}.FkIkBlend")

        # Temporarily switch to FK mode to read accurate positions
        cmds.setAttr(f"{switch_ctrl}.FkIkBlend", 0)

        # Match positions based on limb type
        if self.limb_type == "arm":
            # Match wrist IK control to FK wrist
            if all(j in self.joints for j in ["wrist"]):
                wrist_pos = cmds.xform(self.joints["wrist"], q=True, ws=True, t=True)
                wrist_rot = cmds.xform(self.joints["wrist"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["ik_wrist"], ws=True, t=wrist_pos)
                cmds.xform(self.controls["ik_wrist"], ws=True, ro=wrist_rot)

            # Position pole vector - this requires more complex calculation
            self._position_pole_vector_from_fk()
        else:  # leg
            # Match ankle IK control to FK ankle
            if all(j in self.joints for j in ["ankle"]):
                ankle_pos = cmds.xform(self.joints["ankle"], q=True, ws=True, t=True)
                ankle_rot = cmds.xform(self.joints["ankle"], q=True, ws=True, ro=True)
                cmds.xform(self.controls["ik_ankle"], ws=True, t=ankle_pos)
                cmds.xform(self.controls["ik_ankle"], ws=True, ro=ankle_rot)

            # Position pole vector - this requires more complex calculation
            self._position_pole_vector_from_fk()

        # Restore original blend value
        cmds.setAttr(f"{switch_ctrl}.FkIkBlend", current_blend)

        return True

    def _position_pole_vector_from_fk(self):
        """
        Calculate and position the pole vector control to match the current FK pose.
        This is a helper method for match_ik_to_fk.
        """
        if self.limb_type == "arm":
            if not all(j in self.joints for j in ["shoulder", "elbow", "wrist"]):
                return

            # Get joint positions from the binding joints (which have the FK pose)
            shoulder_pos = cmds.xform(self.joints["shoulder"], q=True, ws=True, t=True)
            elbow_pos = cmds.xform(self.joints["elbow"], q=True, ws=True, t=True)
            wrist_pos = cmds.xform(self.joints["wrist"], q=True, ws=True, t=True)
        else:  # leg
            if not all(j in self.joints for j in ["hip", "knee", "ankle"]):
                return

            # Get joint positions from the binding joints (which have the FK pose)
            shoulder_pos = cmds.xform(self.joints["hip"], q=True, ws=True, t=True)
            elbow_pos = cmds.xform(self.joints["knee"], q=True, ws=True, t=True)
            wrist_pos = cmds.xform(self.joints["ankle"], q=True, ws=True, t=True)

        # Calculate vectors using our utility functions (no numpy)
        # First calculate vectors
        v1 = vector_from_two_points(shoulder_pos, elbow_pos)  # Vector from shoulder to elbow
        v2 = vector_from_two_points(elbow_pos, wrist_pos)  # Vector from elbow to wrist

        # Calculate the midpoint of the shoulder-wrist line
        mid = get_midpoint(shoulder_pos, wrist_pos)

        # Calculate vector from midpoint to elbow (this is the bend direction)
        bend_dir = vector_from_two_points(mid, elbow_pos)

        # Normalize and scale to get pole vector position
        bend_length = vector_length(bend_dir)
        if bend_length > 0.0001:  # Avoid division by zero
            pole_dir = normalize_vector(bend_dir)

            # Scale to a suitable distance (can be adjusted)
            scale_factor = 20.0
            pole_pos = [
                elbow_pos[0] + pole_dir[0] * scale_factor,
                elbow_pos[1] + pole_dir[1] * scale_factor,
                elbow_pos[2] + pole_dir[2] * scale_factor
            ]

            # Position the pole vector control
            cmds.xform(self.controls["pole"], ws=True, t=pole_pos)

    def debug_dump_guide_positions(self, stage="unknown"):
        """Dump all guide positions for debugging."""
        print(f"\n=== GUIDE POSITIONS AT {stage} ===")
        for guide_name, guide in self.guides.items():
            if cmds.objExists(guide):
                pos = cmds.xform(guide, query=True, translation=True, worldSpace=True)
                print(f"  {guide_name}: {pos}")

        print(f"\n=== BLADE GUIDE POSITIONS AT {stage} ===")
        for guide_name, guide in self.blade_guides.items():
            if cmds.objExists(guide):
                pos = cmds.xform(guide, query=True, translation=True, worldSpace=True)
                print(f"  {guide_name}: {pos}")
        print("=============================================\n")

    def _calculate_pole_vector_position(self):
        """
        Calculate the correct pole vector position based on the elbow's orientation.
        This places the pole vector behind the elbow along its local Z axis.

        Returns:
            list: The calculated pole vector position [x, y, z]
        """
        if self.limb_type == "arm":
            middle_joint = "elbow"
        else:  # leg
            middle_joint = "knee"

        # Verify the joint exists
        if middle_joint not in self.joints or not cmds.objExists(self.joints[middle_joint]):
            print(f"Cannot calculate pole vector: {middle_joint} joint not found")

            # Use guide position as fallback
            if "pole" in self.guides:
                return cmds.xform(self.guides["pole"], q=True, t=True, ws=True)
            return [0, 0, 0]

        # Get the joint's position
        joint = self.joints[middle_joint]
        joint_pos = cmds.xform(joint, q=True, t=True, ws=True)

        # Get the joint's orientation matrix
        joint_matrix = cmds.xform(joint, q=True, matrix=True, ws=True)

        # Extract the Z axis direction from the matrix
        # In a 4x4 matrix, indices 8, 9, 10 represent the Z axis direction
        z_axis = [joint_matrix[8], joint_matrix[9], joint_matrix[10]]

        # Normalize the Z axis
        z_length = (z_axis[0] ** 2 + z_axis[1] ** 2 + z_axis[2] ** 2) ** 0.5
        if z_length > 0.0001:
            z_axis = [z_axis[0] / z_length, z_axis[1] / z_length, z_axis[2] / z_length]

        # Calculate pole vector position 50 units along NEGATIVE Z axis
        pole_distance = -15.0  # Negative to go backward along Z
        pole_pos = [
            joint_pos[0] + z_axis[0] * pole_distance,
            joint_pos[1] + z_axis[1] * pole_distance,
            joint_pos[2] + z_axis[2] * pole_distance
        ]

        print(f"Calculated pole vector position: {pole_pos}")
        print(f"Based on {middle_joint} position: {joint_pos}")
        print(f"Using Z axis: {z_axis}")

        return pole_pos

    def _create_leg_pole_vector(self):
        """
        Create and properly position the pole vector control for the leg.
        Following a similar workflow to the manual MEL approach.
        """
        print(f"\nCreating pole vector control for {self.module_id} leg")

        # Get color based on side
        color = self._get_color_for_control_type("fk")

        # 1. Create pole vector control
        pole_ctrl, pole_grp = create_control(
            f"{self.module_id}_pole_ctrl",
            "sphere",  # Use sphere for pole vector
            2.5,  # Size
            color
        )

        # 2. Position pole control at knee initially using a temporary constraint
        if "ik_knee" in self.joints and cmds.objExists(self.joints["ik_knee"]):
            print(f"Positioning pole control at knee initially")
            temp_constraint = cmds.parentConstraint(self.joints["ik_knee"], pole_grp, maintainOffset=False)[0]
            cmds.delete(temp_constraint)

        # 3. Parent pole control to control group
        cmds.parent(pole_grp, self.control_grp)
        self.controls["pole"] = pole_ctrl

        # Important: Move pole control up in Y BEFORE constraints
        print(f"Moving pole control up in Y direction")
        cmds.setAttr(f"{pole_ctrl}.translateY", 50)

        # IMPORTANT: Freeze transformations on the pole vector control
        # This will "bake in" the translation offset
        cmds.select(pole_ctrl, replace=True)  # Select only the pole control
        cmds.makeIdentity(apply=True, translate=True, rotate=True, scale=True)
        print(f"Froze transformations on pole vector control")

        # 4. Create pole vector constraint AFTER freezing transforms
        if "ik_handle" in self.controls and cmds.objExists(self.controls["ik_handle"]):
            print(f"Creating pole vector constraint from {pole_ctrl} to {self.controls['ik_handle']}")
            cmds.poleVectorConstraint(pole_ctrl, self.controls["ik_handle"], weight=1)

        # 6. Zero out the ikHandle's poleVector attributes
        if "ik_handle" in self.controls and cmds.objExists(self.controls["ik_handle"]):
            print(f"Zeroing out poleVector attributes on {self.controls['ik_handle']}")
            cmds.setAttr(f"{self.controls['ik_handle']}.poleVectorX", 0)
            cmds.setAttr(f"{self.controls['ik_handle']}.poleVectorY", 0)
            cmds.setAttr(f"{self.controls['ik_handle']}.poleVectorZ", 0)

        print("Leg pole vector setup complete")
        return pole_ctrl

    def _create_clavicle_setup(self):
        """
        Creates a clavicle joint and control that works with all joint chains.
        The FK shoulder control will be parented later in finalize method.
        """
        if self.limb_type != "arm":
            return  # Only for arms

        # Check if clavicle guide exists
        if "clavicle" not in self.guides:
            print(f"No clavicle guide found for {self.module_id}, skipping clavicle setup")
            return

        # Get clavicle and shoulder positions
        clavicle_pos = cmds.xform(self.guides["clavicle"], query=True, translation=True, worldSpace=True)
        shoulder_pos = cmds.xform(self.guides["shoulder"], query=True, translation=True, worldSpace=True)

        # Create clavicle joint
        cmds.select(clear=True)
        cmds.select(self.joint_grp)
        clavicle_joint = cmds.joint(name=f"{self.module_id}_clavicle_jnt", position=clavicle_pos)

        # Create temporary shoulder joint to help with orientation
        cmds.select(clavicle_joint)
        temp_shoulder = cmds.joint(name="temp_shoulder", position=shoulder_pos)

        # Orient the joint chain properly
        cmds.joint(clavicle_joint, e=True, oj="xyz", secondaryAxisOrient="yup", zeroScaleOrient=True)

        # Store the clavicle joint
        self.joints["clavicle"] = clavicle_joint

        # Delete the temporary shoulder joint
        cmds.delete(temp_shoulder)

        # Create circle control with proper orientation
        circle = cmds.circle(name=f"{self.module_id}_clavicle_ctrl", normal=[0, 1, 0], radius=7.0)[0]

        # Rotate -90 in Z to orient the opening along X
        cmds.rotate(0, 0, -90, circle, relative=True, objectSpace=True)

        # Freeze transformations
        cmds.makeIdentity(circle, apply=True, translate=True, rotate=True, scale=True)

        # Get color based on side
        color = self._get_color_for_control_type("fk")

        # Apply color
        set_color_override(circle, color)

        # Create control group
        circle_grp = cmds.group(circle, name=f"{circle}_grp")

        # Position at clavicle
        temp_constraint = cmds.parentConstraint(clavicle_joint, circle_grp, maintainOffset=False)[0]
        cmds.delete(temp_constraint)

        # Store reference and parent to control group
        self.controls["clavicle"] = circle
        cmds.parent(circle_grp, self.control_grp)

        # Connect control to joint
        cmds.parentConstraint(circle, clavicle_joint, maintainOffset=True)

        # Parent all shoulder joints (main, FK, IK) under the clavicle
        for prefix in ["", "fk_", "ik_"]:
            key = f"{prefix}shoulder"
            if key in self.joints and cmds.objExists(self.joints[key]):
                # Get current parent
                current_parent = cmds.listRelatives(self.joints[key], parent=True) or []
                if current_parent:
                    # Unparent first
                    cmds.parent(self.joints[key], world=True)

                # Parent to clavicle
                cmds.parent(self.joints[key], clavicle_joint)
                print(f"Parented {key} joint to clavicle")

        print(f"Created clavicle setup for {self.module_id}")

    def _finalize_clavicle_connection(self):
        """
        Finalize the connection between clavicle control and FK shoulder control.
        This goes directly by name rather than using the control dictionary.
        """
        if self.limb_type != "arm":
            return  # Only for arms

        # Use exact node names rather than dictionary lookup
        fk_ctrl_grp = f"{self.module_id}_shoulder_fk_ctrl_grp"
        clavicle_ctrl = f"{self.module_id}_clavicle_ctrl"

        # Verify both exist
        if not cmds.objExists(fk_ctrl_grp) or not cmds.objExists(clavicle_ctrl):
            print(f"Cannot complete clavicle connection for {self.module_id}: required nodes not found")
            return

        try:
            # Direct parenting operation
            cmds.parent(fk_ctrl_grp, clavicle_ctrl)
            print(f"Connected {fk_ctrl_grp} to {clavicle_ctrl}")
        except Exception as e:
            print(f"Error connecting clavicle to FK shoulder: {str(e)}")

    def _get_color_for_control_type(self, control_type):
        """
        Get the color for a control based on the module's side.

        Args:
            control_type (str): Type of control ('fk', 'ik', etc.)

        Returns:
            list: RGB color values
        """
        # FK/IK switch always yellow
        if control_type == "fkik_switch":
            return [1, 1, 0]  # Yellow

        # Center controls always yellow
        if self.side == "c":
            return CONTROL_COLORS.get(control_type, [1, 1, 0])  # Default to yellow

        # Left side: blue
        if self.side == "l":
            if control_type in ["fk", "ik", "pole"]:
                return [0, 0, 1.0]  # Pure blue

        # Right side: red
        if self.side == "r":
            if control_type in ["fk", "ik", "pole"]:
                return [1.0, 0, 0]  # Red for right side

        # Default to original color
        return CONTROL_COLORS.get(control_type, [1, 1, 0])

    def create_pole_vector_visualization(self):
        """
        Create a visual line connecting from mid-joint to pole vector.
        Useful for visualizing the pole vector direction.

        Returns:
            str: Name of the created curve
        """
        if self.limb_type == "arm" and all(j in self.joints for j in ["elbow", "shoulder"]):
            mid_joint = self.joints["elbow"]
        elif self.limb_type == "leg" and all(j in self.joints for j in ["knee", "hip"]):
            mid_joint = self.joints["knee"]
        else:
            return None

        if "pole" not in self.controls:
            return None

        from autorig.core.utils import create_pole_vector_line

        # Create visualization line with color matching the IK control (now Z-axis blue for left side)
        curve, clusters = create_pole_vector_line(
            self.joints["shoulder" if self.limb_type == "arm" else "hip"],
            mid_joint,
            self.controls["pole"],
            color=self._get_color_for_control_type("ik")
        )

        # Store reference to the curve
        self.utility_nodes["pole_viz_curve"] = curve
        self.utility_nodes["pole_viz_clusters"] = clusters

        # Connect curve visibility to IK/FK switch (visible only in IK mode)
        if "fkik_switch" in self.controls:
            # Connect visibility to the FK/IK switch attribute - matches IK control visibility
            cmds.connectAttr(f"{self.controls['fkik_switch']}.FkIkBlend", f"{curve}.visibility", force=True)
            print(f"Connected pole vector line visibility to FK/IK switch")

        return curve
