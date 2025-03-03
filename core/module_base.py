"""
Modular Auto-Rig System
Base Module Class

This module contains the abstract base class for rig modules.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
from abc import ABC, abstractmethod


class BaseModule(ABC):
    """
    Abstract base class for rig modules.
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
        self.guides = {}
        self.joints = {}
        self.controls = {}

        self.guide_grp = None
        self.joint_grp = None
        self.control_grp = None

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