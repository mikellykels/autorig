"""
Modular Auto-Rig System
Module Manager

This module contains the ModuleManager class which manages rig modules.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import json


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

    def build_mirrored_module(self, left_module, right_module):
        """
        Build and connect all controls for a mirrored module.
        This is much more reliable than trying to mirror controls.

        Args:
            left_module (BaseModule): Source module (left side)
            right_module (BaseModule): Target module (right side)
        """
        print(f"\n=== BUILDING MIRRORED MODULE {right_module.module_id} FROM {left_module.module_id} ===")

        # Verify modules are compatible
        if left_module.module_type != right_module.module_type:
            print(f"Module types don't match: {left_module.module_type} vs {right_module.module_type}")
            return False

        # Check if we already have joints before proceeding
        if not right_module.joints:
            print("No joints found in target module - mirroring joints first")
            self._mirror_joints(left_module, right_module)
            self._mirror_ik_handles(left_module, right_module)

        # Store important references before clearing controls
        ik_handle = right_module.controls.get("ik_handle", None)
        foot_roll_grp = right_module.controls.get("foot_roll_grp", None)
        heel_pivot = right_module.controls.get("heel_pivot", None)
        toe_pivot = right_module.controls.get("toe_pivot", None)
        ball_pivot = right_module.controls.get("ball_pivot", None)
        ankle_pivot = right_module.controls.get("ankle_pivot", None)
        ankle_foot_ik = right_module.controls.get("ankle_foot_ik", None)
        foot_toe_ik = right_module.controls.get("foot_toe_ik", None)

        # Clear existing controls excluding the IK handles and foot roll groups
        if right_module.controls:
            print("Clearing existing controls in target module (preserving IK handles and foot roll groups)")
            preserved_nodes = ["ik_handle", "foot_roll_grp", "heel_pivot", "toe_pivot",
                               "ball_pivot", "ankle_pivot", "ankle_foot_ik", "foot_toe_ik"]

            for ctrl_name, ctrl in list(right_module.controls.items()):
                if ctrl_name in preserved_nodes:
                    # Skip preserved nodes
                    continue

                if cmds.objExists(ctrl):
                    grp_name = f"{ctrl}_grp"
                    if cmds.objExists(grp_name):
                        print(f"Deleting control group: {grp_name}")
                        cmds.delete(grp_name)
                    else:
                        print(f"Deleting control: {ctrl}")
                        cmds.delete(ctrl)

            # Clear and then restore preserved controls
            controls_backup = {}
            for node in preserved_nodes:
                if node in right_module.controls:
                    controls_backup[node] = right_module.controls[node]

            right_module.controls = {}

            # Restore preserved nodes
            for node, value in controls_backup.items():
                if cmds.objExists(value):  # Only restore if the node still exists
                    right_module.controls[node] = value
                    print(f"Preserved control: {node} = {value}")

        # Now call the appropriate creation method based on module type
        if right_module.module_type == "leg":
            print("Building leg controls for mirrored module")
            right_module._create_leg_controls()
            right_module._create_fkik_switch()

            # Set up IK constraints
            self._setup_mirrored_ik_constraints_for_leg(right_module)

            right_module._setup_ikfk_blending()
            right_module._finalize_fkik_switch()

            # Fix hip orientation
            print("Fixing hip orientation for mirrored leg")
            right_module._fix_hip_joint_orientation()

        elif right_module.module_type == "arm":
            print("Building arm controls for mirrored module")
            right_module._create_arm_controls()
            right_module._create_fkik_switch()

            # Set up IK constraints
            self._setup_mirrored_ik_constraints_for_arm(right_module)

            right_module._setup_ikfk_blending()
            right_module._finalize_fkik_switch()

        print(f"=== MIRRORED MODULE BUILD COMPLETE: {right_module.module_id} ===\n")
        return True

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
            print(f"Processing mirrored module: {right_module.module_id}")

            # 3. Mirror based on the stage of rig creation
            # 3a. If guides exist for the left module, mirror them
            if left_module.guides and not right_module.guides:
                right_module.create_guides()
                self._mirror_guides(left_module, right_module)

            # 3b. Check if the left module is fully built (has controls)
            left_built = len(left_module.controls) > 0

            if left_built:
                # Use the completely new approach for building mirrored controls
                self.build_mirrored_module(left_module, right_module)

        return mirrored_count

    def _mirror_guides(self, source_module, target_module):
        """
        Mirror guides from source module to target module.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
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

                # 4. Mirror the position - negate X coordinate for YZ plane mirroring
                mirror_pos = [-pos[0], pos[1], pos[2]]

                # 5. Mirror the rotation - negate appropriate rotation values
                # For YZ plane, negate Y and Z rotations
                mirror_rot = [rot[0], -rot[1], -rot[2]]

                # 6. Apply mirrored values to target guide
                cmds.xform(target_guide, translation=mirror_pos, worldSpace=True)
                cmds.xform(target_guide, rotation=mirror_rot, worldSpace=True)

                print(f"Mirrored guide: {guide_name} from {source_module.module_id} to {target_module.module_id}")

    def _mirror_joints(self, source_module, target_module):
        """
        Mirror joints from source module to target module using Maya's native mirror joint command.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        # Make sure both modules have joints
        if not source_module.joints:
            print("Error: Source joints not found")
            return

        print(f"\n=== MIRRORING JOINTS from {source_module.module_id} to {target_module.module_id} ===")

        # Determine joint chains based on module type
        if source_module.module_type == "arm":
            main_chain = ["shoulder", "elbow", "wrist", "hand"]
        elif source_module.module_type == "leg":
            main_chain = ["hip", "knee", "ankle", "foot", "toe"]
        else:
            print("Not a limb module, skipping")
            return

        # Get joint groups for each module
        source_joint_grp = source_module.joint_grp
        target_joint_grp = target_module.joint_grp

        if not cmds.objExists(source_joint_grp) or not cmds.objExists(target_joint_grp):
            print(f"Joint groups do not exist: {source_joint_grp} or {target_joint_grp}")
            return

        print(f"Source joint group: {source_joint_grp}")
        print(f"Target joint group: {target_joint_grp}")

        # Process each chain type: main, IK, and FK
        joint_prefixes = ["", "ik_", "fk_"]

        for prefix in joint_prefixes:
            print(f"\n--- Processing chain with prefix: '{prefix}' ---")

            # Get source root joint
            root_joint_name = main_chain[0]
            source_key = f"{prefix}{root_joint_name}"

            if source_key not in source_module.joints or not cmds.objExists(source_module.joints[source_key]):
                print(f"Source joint {source_key} not found, skipping chain")
                continue

            source_root_joint = source_module.joints[source_key]
            print(f"Root joint: {source_root_joint}")

            # Debug: Print all joints in this chain
            for joint_name in main_chain:
                joint_key = f"{prefix}{joint_name}"
                if joint_key in source_module.joints:
                    print(f"Chain includes {joint_key}: {source_module.joints[joint_key]}")

            # Delete existing target joints of this type if they exist
            for joint_name in main_chain:
                target_key = f"{prefix}{joint_name}"
                if target_key in target_module.joints and cmds.objExists(target_module.joints[target_key]):
                    print(f"Deleting existing target joint: {target_module.joints[target_key]}")
                    cmds.delete(target_module.joints[target_key])

            # Use Maya's native mirror joint command
            print(f"Mirroring joint chain using native Maya mirrorJoint command")
            try:
                # Make sure the joint is visible for selection
                cmds.setAttr(f"{source_root_joint}.visibility", 1)

                # Select the source root joint
                cmds.select(source_root_joint, replace=True)
                selected = cmds.ls(selection=True)
                print(f"Selected for mirroring: {selected}")

                # Mirror across YZ plane with proper behavior
                mirrored_joints = cmds.mirrorJoint(
                    mirrorYZ=True,  # Mirror across YZ plane (flip X)
                    mirrorBehavior=True,  # Mirror orientation behavior
                    searchReplace=[f"{source_module.side}_", f"{target_module.side}_"]  # Replace l_ with r_ etc.
                )

                print(f"Successfully mirrored joints: {mirrored_joints}")

                # Update the target module's joint dictionary with the new joints
                for i, joint_name in enumerate(main_chain):
                    if i < len(mirrored_joints):
                        target_key = f"{prefix}{joint_name}"
                        # Store short name to avoid path issues
                        mirrored_joint_name = mirrored_joints[i].split('|')[-1]
                        target_module.joints[target_key] = mirrored_joint_name
                        print(f"Updated target joint: {target_key} = {mirrored_joint_name}")

                # Reparent the mirrored joints to the target joint group
                if mirrored_joints:
                    root_mirrored = mirrored_joints[0]
                    print(f"Reparenting {root_mirrored} to {target_joint_grp}")
                    cmds.parent(root_mirrored, target_joint_grp)

            except Exception as e:
                print(f"Error mirroring joints: {str(e)}")
                import traceback
                traceback.print_exc()

        print(f"=== JOINT MIRRORING COMPLETE: {source_module.module_id} to {target_module.module_id} ===\n")
        return True

    def _mirror_controls(self, source_module, target_module):
        """
        Mirror controls from source module to target module.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        # Make sure both modules have controls
        if not source_module.controls or not target_module.controls:
            print("Error: Controls not found in one or both modules")
            return

        print(f"Mirroring controls from {source_module.module_id} to {target_module.module_id}")

        # Common control types between arms and legs
        control_types = ["fk_", "ik_", "pole"]

        # Add specific control types based on module type
        if source_module.module_type == "arm":
            control_names = [
                "fk_shoulder", "fk_elbow", "fk_wrist",
                "ik_wrist", "pole", "fkik_switch"
            ]
        elif source_module.module_type == "leg":
            control_names = [
                "fk_hip", "fk_knee", "fk_ankle",
                "ik_ankle", "pole", "fkik_switch"
            ]
        else:
            return  # Skip non-limb modules

        # Mirror each control
        for control_name in control_names:
            # Skip if source or target control doesn't exist
            if (control_name not in source_module.controls or
                    control_name not in target_module.controls or
                    not cmds.objExists(source_module.controls[control_name]) or
                    not cmds.objExists(target_module.controls[control_name])):
                continue

            source_ctrl = source_module.controls[control_name]
            target_ctrl = target_module.controls[control_name]

            # Get the control's group for transformation
            source_grp = f"{source_ctrl}_grp"
            target_grp = f"{target_ctrl}_grp"

            if not cmds.objExists(source_grp) or not cmds.objExists(target_grp):
                # Try to find the group
                source_parent = cmds.listRelatives(source_ctrl, parent=True)
                target_parent = cmds.listRelatives(target_ctrl, parent=True)

                if source_parent and target_parent:
                    source_grp = source_parent[0]
                    target_grp = target_parent[0]
                else:
                    continue  # Skip this control

            # Mirror control transform group
            # First check if we should mirror the group or the control directly
            if cmds.objExists(source_grp) and cmds.objExists(target_grp):
                # Mirror position and rotation
                pos = cmds.xform(source_grp, query=True, translation=True, worldSpace=True)
                rot = cmds.xform(source_grp, query=True, rotation=True, worldSpace=True)

                # Mirror across YZ plane
                mirror_pos = [-pos[0], pos[1], pos[2]]
                mirror_rot = [rot[0], -rot[1], -rot[2]]

                # Apply mirrored position and rotation
                # NOTE: We may need to handle parent constraints and relative positioning
                # Skip applying position if there's a parent constraint
                constraints = cmds.listConnections(target_grp, type="constraint") or []

                if not constraints:
                    cmds.xform(target_grp, translation=mirror_pos, worldSpace=True)
                    cmds.xform(target_grp, rotation=mirror_rot, worldSpace=True)
                    print(
                        f"Mirrored control: {control_name} from {source_module.module_id} to {target_module.module_id}")
                else:
                    print(f"Skipped constrained control: {control_name}")

            # Mirror attributes for IK controls (foot attributes, etc.)
            if control_name == "ik_ankle" and source_module.module_type == "leg":
                # Copy foot attribute values
                for attr_name in ["roll", "tilt", "toe", "heel"]:
                    if (cmds.attributeQuery(attr_name, node=source_ctrl, exists=True) and
                            cmds.attributeQuery(attr_name, node=target_ctrl, exists=True)):
                        value = cmds.getAttr(f"{source_ctrl}.{attr_name}")

                        # Flip sign for tilt attribute (side-to-side)
                        if attr_name == "tilt":
                            value = -value

                        cmds.setAttr(f"{target_ctrl}.{attr_name}", value)

            # Mirror FK/IK blend attribute
            if control_name == "fkik_switch":
                if cmds.attributeQuery("FkIkBlend", node=source_ctrl, exists=True) and cmds.attributeQuery("FkIkBlend",
                                                                                                           node=target_ctrl,
                                                                                                           exists=True):
                    value = cmds.getAttr(f"{source_ctrl}.FkIkBlend")
                    cmds.setAttr(f"{target_ctrl}.FkIkBlend", value)

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

            # Check if clusters group already exists
            if cmds.objExists(self.clusters_grp):
                # If it exists, use it as the parent
                grouped_clusters = cmds.group(name=f"{self.character_name}_clusters_grp")
                cmds.parent(grouped_clusters, self.clusters_grp)
            else:
                # If it doesn't exist, create as before
                grouped_clusters = cmds.group(name=f"{self.character_name}_clusters")

            # Set visibility off
            cmds.setAttr(f"{grouped_clusters}.visibility", 0)

            # Clear selection
            cmds.select(clear=True)

            print(f"Organized {len(rig_clusters)} clusters into {grouped_clusters}")
            return len(rig_clusters)

        except Exception as e:
            print(f"Error organizing clusters: {e}")
            return 0