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
        Mirror left side modules to right side using Maya's native mirrorJoint command.
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
            print(f"Processing mirrored module: {right_module.module_id}")

            # 3. Mirror the joints using the _mirror_joints_only method
            self._mirror_joints_only(left_module, right_module)

            # 4. Mirror the controls
            self._mirror_controls(left_module, right_module)

        return mirrored_count

    def _mirror_guides(self, source_module, target_module):
        """
        Mirror guides from source module to target module.
        """
        # 1. Make sure both modules have guide groups
        if not source_module.guide_grp or not target_module.guide_grp:
            print("Error: Guide groups not found")
            return

        # 2. For each guide in the source module
        for guide_name, guide in source_module.guides.items():
            # Check if corresponding guide exists in target module
            if guide_name in target_module.guides and cmds.objExists(guide) and cmds.objExists(
                    target_module.guides[guide_name]):
                target_guide = target_module.guides[guide_name]

                # 3. Get the position of the source guide
                pos = cmds.xform(guide, query=True, translation=True, worldSpace=True)
                rot = cmds.xform(guide, query=True, rotation=True, worldSpace=True)

                # 4. Mirror the position based on the type of guide
                if guide_name == "pole":
                    if source_module.module_type == "arm":
                        # For arms, explicitly set Z to -50 (behind the elbow)
                        mirror_pos = [-pos[0], pos[1], -50.0]
                        print(f"Setting arm pole vector Z to -50.0")
                    else:  # leg
                        # For legs, flip both X and Z
                        mirror_pos = [-pos[0], pos[1], -pos[2]]
                else:
                    # Regular guide mirroring - only flip X
                    mirror_pos = [-pos[0], pos[1], pos[2]]

                # For YZ plane mirroring, flip Y and Z rotations
                mirror_rot = [rot[0], -rot[1], -rot[2]]

                # 5. Apply mirrored values to target guide
                cmds.xform(target_guide, translation=mirror_pos, worldSpace=True)
                cmds.xform(target_guide, rotation=mirror_rot, worldSpace=True)

                print(f"Mirrored guide: {guide_name} from {source_module.module_id} to {target_module.module_id}")
                print(f"  Source position: {pos}")
                print(f"  Mirrored position: {mirror_pos}")

        # 6. Mirror blade guides (up vector guides)
        if hasattr(source_module, 'blade_guides') and hasattr(target_module, 'blade_guides'):
            for guide_name, guide in source_module.blade_guides.items():
                if guide_name in target_module.blade_guides and cmds.objExists(guide) and cmds.objExists(
                        target_module.blade_guides[guide_name]):
                    target_guide = target_module.blade_guides[guide_name]

                    # Get position and rotation
                    pos = cmds.xform(guide, query=True, translation=True, worldSpace=True)
                    rot = cmds.xform(guide, query=True, rotation=True, worldSpace=True)

                    # Mirror position and rotation
                    mirror_pos = [-pos[0], pos[1], pos[2]]
                    mirror_rot = [rot[0], -rot[1], -rot[2]]

                    # Apply to target blade guide
                    cmds.xform(target_guide, translation=mirror_pos, worldSpace=True)
                    cmds.xform(target_guide, rotation=mirror_rot, worldSpace=True)

                    print(
                        f"Mirrored blade guide: {guide_name} from {source_module.module_id} to {target_module.module_id}")

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

    def _setup_mirrored_constraints(self, source_module, target_module):
        """
        Set up constraints for mirrored controls to their corresponding joints.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        print(f"Setting up constraints for mirrored module: {target_module.module_id}")

        # Handle different constraint setup based on module type
        if target_module.limb_type == "arm":
            # Setup FK constraints
            for joint_name, ctrl_name in [
                ("fk_shoulder", "fk_shoulder"),
                ("fk_elbow", "fk_elbow"),
                ("fk_wrist", "fk_wrist")
            ]:
                if joint_name in target_module.joints and ctrl_name in target_module.controls:
                    joint = target_module.joints[joint_name]
                    ctrl = target_module.controls[ctrl_name]

                    # Delete any existing constraints
                    constraints = cmds.listConnections(joint, source=True, destination=True, type="constraint") or []
                    for constraint in constraints:
                        if cmds.objExists(constraint):
                            cmds.delete(constraint)

                    # Create new constraints
                    print(f"Creating constraints from {ctrl} to {joint}")
                    cmds.orientConstraint(ctrl, joint, maintainOffset=True)
                    cmds.pointConstraint(ctrl, joint, maintainOffset=True)

            # Setup IK constraints
            if "ik_handle" in target_module.controls and "ik_wrist" in target_module.controls:
                ik_handle = target_module.controls["ik_handle"]
                wrist_ctrl = target_module.controls["ik_wrist"]

                # Clear existing constraints
                constraints = cmds.listConnections(ik_handle, source=True, destination=True, type="constraint") or []
                for constraint in constraints:
                    if cmds.objExists(constraint):
                        cmds.delete(constraint)

                # Create new constraints
                print(f"Creating IK constraints for {target_module.module_id}")
                cmds.pointConstraint(wrist_ctrl, ik_handle, maintainOffset=True)

                # Add pole vector constraint
                if "pole" in target_module.controls:
                    pole_ctrl = target_module.controls["pole"]
                    cmds.poleVectorConstraint(pole_ctrl, ik_handle)

                # Orient constraint for IK wrist joint
                if "ik_wrist" in target_module.joints:
                    cmds.orientConstraint(wrist_ctrl, target_module.joints["ik_wrist"], maintainOffset=True)

                # Connect IK hand - make it follow the IK wrist joint
                if "ik_wrist" in target_module.joints and "ik_hand" in target_module.joints:
                    cmds.parentConstraint(target_module.joints["ik_wrist"], target_module.joints["ik_hand"],
                                          maintainOffset=True)

        elif target_module.limb_type == "leg":
            # Setup FK constraints
            for joint_name, ctrl_name in [
                ("fk_hip", "fk_hip"),
                ("fk_knee", "fk_knee"),
                ("fk_ankle", "fk_ankle")
            ]:
                if joint_name in target_module.joints and ctrl_name in target_module.controls:
                    joint = target_module.joints[joint_name]
                    ctrl = target_module.controls[ctrl_name]

                    # Delete any existing constraints
                    constraints = cmds.listConnections(joint, source=True, destination=True, type="constraint") or []
                    for constraint in constraints:
                        if cmds.objExists(constraint):
                            cmds.delete(constraint)

                    # Create new constraints
                    print(f"Creating constraints from {ctrl} to {joint}")
                    cmds.orientConstraint(ctrl, joint, maintainOffset=True)
                    cmds.pointConstraint(ctrl, joint, maintainOffset=True)

            # Connect FK foot and toe to follow the FK ankle
            if "fk_ankle" in target_module.controls:
                ankle_ctrl = target_module.controls["fk_ankle"]
                for jnt in ["fk_foot", "fk_toe"]:
                    if jnt in target_module.joints:
                        # Remove existing constraints
                        constraints = cmds.listConnections(target_module.joints[jnt], source=True, destination=True,
                                                           type="constraint") or []
                        for constraint in constraints:
                            if cmds.objExists(constraint):
                                cmds.delete(constraint)

                        # Create new constraint
                        cmds.parentConstraint(ankle_ctrl, target_module.joints[jnt], maintainOffset=True)

            # Setup IK constraints
            if "ik_handle" in target_module.controls and "pole" in target_module.controls:
                ik_handle = target_module.controls["ik_handle"]
                pole_ctrl = target_module.controls["pole"]

                # Clear existing constraints
                constraints = cmds.listConnections(ik_handle, source=True, destination=True, type="constraint") or []
                for constraint in constraints:
                    if cmds.objExists(constraint):
                        cmds.delete(constraint)

                # Add pole vector constraint
                print(f"Creating pole vector constraint for {target_module.module_id}")
                cmds.poleVectorConstraint(pole_ctrl, ik_handle)

                # Set up foot roll group connection
                if "ik_ankle" in target_module.controls and "foot_roll_grp" in target_module.controls:
                    ankle_ctrl = target_module.controls["ik_ankle"]
                    foot_roll_grp = target_module.controls["foot_roll_grp"]

                    # Remove existing constraints
                    constraints = cmds.listConnections(foot_roll_grp, source=True, destination=True,
                                                       type="constraint") or []
                    for constraint in constraints:
                        if cmds.objExists(constraint):
                            cmds.delete(constraint)

                    # Create parent constraint
                    cmds.parentConstraint(
                        ankle_ctrl,
                        foot_roll_grp,
                        maintainOffset=True,
                        name=f"{target_module.module_id}_footRoll_parentConstraint"
                    )

                # Orient constraint for IK ankle
                if "ik_ankle" in target_module.controls and "ik_ankle" in target_module.joints:
                    ankle_ctrl = target_module.controls["ik_ankle"]
                    ankle_joint = target_module.joints["ik_ankle"]

                    # Remove existing constraints
                    constraints = cmds.listConnections(ankle_joint, source=True, destination=True,
                                                       type="orientConstraint") or []
                    for constraint in constraints:
                        if cmds.objExists(constraint):
                            cmds.delete(constraint)

                    # Create orient constraint
                    cmds.orientConstraint(ankle_ctrl, ankle_joint, maintainOffset=True)

        # Fix FK/IK blending
        if "fkik_switch" in target_module.controls:
            print("Fixing FK/IK blending for mirrored module")
            # Essentially call target_module._setup_ikfk_blending() without duplicating all that code
            target_module._setup_ikfk_blending()

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

    def connect_mirrored_joints(self):
        """
        Connect mirrored joints to establish proper hierarchy.
        Runs after mirroring to ensure limb joints are properly connected to the spine.
        """
        print("\n=== CONNECTING MIRRORED JOINTS ===")

        # Check if a root joint exists
        root_joint_name = f"{self.character_name}_root_jnt"
        root_joint_exists = cmds.objExists(root_joint_name)

        # Find the spine module and key joints
        spine_module = None
        cog_joint = None
        pelvis_joint = None
        chest_joint = None

        for module in self.modules.values():
            if module.module_type == "spine":  # We want the spine module
                spine_module = module
                if "cog" in module.joints and cmds.objExists(module.joints["cog"]):
                    cog_joint = module.joints["cog"]
                if "pelvis" in module.joints and cmds.objExists(module.joints["pelvis"]):
                    pelvis_joint = module.joints["pelvis"]
                if "chest" in module.joints and cmds.objExists(module.joints["chest"]):
                    chest_joint = module.joints["chest"]
                break

        # If no spine module found, we can't establish hierarchy
        if not spine_module:
            print("No spine module found, cannot establish hierarchy")
            return

        # STEP 1: If root joint exists, connect COG to it
        if root_joint_exists and cog_joint:
            try:
                # Check current parent of COG
                cog_parent = cmds.listRelatives(cog_joint, parent=True) or []
                if not cog_parent or cog_parent[0] != root_joint_name:
                    # Reparent COG to root
                    cmds.parent(cog_joint, root_joint_name)
                    print(f"Connected {cog_joint} to {root_joint_name}")
            except Exception as e:
                print(f"Error connecting COG to root: {str(e)}")

        # STEP 2: Connect legs to pelvis
        if pelvis_joint:
            # Find all leg modules (both left and right sides)
            leg_modules = [m for m in self.modules.values() if m.module_type == "leg"]

            for leg_module in leg_modules:
                try:
                    if "hip" in leg_module.joints and cmds.objExists(leg_module.joints["hip"]):
                        hip_joint = leg_module.joints["hip"]
                        # Check current parent
                        hip_parent = cmds.listRelatives(hip_joint, parent=True) or []

                        # Only reparent if needed
                        if not hip_parent or hip_parent[0] != pelvis_joint:
                            # Unparent first to avoid hierarchy issues
                            cmds.parent(hip_joint, world=True)
                            # Then parent to pelvis
                            cmds.parent(hip_joint, pelvis_joint)
                            print(f"Connected {hip_joint} to {pelvis_joint}")
                except Exception as e:
                    print(f"Error connecting hip to pelvis: {str(e)}")

        # STEP 3: Connect arms to chest
        if chest_joint:
            # Find all arm modules (both left and right sides)
            arm_modules = [m for m in self.modules.values() if m.module_type == "arm"]

            for arm_module in arm_modules:
                try:
                    if "clavicle" in arm_module.joints and cmds.objExists(arm_module.joints["clavicle"]):
                        clavicle_joint = arm_module.joints["clavicle"]
                        # Check current parent
                        clavicle_parent = cmds.listRelatives(clavicle_joint, parent=True) or []

                        # Only reparent if needed
                        if not clavicle_parent or clavicle_parent[0] != chest_joint:
                            # Unparent first to avoid hierarchy issues
                            cmds.parent(clavicle_joint, world=True)
                            # Then parent to chest
                            cmds.parent(clavicle_joint, chest_joint)
                            print(f"Connected {clavicle_joint} to {chest_joint}")
                except Exception as e:
                    print(f"Error connecting clavicle to chest: {str(e)}")

        print("=== JOINT CONNECTION COMPLETE ===\n")

    def _mirror_controls(self, source_module, target_module):
        """
        Mirror controls from source module to target module.
        This should be called after joints have been mirrored.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        if not source_module.controls:
            print("Source module has no controls to mirror")
            return

        print(f"\n=== MIRRORING CONTROLS from {source_module.module_id} to {target_module.module_id} ===")

        # Clear target module's controls dictionary
        target_module.controls = {}

        # Create equivalent control structures for the target module
        # Depending on module type, we'll create different controls
        if source_module.module_type == "arm":
            # Create clavicle control if it exists
            if "clavicle" in source_module.controls and "clavicle" in target_module.joints:
                self._mirror_single_control(source_module, target_module, "clavicle", "clavicle")

            # Mirror main controls
            if "clavicle" in target_module.controls:
                parent_control = target_module.controls["clavicle"]
            else:
                parent_control = target_module.control_grp

            # FK controls
            fk_controls = ["fk_shoulder", "fk_elbow", "fk_wrist"]
            for i, ctrl_name in enumerate(fk_controls):
                parent = parent_control if i == 0 else target_module.controls.get(fk_controls[i - 1])
                self._mirror_single_control(source_module, target_module, ctrl_name, fk_controls[i], parent)

            # IK controls
            self._mirror_single_control(source_module, target_module, "ik_wrist", "ik_wrist", target_module.control_grp)
            self._mirror_single_control(source_module, target_module, "pole", "pole", target_module.control_grp)

            # Mirror IK handle if it exists
            if "ik_handle" in source_module.controls and target_module.joint_grp:
                source_ik = source_module.controls["ik_handle"]

                # Create the IK handle on the target side
                if "ik_shoulder" in target_module.joints and "ik_wrist" in target_module.joints:
                    print(f"Creating IK handle for {target_module.module_id}")
                    ik_handle, effector = cmds.ikHandle(
                        name=f"{target_module.module_id}_arm_ikh",
                        startJoint=target_module.joints["ik_shoulder"],
                        endEffector=target_module.joints["ik_wrist"],
                        solver="ikRPsolver"
                    )

                    # Parent to IK wrist control if it exists
                    if "ik_wrist" in target_module.controls:
                        cmds.parent(ik_handle, target_module.controls["ik_wrist"])
                    else:
                        cmds.parent(ik_handle, target_module.control_grp)

                    target_module.controls["ik_handle"] = ik_handle

                    # Set up pole vector constraint
                    if "pole" in target_module.controls:
                        cmds.poleVectorConstraint(
                            target_module.controls["pole"],
                            ik_handle
                        )

            # FKIK Switch
            self._mirror_single_control(source_module, target_module, "fkik_switch", "fkik_switch",
                                        target_module.control_grp)

            # Set up constraints
            if "fkik_switch" in target_module.controls:
                # Create reverse node
                reverse_node = cmds.createNode("reverse", name=f"{target_module.module_id}_fkik_reverse")
                cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend", f"{reverse_node}.inputX")

                # Connect main joint chain to IK/FK
                joint_pairs = [
                    ("shoulder", "ik_shoulder", "fk_shoulder"),
                    ("elbow", "ik_elbow", "fk_elbow"),
                    ("wrist", "ik_wrist", "fk_wrist"),
                    ("hand", "ik_hand", "fk_hand")
                ]

                for bind_joint, ik_joint, fk_joint in joint_pairs:
                    if all(key in target_module.joints for key in [bind_joint, ik_joint, fk_joint]):
                        # Create constraint
                        constraint = cmds.parentConstraint(
                            target_module.joints[ik_joint],
                            target_module.joints[fk_joint],
                            target_module.joints[bind_joint],
                            maintainOffset=True
                        )[0]

                        # Connect weights
                        weights = cmds.parentConstraint(constraint, query=True, weightAliasList=True)
                        if len(weights) == 2:
                            cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend",
                                             f"{constraint}.{weights[0]}")
                            cmds.connectAttr(f"{reverse_node}.outputX", f"{constraint}.{weights[1]}")

        elif source_module.module_type == "leg":
            # Mirror FK controls
            fk_controls = ["fk_hip", "fk_knee", "fk_ankle"]
            for i, ctrl_name in enumerate(fk_controls):
                parent = target_module.control_grp if i == 0 else target_module.controls.get(fk_controls[i - 1])
                self._mirror_single_control(source_module, target_module, ctrl_name, fk_controls[i], parent)

            # Mirror IK controls
            self._mirror_single_control(source_module, target_module, "ik_ankle", "ik_ankle", target_module.control_grp)
            self._mirror_single_control(source_module, target_module, "pole", "pole", target_module.control_grp)

            # Mirror IK handle and foot roll system
            if "ik_handle" in source_module.controls and target_module.joint_grp:
                # Create the IK handle
                if "ik_hip" in target_module.joints and "ik_ankle" in target_module.joints:
                    print(f"Creating IK handle for {target_module.module_id}")
                    ik_handle, effector = cmds.ikHandle(
                        name=f"{target_module.module_id}_leg_ikh",
                        startJoint=target_module.joints["ik_hip"],
                        endEffector=target_module.joints["ik_ankle"],
                        solver="ikRPsolver"
                    )

                    target_module.controls["ik_handle"] = ik_handle

                    # Create foot roll system
                    if "ik_ankle" in target_module.joints and "ik_foot" in target_module.joints and "ik_toe" in target_module.joints:
                        # Create ankle to foot IK handle
                        ankle_foot_ik, ankle_foot_eff = cmds.ikHandle(
                            name=f"{target_module.module_id}_ankle_foot_ikh",
                            startJoint=target_module.joints["ik_ankle"],
                            endEffector=target_module.joints["ik_foot"],
                            solver="ikSCsolver"
                        )

                        # Create foot to toe IK handle
                        foot_toe_ik, foot_toe_eff = cmds.ikHandle(
                            name=f"{target_module.module_id}_foot_toe_ikh",
                            startJoint=target_module.joints["ik_foot"],
                            endEffector=target_module.joints["ik_toe"],
                            solver="ikSCsolver"
                        )

                        # Get position data from joints
                        ankle_pos = cmds.xform(target_module.joints["ik_ankle"], query=True, translation=True,
                                               worldSpace=True)
                        foot_pos = cmds.xform(target_module.joints["ik_foot"], query=True, translation=True,
                                              worldSpace=True)
                        toe_pos = cmds.xform(target_module.joints["ik_toe"], query=True, translation=True,
                                             worldSpace=True)

                        # Get heel position
                        if "heel" in target_module.guides and cmds.objExists(target_module.guides["heel"]):
                            heel_pos = cmds.xform(target_module.guides["heel"], query=True, translation=True,
                                                  worldSpace=True)
                        else:
                            heel_pos = [foot_pos[0], foot_pos[1], foot_pos[2] - 5.0]

                        # Create foot roll hierarchy
                        foot_roll_grp = cmds.group(empty=True, name=f"{target_module.module_id}_foot_roll_grp")
                        heel_grp = cmds.group(empty=True, name=f"{target_module.module_id}_heel_pivot_grp")
                        toe_grp = cmds.group(empty=True, name=f"{target_module.module_id}_toe_pivot_grp")
                        ball_grp = cmds.group(empty=True, name=f"{target_module.module_id}_ball_pivot_grp")
                        ankle_grp = cmds.group(empty=True, name=f"{target_module.module_id}_ankle_pivot_grp")

                        # Position the groups
                        cmds.xform(foot_roll_grp, translation=[0, 0, 0], worldSpace=True)
                        cmds.xform(heel_grp, translation=heel_pos, worldSpace=True)
                        cmds.xform(toe_grp, translation=toe_pos, worldSpace=True)
                        cmds.xform(ball_grp, translation=foot_pos, worldSpace=True)
                        cmds.xform(ankle_grp, translation=ankle_pos, worldSpace=True)

                        # Create hierarchy
                        cmds.parent(foot_roll_grp, target_module.control_grp)
                        cmds.parent(heel_grp, foot_roll_grp)
                        cmds.parent(toe_grp, heel_grp)
                        cmds.parent(ball_grp, toe_grp)
                        cmds.parent(ankle_grp, ball_grp)

                        # Parent IK handles
                        cmds.parent(foot_toe_ik, ball_grp)
                        cmds.parent(ankle_foot_ik, ankle_grp)
                        cmds.parent(ik_handle, ankle_grp)

                        # Store references
                        target_module.controls["foot_roll_grp"] = foot_roll_grp
                        target_module.controls["heel_pivot"] = heel_grp
                        target_module.controls["toe_pivot"] = toe_grp
                        target_module.controls["ball_pivot"] = ball_grp
                        target_module.controls["ankle_pivot"] = ankle_grp
                        target_module.controls["ankle_foot_ik"] = ankle_foot_ik
                        target_module.controls["foot_toe_ik"] = foot_toe_ik

                        # Connect foot roll group to ankle control
                        if "ik_ankle" in target_module.controls:
                            cmds.parentConstraint(
                                target_module.controls["ik_ankle"],
                                foot_roll_grp,
                                maintainOffset=True
                            )

                    # Set up pole vector constraint
                    if "pole" in target_module.controls:
                        cmds.poleVectorConstraint(
                            target_module.controls["pole"],
                            ik_handle
                        )

            # FKIK Switch
            self._mirror_single_control(source_module, target_module, "fkik_switch", "fkik_switch",
                                        target_module.control_grp)

            # Set up constraints
            if "fkik_switch" in target_module.controls:
                # Create reverse node
                reverse_node = cmds.createNode("reverse", name=f"{target_module.module_id}_fkik_reverse")
                cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend", f"{reverse_node}.inputX")

                # Connect main joint chain to IK/FK
                joint_pairs = [
                    ("hip", "ik_hip", "fk_hip"),
                    ("knee", "ik_knee", "fk_knee"),
                    ("ankle", "ik_ankle", "fk_ankle"),
                    ("foot", "ik_foot", "fk_foot"),
                    ("toe", "ik_toe", "fk_toe")
                ]

                for bind_joint, ik_joint, fk_joint in joint_pairs:
                    if all(key in target_module.joints for key in [bind_joint, ik_joint, fk_joint]):
                        # Create constraint
                        constraint = cmds.parentConstraint(
                            target_module.joints[ik_joint],
                            target_module.joints[fk_joint],
                            target_module.joints[bind_joint],
                            maintainOffset=True
                        )[0]

                        # Connect weights
                        weights = cmds.parentConstraint(constraint, query=True, weightAliasList=True)
                        if len(weights) == 2:
                            cmds.connectAttr(f"{target_module.controls['fkik_switch']}.FkIkBlend",
                                             f"{constraint}.{weights[0]}")
                            cmds.connectAttr(f"{reverse_node}.outputX", f"{constraint}.{weights[1]}")

        print(f"=== CONTROL MIRRORING COMPLETE: {source_module.module_id} to {target_module.module_id} ===\n")

    def _mirror_single_control(self, source_module, target_module, source_key, target_key, parent=None):
        """
        Mirror a single control from source module to target module.

        Args:
            source_module: Source module containing the original control
            target_module: Target module to create the mirrored control in
            source_key: Key to look up the control in source_module.controls
            target_key: Key to use for the control in target_module.controls
            parent: Parent for the new control
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

        if "_fk_" in source_ctrl:
            shape_type = "circle"
            color = [0.2, 0.8, 0.2]  # green for FK
        elif "_ik_" in source_ctrl:
            shape_type = "cube"
            color = [0.8, 0.2, 0.8]  # purple for IK
        elif "pole" in source_ctrl:
            shape_type = "sphere"
            color = [0.8, 0.2, 0.8]  # purple for pole vector
        elif "fkik_switch" in source_ctrl:
            shape_type = "square"
            color = [1, 1, 0]  # yellow for switch
        elif "clavicle" in source_ctrl:
            shape_type = "circle"
            color = [0.2, 0.8, 0.2]  # green like FK

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