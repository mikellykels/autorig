"""
Modular Auto-Rig System
Module Manager

This module contains the ModuleManager class which manages rig modules.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import json
from autorig.core.utils import create_control


class ModuleManager:
    """
    Manages the creation and registration of rig modules.
    """

    def __init__(self, character_name="character"):
        """
        Initialize the module manager.

        Args:
            character_name (str): Name of the character
        """
        self.character_name = character_name
        self.modules = {}
        self.guides_grp = None
        self.joints_grp = None
        self.controls_grp = None

        # Create main rig structure
        self._create_rig_structure()

    def _create_rig_structure(self):
        """Create the main groups for the rig structure."""
        # Create main rig group
        self.rig_grp = cmds.group(empty=True, name=f"{self.character_name}_rig")

        # Create guide group
        self.guides_grp = cmds.group(empty=True, name=f"{self.character_name}_guides")
        cmds.parent(self.guides_grp, self.rig_grp)

        # Create joints group
        self.joints_grp = cmds.group(empty=True, name=f"{self.character_name}_joints")
        cmds.parent(self.joints_grp, self.rig_grp)

        # Create controls group
        self.controls_grp = cmds.group(empty=True, name=f"{self.character_name}_controls")
        cmds.parent(self.controls_grp, self.rig_grp)

        # Create cluster handles group under guides group
        self.clusters_grp = cmds.group(empty=True, name=f"{self.character_name}_clusters")

        # Verify group was created before setting visibility
        if cmds.objExists(self.clusters_grp):
            cmds.parent(self.clusters_grp, self.guides_grp)
            # Set visibility off by default
            try:
                cmds.setAttr(f"{self.clusters_grp}.visibility", 0)
            except Exception as e:
                print(f"Warning: Could not set visibility for clusters group: {e}")
        else:
            print(f"Error: Could not create clusters group {self.character_name}_clusters")

    def register_module(self, module):
        """
        Register a new module.

        Args:
            module (BaseModule): Module instance
        """
        self.modules[module.module_id] = module
        module.set_manager(self)

    def create_all_guides(self):
        """Create guides for all registered modules."""
        for module_id, module in self.modules.items():
            module.create_guides()

    def build_all_modules(self):
        """Build all registered modules."""
        for module_id, module in self.modules.items():
            module.build()

        self.organize_clusters()

    def save_guide_positions(self, file_path):
        """
        Save the positions of all guides to a file.

        Args:
            file_path (str): Path to save the guide positions
        """
        guide_data = {}

        for module_id, module in self.modules.items():
            guide_data[module_id] = module.get_guide_positions()

        with open(file_path, 'w') as f:
            json.dump(guide_data, f, indent=4)

    def load_guide_positions(self, file_path):
        """
        Load the positions of all guides from a file.

        Args:
            file_path (str): Path to load the guide positions from
        """
        with open(file_path, 'r') as f:
            guide_data = json.load(f)

        for module_id, positions in guide_data.items():
            if module_id in self.modules:
                self.modules[module_id].set_guide_positions(positions)

    def _setup_mirrored_ik_constraints_for_arm(self, module):
        """
        Set up IK constraints specifically for a mirrored arm module.
        This ensures all IK controls are properly connected to IK joints and handles.

        Args:
            module (BaseModule): The mirrored arm module
        """
        print(f"Setting up IK constraints for mirrored arm: {module.module_id}")

        # Verify IK handle exists
        if "ik_handle" not in module.controls or not cmds.objExists(module.controls["ik_handle"]):
            print("IK handle not found, cannot set up constraints")
            return

        # Make sure we have IK wrist and pole controls
        if not all(key in module.controls for key in ["ik_wrist", "pole"]):
            print("Missing IK controls. Make sure controls were created before setting up constraints.")
            return

        if not all(key in module.joints for key in ["ik_wrist", "ik_hand"]):
            print("Missing required IK joints, cannot set up constraints")
            return

        # Get the IK handle and controls
        ik_handle = module.controls["ik_handle"]
        wrist_ctrl = module.controls["ik_wrist"]
        pole_ctrl = module.controls["pole"]

        # Clear existing constraints on the IK handle
        constraints = cmds.listConnections(ik_handle, source=True, destination=True, type="constraint") or []
        for constraint in constraints:
            if cmds.objExists(constraint):
                print(f"Deleting existing constraint: {constraint}")
                cmds.delete(constraint)

        # Set up constraints
        print(f"Creating point constraint from {wrist_ctrl} to {ik_handle}")
        cmds.pointConstraint(wrist_ctrl, ik_handle, maintainOffset=True)

        print(f"Creating pole vector constraint from {pole_ctrl} to {ik_handle}")
        cmds.poleVectorConstraint(pole_ctrl, ik_handle)

        # Orient constraint for IK wrist joint
        print(f"Creating orient constraint from {wrist_ctrl} to {module.joints['ik_wrist']}")
        cmds.orientConstraint(wrist_ctrl, module.joints["ik_wrist"], maintainOffset=True)

        # The hand joint can still follow the wrist joint in the arm setup
        # (since there's no complex foot roll system like in the leg)
        print(f"Creating parent constraint from {module.joints['ik_wrist']} to {module.joints['ik_hand']}")
        cmds.parentConstraint(module.joints["ik_wrist"], module.joints["ik_hand"], maintainOffset=True)

        print(f"IK constraints setup complete for {module.module_id}")

    def _setup_mirrored_ik_constraints_for_leg(self, module):
        """
        Set up IK constraints specifically for a mirrored leg module.
        This ensures all IK controls are properly connected to IK joints and handles.

        Args:
            module (BaseModule): The mirrored leg module
        """
        print(f"Setting up IK constraints for mirrored leg: {module.module_id}")

        # Verify IK handle and foot roll components exist
        if "ik_handle" not in module.controls or not cmds.objExists(module.controls["ik_handle"]):
            print("IK handle not found, cannot set up constraints")
            return

        if not all(key in module.controls for key in ["ik_ankle", "pole", "foot_roll_grp", "ankle_pivot"]):
            print("Missing required controls for leg IK setup")
            return

        # Get the components
        ik_handle = module.controls["ik_handle"]
        ankle_ctrl = module.controls["ik_ankle"]
        pole_ctrl = module.controls["pole"]
        foot_roll_grp = module.controls["foot_roll_grp"]
        ankle_pivot = module.controls["ankle_pivot"]

        # IMPORTANT: We need to fix the connections in a specific order

        # 1. Temporarily unparent the IK handle from the foot roll system
        print(f"Temporarily unparenting IK handle from foot roll system")
        ik_handle_parent = cmds.listRelatives(ik_handle, parent=True)[0]
        ik_handle_grp = f"{module.module_id}_leg_ikh_grp"
        temp_grp = cmds.group(empty=True, name=f"{module.module_id}_temp_grp")
        cmds.parent(ik_handle, temp_grp)

        # 2. Clear existing constraints on the IK handle
        constraints = cmds.listConnections(ik_handle, source=True, destination=True, type="constraint") or []
        for constraint in constraints:
            if cmds.objExists(constraint):
                print(f"Deleting existing constraint: {constraint}")
                cmds.delete(constraint)

        # 3. Create pole vector constraint while IK handle is in neutral space
        print(f"Creating pole vector constraint from {pole_ctrl} to {ik_handle}")
        pv_constraint = cmds.poleVectorConstraint(pole_ctrl, ik_handle)
        print(f"Created pole vector constraint: {pv_constraint}")

        # 4. Reparent IK handle back to foot roll system
        print(f"Reparenting IK handle back to foot roll system")
        cmds.parent(ik_handle, ankle_pivot)
        cmds.delete(temp_grp)

        # 5. Connect ankle control to foot roll group
        print(f"Creating parent constraint from {ankle_ctrl} to {foot_roll_grp}")
        # Clear existing constraints
        foot_constraints = cmds.listConnections(foot_roll_grp, source=True, destination=True, type="constraint") or []
        for constraint in foot_constraints:
            if cmds.objExists(constraint):
                cmds.delete(constraint)

        # Create new constraint
        cmds.parentConstraint(
            ankle_ctrl,
            foot_roll_grp,
            maintainOffset=True,
            name=f"{module.module_id}_footRoll_parentConstraint"
        )

        # 6. Orient constraint for IK ankle joint - IMPORTANT: ONLY ORIENT, no parent constraint
        print(f"Creating orient constraint from {ankle_ctrl} to {module.joints['ik_ankle']}")
        cmds.orientConstraint(ankle_ctrl, module.joints["ik_ankle"], maintainOffset=True)

        print(f"IK constraints setup complete for {module.module_id}")

    def mirror_modules(self):
        """
        Mirror left side modules to right side.
        Only mirror limb modules (arms and legs), not spine.

        Returns:
            int: Number of modules mirrored
        """
        mirrored_count = 0

        # 1. Find all left side modules
        left_modules = [module for module_id, module in self.modules.items()
                        if module.side == "l" and module.module_type in ["arm", "leg"]]

        # Bail early if no left modules to mirror
        if not left_modules:
            return 0

        # 2. For each left module, create a corresponding right module
        for left_module in left_modules:
            # Check if a corresponding right module already exists
            right_module_id = f"r_{left_module.module_name}"

            # Skip if right module already exists in modules dictionary
            if right_module_id in self.modules:
                print(f"Right module {right_module_id} already exists, updating it")
                right_module = self.modules[right_module_id]
            else:
                # Create a new module of the same type
                if left_module.module_type == "arm":
                    from autorig.modules.limb import LimbModule
                    right_module = LimbModule("r", left_module.module_name, "arm")
                elif left_module.module_type == "leg":
                    from autorig.modules.limb import LimbModule
                    right_module = LimbModule("r", left_module.module_name, "leg")
                else:
                    # Skip non-limb modules
                    continue

                # Register the new module
                self.register_module(right_module)

            mirrored_count += 1
            print(f"\n======= MIRRORING MODULE: {right_module.module_id} =======")

            # 3. Mirror the main joints
            self._mirror_joints_only(left_module, right_module)

            # 4. Mirror any missing FK and IK joint chains (mainly for legs)
            self._mirror_fk_ik_joints(left_module, right_module)

            # 5. Handle module type-specific setup
            if right_module.module_type == "arm":
                # For arms, set up the IK handle first, then controls
                self._setup_arm_ik_handle(right_module)

                # Then create all controls
                self._create_mirrored_arm_controls(left_module, right_module, {
                    "main": [1, 0.3, 0.3],  # Red for main controls
                    "secondary": [1, 0.4, 0.4],  # Lighter red for secondary
                    "fk": [0.9, 0.2, 0.2],  # Red for FK
                    "ik": [0.8, 0.2, 0.3],  # Reddish-purple for IK
                    "cog": [0.9, 0.4, 0.2],  # Reddish-orange for COG
                })
            elif right_module.module_type == "leg":
                # For legs, create controls with properly set up IK
                self._create_mirrored_leg_controls(left_module, right_module, {
                    "main": [1, 0.3, 0.3],  # Red for main controls
                    "secondary": [1, 0.4, 0.4],  # Lighter red for secondary
                    "fk": [0.9, 0.2, 0.2],  # Red for FK
                    "ik": [0.8, 0.2, 0.3],  # Reddish-purple for IK
                    "cog": [0.9, 0.4, 0.2],  # Reddish-orange for COG
                })

            # 6. Fix constraints and FK/IK blending
            self._setup_mirrored_constraints(right_module)

            print(f"======= COMPLETED MIRRORING: {right_module.module_id} =======\n")

        # 7. Joint connection happens with Add Root Joint button
        print("\n=== JOINT CONNECTION WILL HAPPEN WITH 'ADD ROOT JOINT' ===\n")

        return mirrored_count

    def _mirror_joints_only(self, source_module, target_module):
        """
        Mirror joints from source module to target module using Maya's native mirror joint command.
        Directly mirrors root joints with -mirrorBehavior flag.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        # Make sure source module has joints
        if not source_module.joints:
            print("Error: Source joints not found")
            return

        print(f"\n=== MIRRORING JOINTS from {source_module.module_id} to {target_module.module_id} ===")

        # Clear target module's joints dictionary
        target_module.joints.clear()

        # Make sure the target module has its module groups created
        if not hasattr(target_module, '_create_module_groups'):
            print("Error: Target module doesn't have _create_module_groups method")
            return

        # Initialize module groups if needed
        target_module._create_module_groups()

        # 1. First mirror the main chain
        # Determine the root joint
        if source_module.module_type == "arm":
            root_joint_key = "clavicle" if "clavicle" in source_module.joints else "shoulder"
        else:  # leg
            root_joint_key = "hip"

        if root_joint_key not in source_module.joints:
            print(f"Root joint {root_joint_key} not found, cannot mirror")
            return

        root_joint = source_module.joints[root_joint_key]

        # Select and mirror using Maya's native command exactly as in your MEL example
        print(f"Mirroring main chain from {root_joint}")
        cmds.select(clear=True)
        cmds.select(root_joint)

        try:
            mirrored_result = cmds.mirrorJoint(
                mirrorYZ=True,
                mirrorBehavior=True,
                searchReplace=[f"{source_module.side}_", f"{target_module.side}_"]
            )
            print(f"Mirror result: {mirrored_result}")

            # Update the target module's joints dictionary
            # We need to map all the mirrored joints to their keys
            if mirrored_result:
                # Find all joints in the target module
                target_prefix = f"{target_module.side}_{target_module.module_name}_"
                target_joints = cmds.ls(f"{target_prefix}*_jnt", f"{target_prefix}*_fk_jnt", f"{target_prefix}*_ik_jnt")

                # Map them to the target module's joints dictionary
                for joint in target_joints:
                    # Extract the joint type from the name
                    if "_fk_jnt" in joint:
                        # FK joint (e.g., r_arm_shoulder_fk_jnt)
                        base_name = joint.replace(f"{target_prefix}", "").replace("_fk_jnt", "")
                        target_module.joints[f"fk_{base_name}"] = joint
                        print(f"Mapped fk_{base_name} to {joint}")
                    elif "_ik_jnt" in joint:
                        # IK joint (e.g., r_arm_shoulder_ik_jnt)
                        base_name = joint.replace(f"{target_prefix}", "").replace("_ik_jnt", "")
                        target_module.joints[f"ik_{base_name}"] = joint
                        print(f"Mapped ik_{base_name} to {joint}")
                    elif "_jnt" in joint:
                        # Main joint (e.g., r_arm_shoulder_jnt)
                        base_name = joint.replace(f"{target_prefix}", "").replace("_jnt", "")
                        target_module.joints[base_name] = joint
                        print(f"Mapped {base_name} to {joint}")

            # Parent the root mirrored joint to the target module's joint group
            if mirrored_result and target_module.joint_grp:
                mirrored_root = mirrored_result[0]
                current_parent = cmds.listRelatives(mirrored_root, parent=True)
                if current_parent:
                    cmds.parent(mirrored_root, world=True)
                cmds.parent(mirrored_root, target_module.joint_grp)
                print(f"Parented {mirrored_root} to {target_module.joint_grp}")
        except Exception as e:
            print(f"Error during mirroring operation: {str(e)}")
            import traceback
            traceback.print_exc()

        print(f"=== JOINT MIRRORING COMPLETE: {source_module.module_id} to {target_module.module_id} ===\n")

    def _setup_mirrored_constraints(self, target_module):
        """
        Set up constraints for a mirrored module with additional debugging.
        """
        print(f"\nSetting up constraints for mirrored module: {target_module.module_id}")

        # Fix FK/IK blending
        print("\nSetting up FK/IK blending")
        if "fkik_switch" in target_module.controls:
            # Create reverse node for the switch
            reverse_node_name = f"{target_module.module_id}_fkik_reverse"
            if not cmds.objExists(reverse_node_name):
                reverse_node = cmds.createNode("reverse", name=reverse_node_name)
                cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend", f"{reverse_node}.inputX")
                print(f"Created reverse node: {reverse_node}")
            else:
                reverse_node = reverse_node_name
                print(f"Using existing reverse node: {reverse_node}")

            # Define joint pairs based on module type
            joint_pairs = []
            if target_module.limb_type == "arm":
                joint_pairs = [
                    ("shoulder", "ik_shoulder", "fk_shoulder"),
                    ("elbow", "ik_elbow", "fk_elbow"),
                    ("wrist", "ik_wrist", "fk_wrist"),
                    ("hand", "ik_hand", "fk_hand")
                ]
            elif target_module.limb_type == "leg":
                joint_pairs = [
                    ("hip", "ik_hip", "fk_hip"),
                    ("knee", "ik_knee", "fk_knee"),
                    ("ankle", "ik_ankle", "fk_ankle"),
                    ("foot", "ik_foot", "fk_foot"),
                    ("toe", "ik_toe", "fk_toe")
                ]

            # Connect main joint chain to IK/FK
            for bind_joint, ik_joint, fk_joint in joint_pairs:
                print(f"Setting up blend for {bind_joint}")

                if all(key in target_module.joints for key in [bind_joint, ik_joint, fk_joint]):
                    print(f"All required joints found")

                    # Check if constraint already exists - delete it to recreate cleanly
                    constraints = cmds.listConnections(target_module.joints[bind_joint], source=True, destination=True,
                                                       type="parentConstraint") or []
                    for constraint in constraints:
                        if cmds.objExists(constraint):
                            cmds.delete(constraint)
                            print(f"Deleted existing constraint: {constraint}")

                    # Create new constraint
                    constraint = cmds.parentConstraint(
                        target_module.joints[ik_joint],
                        target_module.joints[fk_joint],
                        target_module.joints[bind_joint],
                        maintainOffset=True
                    )[0]
                    print(f"Created new constraint: {constraint}")

                    # Get weight attributes and connect to switch
                    weights = cmds.parentConstraint(constraint, query=True, weightAliasList=True)
                    if len(weights) == 2:
                        try:
                            # Connect weights to fkik switch - IK weight first (when switch is 1/IK)
                            cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend",
                                             f"{constraint}.{weights[0]}", force=True)
                            print(
                                f"Connected {target_module.controls['fkik_switch']}.FkIkBlend -> {constraint}.{weights[0]}")

                            # FK weight (when switch is 0/FK) - connect to reverse node
                            cmds.connectAttr(f"{reverse_node}.outputX",
                                             f"{constraint}.{weights[1]}", force=True)
                            print(f"Connected {reverse_node}.outputX -> {constraint}.{weights[1]}")
                        except Exception as e:
                            print(f"Error connecting weights: {str(e)}")
                else:
                    print(f"WARNING: Missing required joints for blend setup")

            # Set up control visibility based on FK/IK switch
            print("\nSetting up control visibility based on FK/IK switch")
            if target_module.limb_type == "arm":
                # Connect FK controls visibility
                for ctrl_key in ["fk_shoulder", "fk_elbow", "fk_wrist"]:
                    if ctrl_key in target_module.controls:
                        ctrl = target_module.controls[ctrl_key]
                        cmds.connectAttr(f"{reverse_node}.outputX", f"{ctrl}.visibility", force=True)
                        print(f"Connected {reverse_node}.outputX -> {ctrl}.visibility")

                # Connect IK controls visibility
                for ctrl_key in ["ik_wrist", "pole"]:
                    if ctrl_key in target_module.controls:
                        ctrl = target_module.controls[ctrl_key]
                        cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend",
                                         f"{ctrl}.visibility", force=True)
                        print(f"Connected {target_module.controls['fkik_switch']}.FkIkBlend -> {ctrl}.visibility")

            elif target_module.limb_type == "leg":
                # Connect FK controls visibility
                for ctrl_key in ["fk_hip", "fk_knee", "fk_ankle"]:
                    if ctrl_key in target_module.controls:
                        ctrl = target_module.controls[ctrl_key]
                        cmds.connectAttr(f"{reverse_node}.outputX", f"{ctrl}.visibility", force=True)
                        print(f"Connected {reverse_node}.outputX -> {ctrl}.visibility")

                # Connect IK controls visibility
                for ctrl_key in ["ik_ankle", "pole"]:
                    if ctrl_key in target_module.controls:
                        ctrl = target_module.controls[ctrl_key]
                        cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend",
                                         f"{ctrl}.visibility", force=True)
                        print(f"Connected {target_module.controls['fkik_switch']}.FkIkBlend -> {ctrl}.visibility")

        print(f"Constraint setup complete for mirrored module: {target_module.module_id}")

    def _mirror_ik_handles(self, source_module, target_module):
        """
        Properly mirror IK handles from source module to target module.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        print(f"\n=== MIRRORING IK HANDLES from {source_module.module_id} to {target_module.module_id} ===")

        # Check module type
        if source_module.module_type not in ["arm", "leg"]:
            print("Not a limb module, skipping")
            return

        # Mirror arm IK handles
        if source_module.module_type == "arm":
            print("Processing arm IK handles")

            # Create IK handle from shoulder to wrist ONLY
            if "ik_shoulder" in target_module.joints and "ik_wrist" in target_module.joints:
                # Delete any existing IK handle
                ik_handle_name = f"{target_module.module_id}_arm_ikh"
                if cmds.objExists(ik_handle_name):
                    print(f"Deleting existing IK handle: {ik_handle_name}")
                    cmds.delete(ik_handle_name)

                # Create new IK handle
                print(
                    f"Creating IK handle from {target_module.joints['ik_shoulder']} to {target_module.joints['ik_wrist']}")
                ik_handle, ik_effector = cmds.ikHandle(
                    name=ik_handle_name,
                    startJoint=target_module.joints["ik_shoulder"],
                    endEffector=target_module.joints["ik_wrist"],  # Stop at wrist
                    solver="ikRPsolver"
                )
                target_module.controls["ik_handle"] = ik_handle
                print(f"Created IK handle: {ik_handle}")

                # Create IK handle group
                ik_handle_grp_name = f"{target_module.module_id}_arm_ikh_grp"
                if cmds.objExists(ik_handle_grp_name):
                    print(f"Deleting existing IK handle group: {ik_handle_grp_name}")
                    cmds.delete(ik_handle_grp_name)

                ik_handle_grp = cmds.group(ik_handle, name=ik_handle_grp_name)
                print(f"Created IK handle group: {ik_handle_grp}")

                print(f"Parenting {ik_handle_grp} to {target_module.control_grp}")
                cmds.parent(ik_handle_grp, target_module.control_grp)

        # Mirror leg IK handles
        elif source_module.module_type == "leg":
            print("Processing leg IK handles")

            # Create IK handle from hip to ankle ONLY
            if "ik_hip" in target_module.joints and "ik_ankle" in target_module.joints:
                # Delete any existing IK handle
                ik_handle_name = f"{target_module.module_id}_leg_ikh"
                if cmds.objExists(ik_handle_name):
                    print(f"Deleting existing IK handle: {ik_handle_name}")
                    cmds.delete(ik_handle_name)

                # Create new IK handle
                print(f"Creating IK handle from {target_module.joints['ik_hip']} to {target_module.joints['ik_ankle']}")
                ik_handle, ik_effector = cmds.ikHandle(
                    name=ik_handle_name,
                    startJoint=target_module.joints["ik_hip"],
                    endEffector=target_module.joints["ik_ankle"],  # Stop at ankle
                    solver="ikRPsolver"
                )
                target_module.controls["ik_handle"] = ik_handle
                print(f"Created IK handle: {ik_handle}")

                # Create IK handle group
                ik_handle_grp_name = f"{target_module.module_id}_leg_ikh_grp"
                if cmds.objExists(ik_handle_grp_name):
                    print(f"Deleting existing IK handle group: {ik_handle_grp_name}")
                    cmds.delete(ik_handle_grp_name)

                ik_handle_grp = cmds.group(ik_handle, name=ik_handle_grp_name)
                print(f"Created IK handle group: {ik_handle_grp}")

                print(f"Parenting {ik_handle_grp} to {target_module.control_grp}")
                cmds.parent(ik_handle_grp, target_module.control_grp)

                # Create foot roll system
                if "ik_ankle" in target_module.joints and "ik_foot" in target_module.joints and "ik_toe" in target_module.joints:
                    print(f"Creating foot roll system for {target_module.module_id}")

                    # Delete any existing foot IK handles
                    ankle_foot_ik_name = f"{target_module.module_id}_ankle_foot_ikh"
                    foot_toe_ik_name = f"{target_module.module_id}_foot_toe_ikh"
                    foot_roll_grp_name = f"{target_module.module_id}_foot_roll_grp"

                    for name in [ankle_foot_ik_name, foot_toe_ik_name, foot_roll_grp_name]:
                        if cmds.objExists(name):
                            print(f"Deleting existing object: {name}")
                            cmds.delete(name)

                    # Create ankle to foot IK handle
                    print(
                        f"Creating ankle-foot IK handle from {target_module.joints['ik_ankle']} to {target_module.joints['ik_foot']}")
                    ankle_foot_ik, ankle_foot_eff = cmds.ikHandle(
                        name=ankle_foot_ik_name,
                        startJoint=target_module.joints["ik_ankle"],
                        endEffector=target_module.joints["ik_foot"],
                        solver="ikSCsolver"
                    )

                    # Create foot to toe IK handle
                    print(
                        f"Creating foot-toe IK handle from {target_module.joints['ik_foot']} to {target_module.joints['ik_toe']}")
                    foot_toe_ik, foot_toe_eff = cmds.ikHandle(
                        name=foot_toe_ik_name,
                        startJoint=target_module.joints["ik_foot"],
                        endEffector=target_module.joints["ik_toe"],
                        solver="ikSCsolver"
                    )

                    # Get position data for reverse foot setup
                    ankle_pos = cmds.xform(target_module.joints["ik_ankle"], query=True, translation=True,
                                           worldSpace=True)
                    foot_pos = cmds.xform(target_module.joints["ik_foot"], query=True, translation=True,
                                          worldSpace=True)
                    toe_pos = cmds.xform(target_module.joints["ik_toe"], query=True, translation=True, worldSpace=True)

                    # Get heel position - it's a guide
                    if "heel" in target_module.guides and cmds.objExists(target_module.guides["heel"]):
                        heel_pos = cmds.xform(target_module.guides["heel"], query=True, translation=True,
                                              worldSpace=True)
                        print(f"Using heel guide for position: {heel_pos}")
                    else:
                        # Estimate heel position if guide doesn't exist
                        heel_pos = [foot_pos[0], foot_pos[1], foot_pos[2] - 5.0]
                        print(f"Using estimated heel position: {heel_pos}")

                    # Create foot roll hierarchy
                    print("Creating foot roll group hierarchy")
                    foot_roll_grp = cmds.group(empty=True, name=foot_roll_grp_name)
                    cmds.xform(foot_roll_grp, translation=[0, 0, 0], worldSpace=True)
                    cmds.parent(foot_roll_grp, target_module.control_grp)

                    heel_grp = cmds.group(empty=True, name=f"{target_module.module_id}_heel_pivot_grp")
                    cmds.xform(heel_grp, translation=heel_pos, worldSpace=True)
                    cmds.parent(heel_grp, foot_roll_grp)

                    toe_grp = cmds.group(empty=True, name=f"{target_module.module_id}_toe_pivot_grp")
                    cmds.xform(toe_grp, translation=toe_pos, worldSpace=True)
                    cmds.parent(toe_grp, heel_grp)

                    ball_grp = cmds.group(empty=True, name=f"{target_module.module_id}_ball_pivot_grp")
                    cmds.xform(ball_grp, translation=foot_pos, worldSpace=True)
                    cmds.parent(ball_grp, toe_grp)

                    ankle_grp = cmds.group(empty=True, name=f"{target_module.module_id}_ankle_pivot_grp")
                    cmds.xform(ankle_grp, translation=ankle_pos, worldSpace=True)
                    cmds.parent(ankle_grp, ball_grp)

                    # Parent IK handles to appropriate groups
                    print(f"Parenting {foot_toe_ik} to {ball_grp}")
                    cmds.parent(foot_toe_ik, ball_grp)

                    print(f"Parenting {ankle_foot_ik} to {ankle_grp}")
                    cmds.parent(ankle_foot_ik, ankle_grp)

                    # Parent main leg IK handle to ankle group
                    print(f"Parenting {ik_handle} to {ankle_grp}")
                    cmds.parent(ik_handle, ankle_grp)

                    # Store references to the pivot groups
                    target_module.controls["foot_roll_grp"] = foot_roll_grp
                    target_module.controls["heel_pivot"] = heel_grp
                    target_module.controls["toe_pivot"] = toe_grp
                    target_module.controls["ball_pivot"] = ball_grp
                    target_module.controls["ankle_pivot"] = ankle_grp

                    # Store the foot IK handles
                    target_module.controls["ankle_foot_ik"] = ankle_foot_ik
                    target_module.controls["foot_toe_ik"] = foot_toe_ik

                    print(f"Created reverse foot pivot system for {target_module.module_id}")

        print(f"=== IK HANDLE MIRRORING COMPLETE: {source_module.module_id} to {target_module.module_id} ===\n")

    def organize_clusters(self):
        """
        Collect and group all cluster handles.

        Returns:
            int: Number of clusters organized
        """
        # Find all nodes ending with 'Handle'
        all_clusters = cmds.ls("*Handle", type="transform")

        # Filter to only include actual cluster handles
        rig_clusters = []
        for cluster in all_clusters:
            # Verify it's a cluster handle
            if cmds.listRelatives(cluster, shapes=True, type="clusterHandle"):
                rig_clusters.append(cluster)

        # If no clusters found, return
        if not rig_clusters:
            print("No clusters found.")
            return 0

        try:
            # Clear selection first
            cmds.select(clear=True)

            # Select all cluster handles
            cmds.select(rig_clusters)

            # Ensure clusters group exists
            clusters_grp_name = f"{self.character_name}_clusters"
            if not cmds.objExists(clusters_grp_name):
                clusters_grp = cmds.group(empty=True, name=clusters_grp_name)
                cmds.parent(clusters_grp, self.guides_grp)
                print(f"Created clusters group: {clusters_grp_name}")

            # Create a new subgroup for these clusters
            grouped_clusters = cmds.group(name=f"{self.character_name}_clusters_{len(rig_clusters)}")
            cmds.parent(grouped_clusters, clusters_grp_name)

            # Set visibility off
            cmds.setAttr(f"{grouped_clusters}.visibility", 0)

            # Clear selection
            cmds.select(clear=True)

            print(f"Organized {len(rig_clusters)} clusters into {grouped_clusters}")
            return len(rig_clusters)

        except Exception as e:
            print(f"Error organizing clusters: {e}")
            return 0

    def _mirror_controls(self, source_module, target_module):
        """
        Recreate controls from source module to target module with proper size and orientation.
        Right side controls are colored red for visualization.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        if not source_module.controls:
            print("Source module has no controls to mirror")
            return

        print(f"\n=== CREATING CONTROLS FOR {target_module.module_id} BASED ON {source_module.module_id} ===")

        # Clear target module's controls dictionary but preserve IK handles if they exist
        # Store existing IK handles to preserve them
        saved_controls = {}
        for key in ["ik_handle", "ankle_foot_ik", "foot_toe_ik", "foot_roll_grp",
                    "heel_pivot", "toe_pivot", "ball_pivot", "ankle_pivot"]:
            if key in target_module.controls:
                saved_controls[key] = target_module.controls[key]

        # Clear controls dictionary
        target_module.controls = {}

        # Restore saved IK handles
        for key, value in saved_controls.items():
            target_module.controls[key] = value

        # Define right side color override (red hues)
        right_side_colors = {
            "main": [1, 0.3, 0.3],  # Red for main controls
            "secondary": [1, 0.4, 0.4],  # Lighter red for secondary
            "fk": [0.9, 0.2, 0.2],  # Red for FK
            "ik": [0.8, 0.2, 0.3],  # Reddish-purple for IK
            "cog": [0.9, 0.4, 0.2],  # Reddish-orange for COG
        }

        # Create controls based on module type
        if source_module.module_type == "arm":
            self._create_mirrored_arm_controls(source_module, target_module, right_side_colors)
        elif source_module.module_type == "leg":
            self._create_mirrored_leg_controls(source_module, target_module, right_side_colors)

        print(f"=== CONTROL CREATION COMPLETE FOR {target_module.module_id} ===\n")

    def _mirror_single_control(self, source_module, target_module, source_key, target_key, parent=None,
                               color_override=None):
        """
        Mirror a single control from source module to target module.
        Instead of directly mirroring, we recreate the control with proper position and orientation.

        Args:
            source_module: Source module containing the original control
            target_module: Target module to create the mirrored control in
            source_key: Key to look up the control in source_module.controls
            target_key: Key to use for the control in target_module.controls
            parent: Parent for the new control
            color_override: Optional color override for the mirrored control
        """
        if source_key not in source_module.controls:
            print(f"Source control {source_key} not found")
            return

        source_ctrl = source_module.controls[source_key]

        if not cmds.objExists(source_ctrl):
            print(f"Source control {source_ctrl} does not exist")
            return

        # Determine control shape
        shapes = cmds.listRelatives(source_ctrl, shapes=True) or []
        if not shapes:
            print(f"Source control {source_ctrl} has no shapes")
            return

        # Determine control type based on shape
        shape_type = "circle"  # default
        color = [1, 1, 0]  # default yellow

        # Determine shape type and color from source control if no override
        if "_fk_" in source_ctrl:
            shape_type = "circle"
            color = color_override if color_override else [0.2, 0.8, 0.2]  # green for FK
        elif "_ik_" in source_ctrl:
            shape_type = "cube"
            color = color_override if color_override else [0.8, 0.2, 0.8]  # purple for IK
        elif "pole" in source_ctrl:
            shape_type = "sphere"
            color = color_override if color_override else [0.8, 0.2, 0.8]  # purple for pole vector
        elif "fkik_switch" in source_ctrl:
            shape_type = "square"
            color = color_override if color_override else [1, 1, 0]  # yellow for switch
        elif "clavicle" in source_ctrl:
            shape_type = "circle"
            color = color_override if color_override else [0.2, 0.8, 0.2]  # green like FK

        # Create the control with the same shape and color
        target_ctrl_name = source_ctrl.replace(f"{source_module.side}_", f"{target_module.side}_")

        # Get position from corresponding joint
        joint_key = target_key
        if "fk_" in target_key:
            joint_key = target_key
        elif "ik_" in target_key:
            joint_key = target_key
        elif target_key == "pole":
            joint_key = "elbow" if target_module.module_type == "arm" else "knee"
        elif target_key == "fkik_switch":
            joint_key = "wrist" if target_module.module_type == "arm" else "ankle"
        elif target_key == "clavicle":
            joint_key = "clavicle"

        # Get control size by measuring the source control
        size = 7.0  # default
        if cmds.objExists(source_ctrl):
            bounding_box = cmds.exactWorldBoundingBox(source_ctrl)
            size = max(
                bounding_box[3] - bounding_box[0],  # x size
                bounding_box[4] - bounding_box[1],  # y size
                bounding_box[5] - bounding_box[2]  # z size
            ) / 2.0

        # Create the control
        if joint_key in target_module.joints:
            target_joint = target_module.joints[joint_key]

            # Get position from joint
            pos = cmds.xform(target_joint, query=True, translation=True, worldSpace=True)

            # Special handling for pole vector
            if target_key == "pole":
                if target_module.module_type == "arm":
                    pos = [pos[0], pos[1], -50.0]  # Put arm pole vector at Z=-50
                else:
                    pos = [pos[0], pos[1] + 50.0, pos[2]]  # Put leg pole vector 50 units up

            # Special handling for FK/IK switch
            if target_key == "fkik_switch":
                if target_module.module_type == "arm":
                    pos = [pos[0], pos[1] + 5.0, pos[2]]  # Put switch 5 units above wrist
                else:
                    if target_module.side == "l":
                        pos = [pos[0] + 5.0, pos[1], pos[2]]  # Put switch 5 units to the right of ankle
                    else:
                        pos = [pos[0] - 5.0, pos[1], pos[2]]  # Put switch 5 units to the left of ankle

            # Create the control
            target_ctrl, target_grp = create_control(
                target_ctrl_name,
                shape_type,
                size,
                color
            )

            # Position the control
            cmds.xform(target_grp, translation=pos, worldSpace=True)

            # Get rotation from joint
            rot = cmds.xform(target_joint, query=True, rotation=True, worldSpace=True)
            cmds.xform(target_grp, rotation=rot, worldSpace=True)

            # Parent appropriately
            if parent:
                cmds.parent(target_grp, parent)
            else:
                cmds.parent(target_grp, target_module.control_grp)

            # For FK controls, connect to corresponding joint
            if "fk_" in target_key and f"fk_{joint_key}" in target_module.joints:
                cmds.parentConstraint(target_ctrl, target_module.joints[f"fk_{joint_key}"], maintainOffset=True)

            # For clavicle control, connect to clavicle joint
            if target_key == "clavicle" and "clavicle" in target_module.joints:
                cmds.parentConstraint(target_ctrl, target_module.joints["clavicle"], maintainOffset=True)

            # For IK controls, some specialized handling:
            if target_key in ["ik_wrist", "ik_ankle"]:
                # Orient constraint to corresponding IK joint
                cmds.orientConstraint(target_ctrl, target_module.joints[target_key], maintainOffset=True)

                # Add attributes for foot controls
                if target_key == "ik_ankle":
                    for attr_name in ["roll", "tilt", "toe", "heel"]:
                        if not cmds.attributeQuery(attr_name, node=target_ctrl, exists=True):
                            cmds.addAttr(target_ctrl, longName=attr_name, attributeType="float", defaultValue=0,
                                         keyable=True)

            # For FK/IK switch, add the blend attribute
            if target_key == "fkik_switch":
                if not cmds.attributeQuery("FkIkBlend", node=target_ctrl, exists=True):
                    cmds.addAttr(target_ctrl, longName="FkIkBlend", attributeType="float", min=0, max=1, defaultValue=1,
                                 keyable=True)

            # Store the control
            target_module.controls[target_key] = target_ctrl
            print(f"Created control {target_key}: {target_ctrl}")
            return target_ctrl

    def _create_mirrored_arm_controls(self, source_module, target_module, colors):
        """
        Create controls for a mirrored arm module with proper sizes, orientations
        and constraints.
        """
        print(f"Creating arm controls for {target_module.module_id}")

        # 1. Create clavicle control if needed
        if "clavicle" in target_module.joints:
            clavicle_joint = target_module.joints["clavicle"]
            clavicle_pos = cmds.xform(clavicle_joint, q=True, t=True, ws=True)

            # Create circle control with Y-up normal as in MEL example
            clavicle_ctrl = cmds.circle(
                name=f"{target_module.module_id}_clavicle_ctrl",
                center=[0, 0, 0],
                normal=[0, 1, 0],
                radius=7.0,
                degree=3
            )[0]

            # Rotate -90 in Z as per the MEL example
            cmds.rotate(0, 0, -90, clavicle_ctrl, relative=True, objectSpace=True)

            # Freeze transformations
            cmds.makeIdentity(clavicle_ctrl, apply=True, translate=True, rotate=True, scale=True)

            # Apply FK color
            shape = cmds.listRelatives(clavicle_ctrl, shapes=True)[0]
            cmds.setAttr(f"{shape}.overrideEnabled", 1)
            cmds.setAttr(f"{shape}.overrideRGBColors", 1)
            cmds.setAttr(f"{shape}.overrideColorR", colors["fk"][0])
            cmds.setAttr(f"{shape}.overrideColorG", colors["fk"][1])
            cmds.setAttr(f"{shape}.overrideColorB", colors["fk"][2])

            # Create group
            clavicle_grp = cmds.group(clavicle_ctrl, name=f"{clavicle_ctrl}_grp")

            # Position to match joint
            cmds.delete(cmds.parentConstraint(clavicle_joint, clavicle_grp, maintainOffset=False))

            # Parent to control group
            cmds.parent(clavicle_grp, target_module.control_grp)
            target_module.controls["clavicle"] = clavicle_ctrl

            # Connect with constraint
            cmds.parentConstraint(clavicle_ctrl, clavicle_joint, maintainOffset=True)
            print(f"Created clavicle control: {clavicle_ctrl}")

        # 2. Create FK controls chain
        fk_joints = ["fk_shoulder", "fk_elbow", "fk_wrist"]
        prev_ctrl = None

        for i, joint_key in enumerate(fk_joints):
            if joint_key in target_module.joints:
                joint = target_module.joints[joint_key]
                joint_name = joint_key.replace("fk_", "")
                ctrl_name = f"{target_module.module_id}_{joint_name}_fk_ctrl"

                # Create control curve with appropriate size
                ctrl, ctrl_grp = create_control(
                    ctrl_name,
                    "circle",
                    6.0 - (i * 0.5),  # Decreasing size down the chain
                    colors["fk"],
                    normal=[1, 0, 0]  # X-axis normal for proper orientation
                )

                # Position and orient control to match joint
                cmds.delete(cmds.parentConstraint(joint, ctrl_grp, maintainOffset=False))

                # Set proper parenting
                if i == 0:  # First control (shoulder)
                    if "clavicle" in target_module.controls:
                        cmds.parent(ctrl_grp, target_module.controls["clavicle"])
                    else:
                        cmds.parent(ctrl_grp, target_module.control_grp)
                else:  # Parent to previous control in chain
                    cmds.parent(ctrl_grp, prev_ctrl)

                # Connect control to joint with constraints
                cmds.parentConstraint(ctrl, joint, maintainOffset=True)

                # Store for the chain
                target_module.controls[joint_key] = ctrl
                prev_ctrl = ctrl
                print(f"Created {joint_key} control: {ctrl}")

        # 3. Set up the proper arm IK handle first
        self._setup_arm_ik_handle(target_module)

        # 4. Create IK wrist control
        if "ik_wrist" in target_module.joints:
            wrist_joint = target_module.joints["ik_wrist"]

            # Create cube control
            wrist_ctrl, wrist_grp = create_control(
                f"{target_module.module_id}_wrist_ik_ctrl",
                "cube",
                3.5,
                colors["ik"]
            )

            # Position and orient
            cmds.delete(cmds.parentConstraint(wrist_joint, wrist_grp, maintainOffset=False))
            cmds.parent(wrist_grp, target_module.control_grp)

            # Store control
            target_module.controls["ik_wrist"] = wrist_ctrl

            # Connect IK handle to wrist control if it exists
            if "ik_handle" in target_module.controls:
                ik_handle = target_module.controls["ik_handle"]
                # Check if it's already parented
                current_parent = cmds.listRelatives(ik_handle, parent=True)
                if not current_parent or current_parent[0] != wrist_ctrl:
                    cmds.parent(ik_handle, wrist_ctrl)
                    print(f"Parented {ik_handle} to {wrist_ctrl}")

            # Orient constraint for IK wrist joint
            cmds.orientConstraint(wrist_ctrl, wrist_joint, maintainOffset=True)
            print(f"Created IK wrist control: {wrist_ctrl}")

        # 5. Create pole vector control
        if "ik_elbow" in target_module.joints:
            elbow_joint = target_module.joints["ik_elbow"]
            elbow_pos = cmds.xform(elbow_joint, q=True, t=True, ws=True)

            pole_ctrl, pole_grp = create_control(
                f"{target_module.module_id}_pole_ctrl",
                "sphere",
                2.5,
                colors["ik"]
            )

            # Position the pole vector away from the elbow
            cmds.xform(pole_grp, t=elbow_pos, ws=True)
            cmds.setAttr(f"{pole_ctrl}.translateZ", -50)  # Move backwards for arms

            # Freeze transformations to "bake in" the position
            cmds.makeIdentity(pole_ctrl, apply=True, t=True)

            # Parent to control group
            cmds.parent(pole_grp, target_module.control_grp)
            target_module.controls["pole"] = pole_ctrl

            # Create pole vector constraint if IK handle exists
            if "ik_handle" in target_module.controls:
                cmds.poleVectorConstraint(pole_ctrl, target_module.controls["ik_handle"])

            print(f"Created pole vector control: {pole_ctrl}")

        # 6. Create FK/IK Switch - KEEP YELLOW color
        if "wrist" in target_module.joints:
            switch_joint = target_module.joints["wrist"]
            switch_pos = cmds.xform(switch_joint, q=True, t=True, ws=True)

            # Create switch control
            switch_ctrl = cmds.curve(
                name=f"{target_module.module_id}_fkik_switch",
                p=[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (-1, 0, -1)],
                degree=1
            )

            # Scale the control
            cmds.setAttr(f"{switch_ctrl}.scaleX", 1.5)
            cmds.setAttr(f"{switch_ctrl}.scaleY", 1.5)
            cmds.setAttr(f"{switch_ctrl}.scaleZ", 1.5)

            # Apply YELLOW color (not red)
            shape = cmds.listRelatives(switch_ctrl, shapes=True)[0]
            cmds.setAttr(f"{shape}.overrideEnabled", 1)
            cmds.setAttr(f"{shape}.overrideRGBColors", 1)
            cmds.setAttr(f"{shape}.overrideColorR", 1.0)
            cmds.setAttr(f"{shape}.overrideColorG", 1.0)
            cmds.setAttr(f"{shape}.overrideColorB", 0.0)

            # Create group
            switch_grp = cmds.group(switch_ctrl, name=f"{switch_ctrl}_grp")

            # Position above wrist
            offset_pos = [switch_pos[0], switch_pos[1] + 5.0, switch_pos[2]]
            cmds.xform(switch_grp, t=offset_pos, ws=True)

            # Rotate to face forward
            cmds.xform(switch_grp, ro=[90, 0, 0], ws=True)

            # Parent to control group
            cmds.parent(switch_grp, target_module.control_grp)

            # Add FK/IK blend attribute
            if not cmds.attributeQuery("FkIkBlend", node=switch_ctrl, exists=True):
                cmds.addAttr(switch_ctrl, ln="FkIkBlend", at="float", min=0, max=1, dv=1, k=True)

            # Store control
            target_module.controls["fkik_switch"] = switch_ctrl

            # Make switch follow the main joint
            cmds.parentConstraint(
                switch_joint,
                switch_grp,
                mo=True,
                skipRotate=["x", "y", "z"]
            )

            print(f"Created FK/IK switch: {switch_ctrl}")

    def _create_mirrored_leg_controls(self, source_module, target_module, colors):
        """
        Create controls for a mirrored leg module.
        """
        print(f"\nCreating leg controls for {target_module.module_id}")

        # Debug the module's joints to ensure they exist
        print("Leg joints available:")
        for key in ["hip", "knee", "ankle", "foot", "toe", "fk_hip", "fk_knee", "fk_ankle", "ik_hip", "ik_knee",
                    "ik_ankle"]:
            if key in target_module.joints:
                print(f"  {key}: {target_module.joints[key]}")
            else:
                print(f"  MISSING: {key}")

        # 1. Create FK controls chain
        fk_joints = ["fk_hip", "fk_knee", "fk_ankle"]
        prev_ctrl = None

        for i, joint_key in enumerate(fk_joints):
            print(f"Processing FK joint: {joint_key}")
            if joint_key in target_module.joints:
                joint = target_module.joints[joint_key]
                joint_name = joint_key.replace("fk_", "")
                ctrl_name = f"{target_module.module_id}_{joint_name}_fk_ctrl"

                # Create control curve with appropriate size
                ctrl, ctrl_grp = create_control(
                    ctrl_name,
                    "circle",
                    9.0 - (i * 1.5),  # Decreasing size down the chain
                    colors["fk"],
                    normal=[0, 1, 0]  # Y-axis normal for proper orientation
                )

                # Rotate 90 degrees in Z for proper orientation
                cmds.rotate(0, 0, -90, ctrl, r=True, os=True)
                cmds.makeIdentity(ctrl, apply=True, t=True, r=True, s=True)

                # Position and orient control to match joint
                cmds.delete(cmds.parentConstraint(joint, ctrl_grp, maintainOffset=False))

                # Set proper parenting
                if i == 0:  # First control (hip)
                    cmds.parent(ctrl_grp, target_module.control_grp)
                else:  # Parent to previous control in chain
                    cmds.parent(ctrl_grp, prev_ctrl)

                # Connect control to joint with constraints
                cmds.parentConstraint(ctrl, joint, maintainOffset=True)

                # Store for the chain
                target_module.controls[joint_key] = ctrl
                prev_ctrl = ctrl
                print(f"Created {joint_key} control: {ctrl}")
            else:
                print(f"WARNING: Joint {joint_key} not found!")

        # 2. Create or update IK handle for main leg
        print("Setting up IK handle for leg")
        ik_handle_name = f"{target_module.module_id}_leg_ikh"

        # Delete any existing IK handle to ensure clean setup
        if cmds.objExists(ik_handle_name):
            cmds.delete(ik_handle_name)
            print(f"Deleted existing IK handle: {ik_handle_name}")

        if "ik_hip" in target_module.joints and "ik_ankle" in target_module.joints:
            print(f"Creating IK handle from {target_module.joints['ik_hip']} to {target_module.joints['ik_ankle']}")
            ik_handle, effector = cmds.ikHandle(
                name=ik_handle_name,
                startJoint=target_module.joints["ik_hip"],
                endEffector=target_module.joints["ik_ankle"],
                solver="ikRPsolver"
            )
            target_module.controls["ik_handle"] = ik_handle
            print(f"Created IK handle: {ik_handle}")
        else:
            print(f"WARNING: Cannot create IK handle - required joints not found")

        # 3. Create IK ankle control
        print("Creating IK ankle control")
        if "ik_ankle" in target_module.joints:
            ankle_joint = target_module.joints["ik_ankle"]

            # Create cube control
            ankle_ctrl, ankle_grp = create_control(
                f"{target_module.module_id}_ankle_ik_ctrl",
                "cube",
                3.5,
                colors["ik"]
            )

            # Position and orient
            cmds.delete(cmds.parentConstraint(ankle_joint, ankle_grp, maintainOffset=False))
            cmds.parent(ankle_grp, target_module.control_grp)

            # Store control
            target_module.controls["ik_ankle"] = ankle_ctrl

            # Add foot attributes
            for attr_name in ["roll", "tilt", "toe", "heel"]:
                if not cmds.attributeQuery(attr_name, node=ankle_ctrl, exists=True):
                    cmds.addAttr(ankle_ctrl, ln=attr_name, at="float", dv=0, k=True)

            # Setup foot roll system
            self._setup_mirrored_foot_roll(target_module, ankle_ctrl)

            print(f"Created IK ankle control: {ankle_ctrl}")
        else:
            print(f"WARNING: Joint ik_ankle not found!")

        # 4. Create pole vector control - CORRECTLY POSITIONED AT KNEE + OFFSET
        print("Creating pole vector control")
        if "ik_knee" in target_module.joints:
            knee_joint = target_module.joints["ik_knee"]

            # Create the pole vector control
            pole_ctrl, pole_grp = create_control(
                f"{target_module.module_id}_pole_ctrl",
                "sphere",
                2.5,
                colors["ik"]
            )

            # First position at knee joint
            cmds.delete(cmds.parentConstraint(knee_joint, pole_grp, maintainOffset=False))

            # Then move it forward by 50 units in Y axis (same as left side but mirrored)
            cmds.move(0, -50, 0, pole_ctrl, relative=True, objectSpace=True)

            # Freeze transformations to "bake in" the offset
            cmds.makeIdentity(pole_ctrl, apply=True, translate=True)

            # Parent to control group
            cmds.parent(pole_grp, target_module.control_grp)
            target_module.controls["pole"] = pole_ctrl

            # Create pole vector constraint
            if "ik_handle" in target_module.controls:
                cmds.poleVectorConstraint(pole_ctrl, target_module.controls["ik_handle"])
                print(f"Created pole vector constraint from {pole_ctrl} to {target_module.controls['ik_handle']}")

            print(f"Created pole vector control: {pole_ctrl}")
        else:
            print(f"WARNING: Joint ik_knee not found!")

        # 5. Create FK/IK Switch - KEEP YELLOW color
        print("Creating FK/IK switch")
        if "ankle" in target_module.joints:
            switch_joint = target_module.joints["ankle"]
            switch_pos = cmds.xform(switch_joint, q=True, t=True, ws=True)

            # Create switch control
            switch_ctrl = cmds.curve(
                name=f"{target_module.module_id}_fkik_switch",
                p=[(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (-1, 0, -1)],
                degree=1
            )

            # Scale the control
            cmds.setAttr(f"{switch_ctrl}.scaleX", 1.5)
            cmds.setAttr(f"{switch_ctrl}.scaleY", 1.5)
            cmds.setAttr(f"{switch_ctrl}.scaleZ", 1.5)

            # Apply YELLOW color (not red)
            shape = cmds.listRelatives(switch_ctrl, shapes=True)[0]
            cmds.setAttr(f"{shape}.overrideEnabled", 1)
            cmds.setAttr(f"{shape}.overrideRGBColors", 1)
            cmds.setAttr(f"{shape}.overrideColorR", 1.0)
            cmds.setAttr(f"{shape}.overrideColorG", 1.0)
            cmds.setAttr(f"{shape}.overrideColorB", 0.0)

            # Create group
            switch_grp = cmds.group(switch_ctrl, name=f"{switch_ctrl}_grp")

            # Position to the side of ankle
            offset_pos = [switch_pos[0] - 5.0, switch_pos[1], switch_pos[2]]  # Moved to the left for right leg
            cmds.xform(switch_grp, t=offset_pos, ws=True)

            # Rotate to face forward
            cmds.xform(switch_grp, ro=[90, 0, 0], ws=True)

            # Parent to control group
            cmds.parent(switch_grp, target_module.control_grp)

            # Add FK/IK blend attribute
            if not cmds.attributeQuery("FkIkBlend", node=switch_ctrl, exists=True):
                cmds.addAttr(switch_ctrl, ln="FkIkBlend", at="float", min=0, max=1, dv=1, k=True)

            # Store control
            target_module.controls["fkik_switch"] = switch_ctrl

            # Make switch follow the main joint
            cmds.parentConstraint(
                switch_joint,
                switch_grp,
                mo=True,
                skipRotate=["x", "y", "z"]
            )

            print(f"Created FK/IK switch: {switch_ctrl}")
        else:
            print(f"WARNING: Joint ankle not found!")

    def _setup_mirrored_foot_roll(self, target_module, ankle_ctrl):
        """
        Set up the foot roll system for a mirrored leg module.

        Args:
            target_module: Target leg module
            ankle_ctrl: The ankle IK control
        """
        print(f"\nSetting up foot roll system for {target_module.module_id}")

        # Check if we have the necessary joints
        if not all(key in target_module.joints for key in ["ik_ankle", "ik_foot", "ik_toe"]):
            print("Missing required joints for foot roll setup")
            return

        # Get joint positions
        ankle_pos = cmds.xform(target_module.joints["ik_ankle"], q=True, t=True, ws=True)
        foot_pos = cmds.xform(target_module.joints["ik_foot"], q=True, t=True, ws=True)
        toe_pos = cmds.xform(target_module.joints["ik_toe"], q=True, t=True, ws=True)

        # Estimate heel position if not available (behind the foot joint)
        heel_pos = [foot_pos[0], foot_pos[1], foot_pos[2] - 5.0]

        # Delete any existing foot roll components to recreate them cleanly
        for name in [
            f"{target_module.module_id}_foot_roll_grp",
            f"{target_module.module_id}_heel_pivot_grp",
            f"{target_module.module_id}_toe_pivot_grp",
            f"{target_module.module_id}_ball_pivot_grp",
            f"{target_module.module_id}_ankle_pivot_grp",
            f"{target_module.module_id}_ankle_foot_ikh",
            f"{target_module.module_id}_foot_toe_ikh"
        ]:
            if cmds.objExists(name):
                cmds.delete(name)
                print(f"Deleted existing component: {name}")

        # Create IK handles first
        ankle_foot_ik, ankle_foot_eff = cmds.ikHandle(
            name=f"{target_module.module_id}_ankle_foot_ikh",
            startJoint=target_module.joints["ik_ankle"],
            endEffector=target_module.joints["ik_foot"],
            solver="ikSCsolver"
        )

        foot_toe_ik, foot_toe_eff = cmds.ikHandle(
            name=f"{target_module.module_id}_foot_toe_ikh",
            startJoint=target_module.joints["ik_foot"],
            endEffector=target_module.joints["ik_toe"],
            solver="ikSCsolver"
        )

        # Create the pivot groups
        foot_roll_grp = cmds.group(empty=True, name=f"{target_module.module_id}_foot_roll_grp")
        heel_grp = cmds.group(empty=True, name=f"{target_module.module_id}_heel_pivot_grp")
        toe_grp = cmds.group(empty=True, name=f"{target_module.module_id}_toe_pivot_grp")
        ball_grp = cmds.group(empty=True, name=f"{target_module.module_id}_ball_pivot_grp")
        ankle_grp = cmds.group(empty=True, name=f"{target_module.module_id}_ankle_pivot_grp")

        # Position the groups
        cmds.xform(foot_roll_grp, t=[0, 0, 0], ws=True)
        cmds.xform(heel_grp, t=heel_pos, ws=True)
        cmds.xform(toe_grp, t=toe_pos, ws=True)
        cmds.xform(ball_grp, t=foot_pos, ws=True)
        cmds.xform(ankle_grp, t=ankle_pos, ws=True)

        # Create hierarchy
        cmds.parent(foot_roll_grp, target_module.control_grp)
        cmds.parent(heel_grp, foot_roll_grp)
        cmds.parent(toe_grp, heel_grp)
        cmds.parent(ball_grp, toe_grp)
        cmds.parent(ankle_grp, ball_grp)

        # Parent IK handles to the correct pivot groups
        print(f"Parenting {foot_toe_ik} to {ball_grp}")
        cmds.parent(foot_toe_ik, ball_grp)

        print(f"Parenting {ankle_foot_ik} to {ankle_grp}")
        cmds.parent(ankle_foot_ik, ankle_grp)

        # Parent main leg IK handle to ankle group
        if "ik_handle" in target_module.controls:
            print(f"Parenting {target_module.controls['ik_handle']} to {ankle_grp}")
            cmds.parent(target_module.controls["ik_handle"], ankle_grp)

        # Store references
        target_module.controls["foot_roll_grp"] = foot_roll_grp
        target_module.controls["heel_pivot"] = heel_grp
        target_module.controls["toe_pivot"] = toe_grp
        target_module.controls["ball_pivot"] = ball_grp
        target_module.controls["ankle_pivot"] = ankle_grp
        target_module.controls["ankle_foot_ik"] = ankle_foot_ik
        target_module.controls["foot_toe_ik"] = foot_toe_ik

        # Connect ankle control to foot roll group
        cmds.parentConstraint(
            ankle_ctrl,
            foot_roll_grp,
            maintainOffset=True,
            name=f"{target_module.module_id}_footRoll_parentConstraint"
        )

        # Set up the foot roll attributes
        if all(key in target_module.controls for key in ["heel_pivot", "toe_pivot", "ball_pivot"]):
            # Create utility nodes for foot roll
            heel_cond = cmds.createNode("condition", name=f"{target_module.module_id}_heel_condition")
            cmds.setAttr(f"{heel_cond}.operation", 4)  # Less than
            cmds.setAttr(f"{heel_cond}.colorIfFalseR", 0)
            cmds.setAttr(f"{heel_cond}.secondTerm", 0)

            # Connect roll attribute to condition
            cmds.connectAttr(f"{ankle_ctrl}.roll", f"{heel_cond}.firstTerm")

            # For negative values (heel roll)
            neg_roll = cmds.createNode("multiplyDivide", name=f"{target_module.module_id}_neg_roll_mult")
            cmds.setAttr(f"{neg_roll}.input2X", -1)
            cmds.connectAttr(f"{ankle_ctrl}.roll", f"{neg_roll}.input1X")
            cmds.connectAttr(f"{neg_roll}.outputX", f"{heel_cond}.colorIfTrueR")

            # Connect to heel pivot
            cmds.connectAttr(f"{heel_cond}.outColorR", f"{target_module.controls['heel_pivot']}.rotateX")

            # Set up ball and toe roll
            ball_roll_threshold = 30.0

            # Ball roll (0 to threshold)
            ball_cond = cmds.createNode("condition", name=f"{target_module.module_id}_ball_condition")
            cmds.setAttr(f"{ball_cond}.operation", 2)  # Greater than
            cmds.setAttr(f"{ball_cond}.secondTerm", 0)

            ball_clamp = cmds.createNode("clamp", name=f"{target_module.module_id}_ball_clamp")
            cmds.setAttr(f"{ball_clamp}.minR", 0)
            cmds.setAttr(f"{ball_clamp}.maxR", ball_roll_threshold)

            cmds.connectAttr(f"{ankle_ctrl}.roll", f"{ball_cond}.firstTerm")
            cmds.connectAttr(f"{ankle_ctrl}.roll", f"{ball_clamp}.inputR")

            cmds.connectAttr(f"{ball_clamp}.outputR", f"{ball_cond}.colorIfTrueR")
            cmds.setAttr(f"{ball_cond}.colorIfFalseR", 0)

            cmds.connectAttr(f"{ball_cond}.outColorR", f"{target_module.controls['ball_pivot']}.rotateX")

            # Toe roll (beyond threshold)
            toe_cond = cmds.createNode("condition", name=f"{target_module.module_id}_toe_condition")
            cmds.setAttr(f"{toe_cond}.operation", 2)  # Greater than
            cmds.setAttr(f"{toe_cond}.secondTerm", ball_roll_threshold)

            cmds.connectAttr(f"{ankle_ctrl}.roll", f"{toe_cond}.firstTerm")

            toe_offset = cmds.createNode("plusMinusAverage", name=f"{target_module.module_id}_toe_offset")
            cmds.setAttr(f"{toe_offset}.operation", 2)  # Subtract
            cmds.connectAttr(f"{ankle_ctrl}.roll", f"{toe_offset}.input1D[0]")
            cmds.setAttr(f"{toe_offset}.input1D[1]", ball_roll_threshold)

            cmds.connectAttr(f"{toe_offset}.output1D", f"{toe_cond}.colorIfTrueR")
            cmds.setAttr(f"{toe_cond}.colorIfFalseR", 0)

            # Combine automatic toe roll with manual control
            toe_combine = cmds.createNode("plusMinusAverage", name=f"{target_module.module_id}_toe_combine")
            cmds.setAttr(f"{toe_combine}.operation", 1)  # Add

            cmds.connectAttr(f"{toe_cond}.outColorR", f"{toe_combine}.input1D[0]")
            cmds.connectAttr(f"{ankle_ctrl}.toe", f"{toe_combine}.input1D[1]")

            cmds.connectAttr(f"{toe_combine}.output1D", f"{target_module.controls['toe_pivot']}.rotateX")

            # Tilt (Z rotation)
            cmds.connectAttr(f"{ankle_ctrl}.tilt", f"{target_module.controls['ball_pivot']}.rotateZ")

            # Heel (Y rotation)
            cmds.connectAttr(f"{ankle_ctrl}.heel", f"{target_module.controls['heel_pivot']}.rotateY")

        print(f"Foot roll setup complete for {target_module.module_id}")

    def _setup_arm_ik_handle(self, target_module):
        """
        Properly set up the IK handle for an arm module.
        """
        print(f"\nSetting up IK handle for arm module: {target_module.module_id}")

        # Check if we have the necessary joints
        if not all(key in target_module.joints for key in ["ik_shoulder", "ik_wrist"]):
            print("Missing required IK joints for arm, cannot create IK handle")
            return None

        # Create or retrieve the IK handle
        ik_handle_name = f"{target_module.module_id}_arm_ikh"
        if cmds.objExists(ik_handle_name):
            # Delete existing handle - easier to recreate properly than fix
            cmds.delete(ik_handle_name)
            print(f"Deleted existing IK handle to recreate properly")

        # Create the IK handle
        print(
            f"Creating new IK handle from {target_module.joints['ik_shoulder']} to {target_module.joints['ik_wrist']}")
        ik_handle, effector = cmds.ikHandle(
            name=ik_handle_name,
            startJoint=target_module.joints["ik_shoulder"],
            endEffector=target_module.joints["ik_wrist"],
            solver="ikRPsolver"
        )

        # Store in controls dictionary
        target_module.controls["ik_handle"] = ik_handle

        print(f"IK handle setup complete: {ik_handle}")
        return ik_handle

    def _mirror_fk_ik_joints(self, source_module, target_module):
        """
        Mirror the FK and IK joint chains from source (left) to target (right) module
        using Maya's mirrorJoint command. Only applies to legs or if the joints don't
        already exist in the target module.

        Args:
            source_module: Source module (left side)
            target_module: Target module (right side)
        """
        print(f"\n=== CHECKING FOR MISSING FK/IK CHAINS FOR {target_module.module_id} ===")

        # Define keys based on module type
        limb_type = source_module.module_type
        if limb_type == "arm":
            fk_root_key = "fk_shoulder"
            ik_root_key = "ik_shoulder"
        else:  # leg
            fk_root_key = "fk_hip"
            ik_root_key = "ik_hip"

        # Check if FK and IK chains already exist in target module
        if fk_root_key in target_module.joints and ik_root_key in target_module.joints:
            print(f"FK and IK chains already exist for {target_module.module_id}, skipping")
            return True

        # Check for source FK root
        if fk_root_key not in source_module.joints:
            print(f"Source module missing FK root joint: {fk_root_key}")
            return False

        # Check for source IK root
        if ik_root_key not in source_module.joints:
            print(f"Source module missing IK root joint: {ik_root_key}")
            return False

        print(f"\n=== MIRRORING FK/IK CHAINS FROM {source_module.module_id} TO {target_module.module_id} ===")

        # Get the source FK and IK root joints
        fk_root = source_module.joints[fk_root_key]
        ik_root = source_module.joints[ik_root_key]

        # 1. Mirror the FK chain
        print(f"Mirroring FK chain from {fk_root}")
        cmds.select(clear=True)
        cmds.select(fk_root)

        try:
            fk_mirrored = cmds.mirrorJoint(
                mirrorYZ=True,
                mirrorBehavior=True,
                searchReplace=[f"{source_module.side}_", f"{target_module.side}_"]
            )
            print(f"FK mirror result: {fk_mirrored}")

            # Parent to target module's joint group
            mirrored_root = fk_mirrored[0]
            current_parent = cmds.listRelatives(mirrored_root, parent=True)
            if current_parent:
                cmds.parent(mirrored_root, world=True)
            cmds.parent(mirrored_root, target_module.joint_grp)
            print(f"Parented {mirrored_root} to {target_module.joint_grp}")

            # Update target module's joints dictionary
            if limb_type == "arm":
                # Map the mirrored FK joints to the dictionary
                target_module.joints["fk_shoulder"] = mirrored_root
                children = cmds.listRelatives(mirrored_root, allDescendents=True, type="joint") or []

                # Map the rest of the joints
                for child in children:
                    if "_elbow_fk_" in child:
                        target_module.joints["fk_elbow"] = child
                        print(f"Mapped fk_elbow to {child}")
                    elif "_wrist_fk_" in child:
                        target_module.joints["fk_wrist"] = child
                        print(f"Mapped fk_wrist to {child}")
                    elif "_hand_fk_" in child:
                        target_module.joints["fk_hand"] = child
                        print(f"Mapped fk_hand to {child}")
            else:  # leg
                # Map the mirrored FK joints to the dictionary
                target_module.joints["fk_hip"] = mirrored_root
                children = cmds.listRelatives(mirrored_root, allDescendents=True, type="joint") or []

                # Map the rest of the joints
                for child in children:
                    if "_knee_fk_" in child:
                        target_module.joints["fk_knee"] = child
                        print(f"Mapped fk_knee to {child}")
                    elif "_ankle_fk_" in child:
                        target_module.joints["fk_ankle"] = child
                        print(f"Mapped fk_ankle to {child}")
                    elif "_foot_fk_" in child:
                        target_module.joints["fk_foot"] = child
                        print(f"Mapped fk_foot to {child}")
                    elif "_toe_fk_" in child:
                        target_module.joints["fk_toe"] = child
                        print(f"Mapped fk_toe to {child}")

        except Exception as e:
            print(f"Error mirroring FK chain: {str(e)}")
            return False

        # 2. Mirror the IK chain
        print(f"\nMirroring IK chain from {ik_root}")
        cmds.select(clear=True)
        cmds.select(ik_root)

        try:
            ik_mirrored = cmds.mirrorJoint(
                mirrorYZ=True,
                mirrorBehavior=True,
                searchReplace=[f"{source_module.side}_", f"{target_module.side}_"]
            )
            print(f"IK mirror result: {ik_mirrored}")

            # Parent to target module's joint group
            mirrored_root = ik_mirrored[0]
            current_parent = cmds.listRelatives(mirrored_root, parent=True)
            if current_parent:
                cmds.parent(mirrored_root, world=True)
            cmds.parent(mirrored_root, target_module.joint_grp)
            print(f"Parented {mirrored_root} to {target_module.joint_grp}")

            # Update target module's joints dictionary
            if limb_type == "arm":
                # Map the mirrored IK joints to the dictionary
                target_module.joints["ik_shoulder"] = mirrored_root
                children = cmds.listRelatives(mirrored_root, allDescendents=True, type="joint") or []

                # Map the rest of the joints
                for child in children:
                    if "_elbow_ik_" in child:
                        target_module.joints["ik_elbow"] = child
                        print(f"Mapped ik_elbow to {child}")
                    elif "_wrist_ik_" in child:
                        target_module.joints["ik_wrist"] = child
                        print(f"Mapped ik_wrist to {child}")
                    elif "_hand_ik_" in child:
                        target_module.joints["ik_hand"] = child
                        print(f"Mapped ik_hand to {child}")
            else:  # leg
                # Map the mirrored IK joints to the dictionary
                target_module.joints["ik_hip"] = mirrored_root
                children = cmds.listRelatives(mirrored_root, allDescendents=True, type="joint") or []

                # Map the rest of the joints
                for child in children:
                    if "_knee_ik_" in child:
                        target_module.joints["ik_knee"] = child
                        print(f"Mapped ik_knee to {child}")
                    elif "_ankle_ik_" in child:
                        target_module.joints["ik_ankle"] = child
                        print(f"Mapped ik_ankle to {child}")
                    elif "_foot_ik_" in child:
                        target_module.joints["ik_foot"] = child
                        print(f"Mapped ik_foot to {child}")
                    elif "_toe_ik_" in child:
                        target_module.joints["ik_toe"] = child
                        print(f"Mapped ik_toe to {child}")

        except Exception as e:
            print(f"Error mirroring IK chain: {str(e)}")
            return False

        print(f"=== FK/IK CHAIN MIRRORING COMPLETE: {source_module.module_id} to {target_module.module_id} ===\n")
        return True