"""
Modular Auto-Rig System
Core package initialization

This package contains the core components of the auto-rigging system.

Author: Mikaela Carino
Date: 2025
"""

from autorig.core.utils import (
    create_control,
    create_guide,
    create_joint,
    set_color_override,
    CONTROL_COLORS,
    GUIDE_COLOR
)

from autorig.core.module_base import BaseModule
from autorig.core.manager import ModuleManager