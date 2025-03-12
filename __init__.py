"""
Modular Rig System
Main package initialization

This package contains a Modular Rig Systemging system for Maya.

Author: Mikaela Carino
Date: 2025
"""

# Make core classes available at the package level
from autorig.core.manager import ModuleManager
from autorig.core.module_base import BaseModule

# Import modules to make them available
import autorig.modules
import autorig.ui

__version__ = "1.0.0"