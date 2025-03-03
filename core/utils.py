"""
Modular Auto-Rig System
Utility Functions

This module contains utility functions for the auto-rigging system.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds

# Constants
GUIDE_COLOR = [1, 0.7, 0]  # Orange for guides
CONTROL_COLORS = {
    "main": [1, 1, 0],  # Yellow for main controls
    "secondary": [0, 1, 1],  # Cyan for secondary controls
    "fk": [0.2, 0.8, 0.2],  # Green for FK
    "ik": [0.8, 0.2, 0.8],  # Purple for IK
    "twist": [0.8, 0.4, 0.2]  # Orange for twist controls
}


def create_control(name, shape_type="circle", radius=1.0, color=None, normal=None):
    """
    Create a control curve with the specified shape and settings.

    Args:
        name (str): Name of the control
        shape_type (str): Type of control shape ("circle", "square", "cube", "sphere")
        radius (float): Size of the control
        color (list): RGB color for the control
        normal (list): Normal direction for circle controls [x,y,z]

    Returns:
        tuple(str, str): Name of created control and its group
    """
    ctrl = None

    if shape_type == "circle":
        # If normal is provided, use it, otherwise default to Y-up
        if normal is None:
            normal = [0, 1, 0]  # Default Y-up

        ctrl = cmds.circle(name=name, normal=normal, radius=radius)[0]
    elif shape_type == "square":
        points = [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1), (-1, 0, -1)]
        ctrl = cmds.curve(name=name, p=[(p[0] * radius, p[1] * radius, p[2] * radius) for p in points], degree=1)
    elif shape_type == "cube":
        # Create cube control points
        points = [
            (-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1), (-1, 1, 1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (1, -1, 1), (1, -1, -1),
            (1, 1, -1), (1, -1, -1), (-1, -1, -1), (-1, 1, -1), (-1, -1, -1),
            (-1, -1, 1)
        ]
        ctrl = cmds.curve(name=name, p=[(p[0] * radius, p[1] * radius, p[2] * radius) for p in points], degree=1)
    elif shape_type == "sphere":
        # Create sphere using NURBS circles
        ctrl = cmds.circle(name=name, normal=[0, 1, 0], radius=radius)[0]

        # Create additional circles for the sphere
        circle1 = cmds.circle(normal=[1, 0, 0], radius=radius)[0]
        circle2 = cmds.circle(normal=[0, 0, 1], radius=radius)[0]

        # Parent shapes to main control
        shapes = cmds.listRelatives(circle1, shapes=True) + cmds.listRelatives(circle2, shapes=True)
        for shape in shapes:
            cmds.parent(shape, ctrl, shape=True, relative=True)

        # Delete empty transforms
        cmds.delete(circle1, circle2)

    # Set color if provided
    if color and ctrl:
        shapes = cmds.listRelatives(ctrl, shapes=True)
        for shape in shapes:
            cmds.setAttr(f"{shape}.overrideEnabled", 1)
            cmds.setAttr(f"{shape}.overrideRGBColors", 1)
            cmds.setAttr(f"{shape}.overrideColorR", color[0])
            cmds.setAttr(f"{shape}.overrideColorG", color[1])
            cmds.setAttr(f"{shape}.overrideColorB", color[2])

    # Create control group
    ctrl_grp = cmds.group(ctrl, name=f"{name}_grp")

    return ctrl, ctrl_grp

def create_guide(name, position=(0, 0, 0), parent=None):
    """
    Create a guide locator at the specified position.

    Args:
        name (str): Name of the guide
        position (tuple): Position (x, y, z) of the guide
        parent (str): Parent guide

    Returns:
        str: Name of created guide
    """
    guide = cmds.spaceLocator(name=f"{name}_guide")[0]
    cmds.setAttr(f"{guide}.localScaleX", 0.5)
    cmds.setAttr(f"{guide}.localScaleY", 0.5)
    cmds.setAttr(f"{guide}.localScaleZ", 0.5)

    # Set color
    shape = cmds.listRelatives(guide, shapes=True)[0]
    cmds.setAttr(f"{shape}.overrideEnabled", 1)
    cmds.setAttr(f"{shape}.overrideRGBColors", 1)
    cmds.setAttr(f"{shape}.overrideColorR", GUIDE_COLOR[0])
    cmds.setAttr(f"{shape}.overrideColorG", GUIDE_COLOR[1])
    cmds.setAttr(f"{shape}.overrideColorB", GUIDE_COLOR[2])

    # Set position
    cmds.setAttr(f"{guide}.translateX", position[0])
    cmds.setAttr(f"{guide}.translateY", position[1])
    cmds.setAttr(f"{guide}.translateZ", position[2])

    # Parent if specified
    if parent:
        cmds.parent(guide, parent)

    return guide

def create_joint(name, position=(0, 0, 0), parent=None):
    """
    Create a joint at the specified position.

    Args:
        name (str): Name of the joint
        position (tuple): Position (x, y, z) of the joint
        parent (str): Parent joint

    Returns:
        str: Name of created joint
    """
    # Store selection to restore it later
    selection = cmds.ls(selection=True)

    # Unselect everything
    cmds.select(clear=True)

    # Select parent if specified
    if parent:
        cmds.select(parent)

    # Create joint
    joint = cmds.joint(name=name, position=position)

    # Restore selection
    if selection:
        cmds.select(selection)
    else:
        cmds.select(clear=True)

    return joint

def set_color_override(obj, color):
    """
    Set the color override for an object.

    Args:
        obj (str): Name of the object
        color (list): RGB color
    """
    shapes = cmds.listRelatives(obj, shapes=True) or []
    for shape in shapes:
        cmds.setAttr(f"{shape}.overrideEnabled", 1)
        cmds.setAttr(f"{shape}.overrideRGBColors", 1)
        cmds.setAttr(f"{shape}.overrideColorR", color[0])
        cmds.setAttr(f"{shape}.overrideColorG", color[1])
        cmds.setAttr(f"{shape}.overrideColorB", color[2])