"""
Modular Auto-Rig System
Base Module Class (Refactored)

This module contains the abstract base class for rig modules.
Modified to support improved rigging workflow with better joint orientation.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
from abc import ABC, abstractmethod


class BaseModule(ABC):
    """
    Abstract base class for rig modules.
    Provides the foundation for all rigging components.
    """

    def __init__(self, side, module_name, module_type):
        """
        Initialize the module.

        Args:
            side (str): Side of the body ('l', 'r', 'c')
            module_name (str): Name of the module
            module_type (str): Type of the module
        """
        self.side = side
        self.module_name = module_name
        self.module_type = module_type
        self.module_id = f"{self.side}_{self.module_name}"

        self.manager = None

        # Dictionaries to store rig components
        self.guides = {}
        self.blade_guides = {}  # Specialized guides for orientation
        self.joints = {}
        self.controls = {}
        self.utility_nodes = {}  # Store utility nodes created for this module

        # Group references
        self.guide_grp = None
        self.joint_grp = None
        self.control_grp = None

        # Debug flags
        self.debug_mode = False

        # Status tracking
        self.build_status = {
            "guides_created": False,
            "joints_created": False,
            "controls_created": False,
            "constraints_created": False,
            "build_completed": False
        }

    def set_manager(self, manager):
        """
        Set the module manager.

        Args:
            manager (ModuleManager): Module manager instance
        """
        self.manager = manager

    def _create_module_groups(self):
        """Create the module groups."""
        if not self.manager:
            raise RuntimeError("Module manager not set.")

        # Create guide group
        self.guide_grp = cmds.group(empty=True, name=f"{self.module_id}_guides")
        cmds.parent(self.guide_grp, self.manager.guides_grp)

        # Create joint group
        self.joint_grp = cmds.group(empty=True, name=f"{self.module_id}_joints")
        cmds.parent(self.joint_grp, self.manager.joints_grp)

        # Create control group
        self.control_grp = cmds.group(empty=True, name=f"{self.module_id}_controls")
        cmds.parent(self.control_grp, self.manager.controls_grp)

    @abstractmethod
    def create_guides(self):
        """Create the module guides."""
        pass

    @abstractmethod
    def build(self):
        """Build the module."""
        pass

    def get_guide_positions(self):
        """
        Get the positions of all module guides.

        Returns:
            dict: Guide positions
        """
        positions = {}

        for guide_name, guide in self.guides.items():
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
            positions (dict): Guide positions
        """
        for guide_name, guide_data in positions.items():
            if guide_name in self.guides and cmds.objExists(self.guides[guide_name]):
                guide = self.guides[guide_name]
                cmds.xform(guide, translation=guide_data['position'], worldSpace=True)
                cmds.xform(guide, rotation=guide_data['rotation'], worldSpace=True)

    def validate_guides(self):
        """
        Validate guide positions and make adjustments if needed.
        Should be implemented by derived classes.

        Returns:
            bool: True if guides are valid
        """
        # Default implementation does nothing but report success
        return True

    def debug_log(self, message):
        """
        Log a debug message if debug mode is enabled.

        Args:
            message (str): Message to log
        """
        if self.debug_mode:
            print(f"[DEBUG] {self.module_id}: {message}")

    def get_module_info(self):
        """
        Get information about the module.

        Returns:
            dict: Module information
        """
        return {
            "side": self.side,
            "name": self.module_name,
            "type": self.module_type,
            "id": self.module_id,
            "guides": len(self.guides),
            "joints": len(self.joints),
            "controls": len(self.controls),
            "status": self.build_status
        }

    def cleanup(self):
        """
        Clean up temporary nodes created during the build process.
        """
        # Override this in derived classes if needed
        pass

    def lock_attributes(self, node, attributes):
        """
        Lock and hide specified attributes on a node.

        Args:
            node (str): Node name
            attributes (list): Attributes to lock
        """
        if not cmds.objExists(node):
            return

        for attr in attributes:
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.setAttr(f"{node}.{attr}", lock=True, keyable=False, channelBox=False)

    def unlock_attributes(self, node, attributes):
        """
        Unlock and show specified attributes on a node.

        Args:
            node (str): Node name
            attributes (list): Attributes to unlock
        """
        if not cmds.objExists(node):
            return

        for attr in attributes:
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.setAttr(f"{node}.{attr}", lock=False, keyable=True)

    def add_attribute(self, node, attr_name, attr_type="float", default_value=0.0, min_value=None, max_value=None, keyable=True):
        """
        Add a custom attribute to a node.

        Args:
            node (str): Node name
            attr_name (str): Attribute name
            attr_type (str): Attribute type
            default_value: Default value for the attribute
            min_value: Minimum value (optional)
            max_value: Maximum value (optional)
            keyable (bool): Whether the attribute should be keyable

        Returns:
            bool: True if successful
        """
        if not cmds.objExists(node):
            return False

        # Check if attribute already exists
        if cmds.attributeQuery(attr_name, node=node, exists=True):
            return True

        # Add attribute
        kwargs = {
            "longName": attr_name,
            "attributeType": attr_type,
            "defaultValue": default_value,
            "keyable": keyable
        }

        # Add min/max if specified
        if min_value is not None:
            kwargs["minValue"] = min_value
        if max_value is not None:
            kwargs["maxValue"] = max_value

        cmds.addAttr(node, **kwargs)
        return True

    def set_debug_mode(self, enabled=True):
        """
        Enable or disable debug mode.

        Args:
            enabled (bool): Whether to enable debug mode
        """
        self.debug_mode = enabled
        print(f"Debug mode {'enabled' if enabled else 'disabled'} for {self.module_id}")