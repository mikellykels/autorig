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

    def mirror_modules(self):
        """
        Mirror left side modules to right side.
        Only mirror limb modules (arms and legs), not spine.

        This handles mirroring at all stages of the rig:
        1. Module creation
        2. Guide placement
        3. Joint creation
        4. Control creation

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
            if f"r_{left_module.module_name}" in self.modules:
                print(f"Right module {right_module_id} already exists, skipping")
                continue

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

            print(f"Created mirrored module: {right_module.module_id}")

            # 3. Mirror based on the stage of rig creation

            # 3a. If guides exist for the left module, mirror them
            if left_module.guides:
                right_module.create_guides()
                self._mirror_guides(left_module, right_module)

            # 3b. If joints exist for the left module, mirror them
            if left_module.joints:
                # Check if left module has been fully built
                left_built = len(left_module.controls) > 0

                # Only mirror joints if right module doesn't have joints yet
                if not right_module.joints:
                    # Build just the joints without controls if the left module is not fully built
                    if not left_built:
                        if hasattr(right_module, '_create_joints'):
                            right_module._create_joints()
                        else:
                            # Fall back to full build
                            right_module.build()
                    else:
                        # If left is fully built, fully build right
                        right_module.build()

                    # Mirror joint positions and orientations
                    self._mirror_joints(left_module, right_module)

                # 3c. If controls exist for the left module, mirror them
                if left_built and len(right_module.controls) > 0:
                    self._mirror_controls(left_module, right_module)

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
        Mirror joints from source module to target module.

        Args:
            source_module (BaseModule): Source module (left side)
            target_module (BaseModule): Target module (right side)
        """
        # Make sure both modules have joints
        if not source_module.joints or not target_module.joints:
            print("Error: Joints not found in one or both modules")
            return

        print(f"Mirroring joints from {source_module.module_id} to {target_module.module_id}")

        # Process joint chains - we need to handle the main chain and IK/FK chains
        joint_prefixes = ["", "ik_", "fk_"]

        for prefix in joint_prefixes:
            # Determine joint chains based on module type
            if source_module.module_type == "arm":
                joint_chain = ["shoulder", "elbow", "wrist", "hand"]
            elif source_module.module_type == "leg":
                joint_chain = ["hip", "knee", "ankle", "foot", "toe"]
            else:
                continue  # Skip non-limb modules

            # Mirror each joint in the chain
            for joint_name in joint_chain:
                source_key = f"{prefix}{joint_name}"

                # Skip if source or target joint doesn't exist
                if (source_key not in source_module.joints or
                        source_key not in target_module.joints or
                        not cmds.objExists(source_module.joints[source_key]) or
                        not cmds.objExists(target_module.joints[source_key])):
                    continue

                source_joint = source_module.joints[source_key]
                target_joint = target_module.joints[source_key]

                # Mirror the joint position
                pos = cmds.xform(source_joint, query=True, translation=True, worldSpace=True)
                mirror_pos = [-pos[0], pos[1], pos[2]]

                # Apply position to target joint - use relative movement to avoid hierarchy issues
                curr_pos = cmds.xform(target_joint, query=True, translation=True, worldSpace=True)
                delta = [mirror_pos[i] - curr_pos[i] for i in range(3)]

                # Get joint's parent to handle relative movement
                parent = cmds.listRelatives(target_joint, parent=True)
                if parent:
                    # Convert delta to local space if needed
                    cmds.xform(target_joint, translation=delta, relative=True)
                else:
                    # If no parent, just set world position
                    cmds.xform(target_joint, translation=mirror_pos, worldSpace=True)

                # Mirror joint orientation
                # Note: For proper behavior mirroring, we need to handle the joint orientation appropriately
                joint_orient = cmds.getAttr(f"{source_joint}.jointOrient")[0]
                mirror_orient = [joint_orient[0], -joint_orient[1], -joint_orient[2]]

                try:
                    cmds.setAttr(f"{target_joint}.jointOrient", *mirror_orient)
                except Exception as e:
                    print(f"Error setting joint orientation for {target_joint}: {str(e)}")

                print(f"Mirrored joint: {source_key} from {source_module.module_id} to {target_module.module_id}")

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