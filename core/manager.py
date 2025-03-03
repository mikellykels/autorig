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