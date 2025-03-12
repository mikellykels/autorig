"""
Modular Rig System
Utility Functions (Refactored)

This module contains utility functions for the modular rigging system.
Improved with better control shapes and guide creation.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import math

# Constants
GUIDE_COLOR = [1, 0.7, 0]  # Orange for guides
GUIDE_BLADE_COLOR = [0, 0.8, 0.8]  # Cyan for up vector guides
CONTROL_COLORS = {
    "main": [1, 1, 0],       # Yellow for main controls
    "secondary": [0, 1, 1],   # Cyan for secondary controls
    "fk": [0.2, 0.8, 0.2],    # Green for FK
    "ik": [0.8, 0.2, 0.8],    # Purple for IK
    "twist": [0.8, 0.4, 0.2], # Orange for twist controls
    "cog": [0.5, 0, 0.5],   # purple
    "offset": [0.5, 0.5, 1.0] # Light blue for offset controls
}


def create_control(name, shape_type="circle", radius=1.0, color=None, normal=None, parent=None):
    """
    Create a control curve with the specified shape and settings.

    Args:
        name (str): Name of the control
        shape_type (str): Type of control shape ("circle", "square", "cube", "sphere", "diamond", "arrow")
        radius (float): Size of the control
        color (list): RGB color for the control
        normal (list): Normal direction for circle controls [x,y,z]
        parent (str): Optional parent for the control

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
        # Create cube control points (8 corners connected with lines)
        points = [
            # Top face
            (-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1), (-1, 1, 1),
            # Bottom face
            (-1, -1, 1), (1, -1, 1), (1, -1, -1), (-1, -1, -1), (-1, -1, 1),
            # Connect top to bottom
            (1, -1, 1), (1, 1, 1), (1, 1, -1), (1, -1, -1), (1, -1, 1),
            # Complete bottom face
            (1, -1, -1), (-1, -1, -1), (-1, -1, 1),
            # Connect remaining edges
            (-1, 1, 1), (-1, -1, 1), (-1, -1, -1), (-1, 1, -1), (-1, 1, 1)
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

    elif shape_type == "diamond":
        # Create a diamond/rhombus shape
        points = [
            (0, 1, 0),  # Top point
            (1, 0, 0),  # Right point
            (0, 0, 1),  # Front point
            (0, 1, 0),  # Top point
            (-1, 0, 0), # Left point
            (0, 0, 1),  # Front point
            (0, -1, 0), # Bottom point
            (-1, 0, 0), # Left point
            (0, 0, -1), # Back point
            (0, -1, 0), # Bottom point
            (1, 0, 0),  # Right point
            (0, 0, -1), # Back point
            (0, 1, 0),  # Top point
            (0, 0, -1), # Back point
            (0, 0, 1),  # Front point
        ]
        ctrl = cmds.curve(name=name, p=[(p[0] * radius, p[1] * radius, p[2] * radius) for p in points], degree=1)

    elif shape_type == "arrow":
        # Create an arrow shape pointing in +Z direction
        points = [
            (0, 0, 2),     # Tip
            (-0.5, 0, 1),  # Right corner of arrowhead
            (-0.25, 0, 1), # Right side of shaft
            (-0.25, 0, -1),# Back right of shaft
            (0.25, 0, -1), # Back left of shaft
            (0.25, 0, 1),  # Left side of shaft
            (0.5, 0, 1),   # Left corner of arrowhead
            (0, 0, 2)      # Back to tip
        ]
        ctrl = cmds.curve(name=name, p=[(p[0] * radius, p[1] * radius, p[2] * radius) for p in points], degree=1)

    else:
        # Default to circle if shape type is not recognized
        ctrl = cmds.circle(name=name, radius=radius)[0]

    # Set color if provided
    if color and ctrl:
        set_color_override(ctrl, color)

    # Create control group
    ctrl_grp = cmds.group(ctrl, name=f"{name}_grp")

    # Parent if specified
    if parent and cmds.objExists(parent):
        cmds.parent(ctrl_grp, parent)

    return ctrl, ctrl_grp


def create_guide(name, position=(0, 0, 0), parent=None, color=None):
    """
    Create a guide locator at the specified position.

    Args:
        name (str): Name of the guide
        position (tuple): Position (x, y, z) of the guide
        parent (str): Parent guide
        color (list): Optional RGB color override (defaults to GUIDE_COLOR)

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

    # Use specified color or default
    guide_color = color if color else GUIDE_COLOR
    cmds.setAttr(f"{shape}.overrideColorR", guide_color[0])
    cmds.setAttr(f"{shape}.overrideColorG", guide_color[1])
    cmds.setAttr(f"{shape}.overrideColorB", guide_color[2])

    # Set position
    cmds.setAttr(f"{guide}.translateX", position[0])
    cmds.setAttr(f"{guide}.translateY", position[1])
    cmds.setAttr(f"{guide}.translateZ", position[2])

    # Parent if specified
    if parent and cmds.objExists(parent):
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
    if parent and cmds.objExists(parent):
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


def create_annotation(start_object, end_object, text="", color=None):
    """
    Create an annotation (label) connecting two objects.

    Args:
        start_object (str): Object that annotation line starts from
        end_object (str): Object that will have the annotation text
        text (str): Text to display
        color (list): RGB color for the annotation

    Returns:
        str: Name of the created annotation
    """
    # Get positions
    start_pos = cmds.xform(start_object, query=True, translation=True, worldSpace=True)
    end_pos = cmds.xform(end_object, query=True, translation=True, worldSpace=True)

    # Create annotation
    annotation = cmds.annotate(end_object, tx=text, p=(end_pos[0], end_pos[1], end_pos[2]))

    # Get the transform node of the annotation
    annotation_transform = cmds.listRelatives(annotation, parent=True)[0]

    # Set color if provided
    if color:
        set_color_override(annotation_transform, color)

    # Connect to start object
    cmds.connectAttr(f"{start_object}.worldMatrix[0]", f"{annotation_transform}.startWorldMatrix")

    return annotation_transform


def create_pole_vector_line(start_joint, mid_joint, pole_ctrl, color=None):
    """
    Create a line connecting the mid joint to the pole vector control.

    Args:
        start_joint (str): First joint in chain (shoulder/hip)
        mid_joint (str): Middle joint in chain (elbow/knee)
        pole_ctrl (str): Pole vector control
        color (list): RGB color for the line

    Returns:
        tuple: Created curve and clusters
    """
    # Get middle joint position
    mid_pos = cmds.xform(mid_joint, query=True, translation=True, worldSpace=True)

    # Get pole control position
    pole_pos = cmds.xform(pole_ctrl, query=True, translation=True, worldSpace=True)

    # Create curve
    curve = cmds.curve(
        name=f"{mid_joint}_to_pole",
        p=[mid_pos, pole_pos],
        degree=1
    )

    # Set color
    if color:
        set_color_override(curve, color)
    else:
        set_color_override(curve, [0.8, 0.8, 0.8])  # Light gray default

    # Create clusters to follow the objects
    cls1 = cmds.cluster(f"{curve}.cv[0]")[1]
    cmds.pointConstraint(mid_joint, cls1)

    cls2 = cmds.cluster(f"{curve}.cv[1]")[1]
    cmds.pointConstraint(pole_ctrl, cls2)

    # Hide clusters
    cmds.setAttr(f"{cls1}.visibility", 0)
    cmds.setAttr(f"{cls2}.visibility", 0)

    return curve, (cls1, cls2)


def get_midpoint(point1, point2):
    """
    Calculate the midpoint between two points.

    Args:
        point1 (list/tuple): First point (x, y, z)
        point2 (list/tuple): Second point (x, y, z)

    Returns:
        list: Midpoint coordinates [x, y, z]
    """
    return [
        (point1[0] + point2[0]) / 2,
        (point1[1] + point2[1]) / 2,
        (point1[2] + point2[2]) / 2
    ]


def get_distance(point1, point2):
    """
    Calculate the distance between two points.

    Args:
        point1 (list/tuple): First point (x, y, z)
        point2 (list/tuple): Second point (x, y, z)

    Returns:
        float: Distance between the points
    """
    return math.sqrt(
        (point2[0] - point1[0])**2 +
        (point2[1] - point1[1])**2 +
        (point2[2] - point1[2])**2
    )


def lock_and_hide_attributes(node, attributes=None):
    """
    Lock and hide specified attributes on a node.

    Args:
        node (str): Node to modify
        attributes (list): List of attributes to lock and hide
                          Default: translate, rotate, scale, visibility
    """
    if not attributes:
        attributes = [
            "tx", "ty", "tz",
            "rx", "ry", "rz",
            "sx", "sy", "sz",
            "v"
        ]

    for attr in attributes:
        if cmds.attributeQuery(attr, node=node, exists=True):
            cmds.setAttr(f"{node}.{attr}", lock=True, keyable=False, channelBox=False)


def unlock_and_show_attributes(node, attributes=None):
    """
    Unlock and show specified attributes on a node.

    Args:
        node (str): Node to modify
        attributes (list): List of attributes to unlock and show
                          Default: translate, rotate, scale, visibility
    """
    if not attributes:
        attributes = [
            "tx", "ty", "tz",
            "rx", "ry", "rz",
            "sx", "sy", "sz",
            "v"
        ]

    for attr in attributes:
        if cmds.attributeQuery(attr, node=node, exists=True):
            cmds.setAttr(f"{node}.{attr}", lock=False, keyable=True)