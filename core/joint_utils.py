"""
Modular Rig System
Joint Utilities

This module contains specialized utilities for joint creation, orientation,
and validation to ensure proper rig setup.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import math
from autorig.core.vector_utils import (
    vector_from_two_points, vector_length, normalize_vector, dot_product,
    cross_product, scale_vector, add_vectors, subtract_vectors, get_midpoint,
    angle_between_vectors, angle_between_vectors_deg, project_vector_onto_plane,
    make_vectors_planar, is_planar, create_rotation_matrix
)

# Constants for orientation references
PRIMARY_AXIS = "x"  # Bone direction axis
SECONDARY_AXIS = "y"  # Up direction for orientation


def is_planar_chain(positions, tolerance=0.01):
    """
    Check if a chain of joint positions is approximately planar.

    Args:
        positions (list): List of 3D positions [(x1,y1,z1), (x2,y2,z2), ...]
        tolerance (float): Maximum allowable deviation from planarity

    Returns:
        bool: True if positions form a planar chain, False otherwise
    """
    return is_planar(positions, tolerance)


def make_planar(positions, preserve_length=True):
    """
    Project a chain of positions onto a best-fit plane while preserving chain lengths.

    Args:
        positions (list): List of 3D positions [(x1,y1,z1), (x2,y2,z2), ...]
        preserve_length (bool): Whether to maintain original distances between joints

    Returns:
        list: Adjusted positions that are planar
    """
    # Debug
    print(f"make_planar called with {len(positions)} positions")
    print(f"Input positions: {positions}")

    if len(positions) < 3 or is_planar(positions):
        print("Positions already planar or too few points - returning original")
        return positions  # Already planar or too few points

    import copy
    # Make deep copy of positions to avoid modifying the original
    positions_copy = copy.deepcopy(positions)

    # Create vectors between consecutive points
    vectors = []
    for i in range(len(positions_copy) - 1):
        vectors.append(vector_from_two_points(positions_copy[i], positions_copy[i + 1]))

    # Debug
    print(f"Created {len(vectors)} vectors between positions")

    # Make vectors planar
    planar_vectors = make_vectors_planar(vectors, preserve_length)

    # Debug
    print(f"Planar vectors: {planar_vectors}")

    # Reconstruct positions from planar vectors
    planar_positions = [list(positions_copy[0])]  # Start with copy of the first point unchanged

    # Debug
    print(f"Starting planar reconstruction with first point: {planar_positions[0]}")

    for i, vec in enumerate(planar_vectors):
        # Debug
        if i > 0:
            print(f"Adding vector {i}: {vec} to previous position {planar_positions[-1]}")

        new_pos = [
            planar_positions[-1][0] + vec[0],
            planar_positions[-1][1] + vec[1],
            planar_positions[-1][2] + vec[2]
        ]
        planar_positions.append(new_pos)

    # Debug output of final result
    print(f"Original positions: {positions}")
    print(f"Planar positions: {planar_positions}")

    return planar_positions


def calculate_aim_up_vectors(positions, up_hint=(0, 1, 0), pole_vector=None):
    """
    Calculate aim and up vectors for joint orientation.

    Args:
        positions (list): List of joint positions
        up_hint (tuple): General up direction to use as hint
        pole_vector (tuple): Position of pole vector guide if available

    Returns:
        list: List of (aim_vector, up_vector) tuples for each joint except the last
    """
    if len(positions) < 2:
        return []

    vectors = []

    for i in range(len(positions) - 1):
        # Calculate aim vector (direction to child)
        aim_vector = vector_from_two_points(positions[i], positions[i+1])
        aim_length = vector_length(aim_vector)

        if aim_length < 0.0001:
            aim_vector = [1, 0, 0]  # Default if joints are coincident
        else:
            aim_vector = normalize_vector(aim_vector)

        # Calculate up vector
        up_vector = None

        if pole_vector is not None and i == 0:  # Only use pole vector for first joint (shoulder/hip)
            # Use pole vector to calculate up direction
            to_pole = vector_from_two_points(positions[i], pole_vector)

            # Ensure up vector is perpendicular to aim_vector
            dot = dot_product(to_pole, aim_vector)
            perpendicular = [
                to_pole[0] - aim_vector[0] * dot,
                to_pole[1] - aim_vector[1] * dot,
                to_pole[2] - aim_vector[2] * dot
            ]

            perp_length = vector_length(perpendicular)

            if perp_length > 0.0001:
                up_vector = normalize_vector(perpendicular)

        if up_vector is None:
            # If no pole or calculation failed, use cross-product method with hint
            hint = up_hint

            # Check if aim and hint are too aligned
            parallel_check = abs(dot_product(aim_vector, normalize_vector(hint)))
            if parallel_check > 0.99:
                # Use an alternative hint if too parallel
                hint = [0, 0, 1] if parallel_check > 0.99 else hint

            # Cross product to get perpendicular vector
            side_vector = cross_product(aim_vector, hint)
            side_length = vector_length(side_vector)

            if side_length < 0.0001:
                # Extremely rare case: try a different hint
                side_vector = cross_product(aim_vector, [0, 0, 1])
                side_length = vector_length(side_vector)

                if side_length < 0.0001:
                    side_vector = cross_product(aim_vector, [1, 0, 0])
                    side_length = vector_length(side_vector)

            side_vector = normalize_vector(side_vector)

            # Cross again to get perpendicular up vector
            up_vector = cross_product(side_vector, aim_vector)
            up_vector = normalize_vector(up_vector)

        vectors.append((aim_vector, up_vector))

    return vectors


def create_blade_matrix(aim_vector, up_vector):
    """
    Create a rotation matrix from aim and up vectors.

    This implements the 'blade' concept from mGear, where a blade
    represents the orientation plane for a joint.

    Args:
        aim_vector (list/tuple): The aim direction
        up_vector (list/tuple): The up direction

    Returns:
        list: 4x4 transformation matrix as a flat list in Maya format
    """
    return create_rotation_matrix(aim_vector, up_vector)


def apply_orientation_to_joint(joint, aim_vector, up_vector, primary_axis=PRIMARY_AXIS,
                               secondary_axis=SECONDARY_AXIS):
    """
    Explicitly orient a joint using aim and up vectors.

    Args:
        joint (str): Name of the joint to orient
        aim_vector (list/tuple): The aim direction vector
        up_vector (list/tuple): The up direction vector
        primary_axis (str): Axis to align with aim direction (x, y, or z)
        secondary_axis (str): Axis to align with up direction (x, y, or z)

    Returns:
        bool: True if orientation was successful
    """
    if not cmds.objExists(joint):
        return False

    # Create matrix from vectors
    matrix = create_blade_matrix(aim_vector, up_vector)

    # Store child joints to maintain positions
    children = cmds.listRelatives(joint, children=True, type="joint") or []
    child_positions = []
    for child in children:
        child_positions.append(cmds.xform(child, query=True, translation=True, worldSpace=True))

    # Apply orientation matrix
    cmds.xform(joint, matrix=matrix, worldSpace=True)

    # Reset rotation values
    cmds.setAttr(f"{joint}.rotate", 0, 0, 0)

    # Fix positions of children
    for i, child in enumerate(children):
        cmds.xform(child, translation=child_positions[i], worldSpace=True)

    return True


def fix_joint_orientations(joint_list, up_hint=(0, 1, 0), pole_vector=None):
    """
    Apply correct orientations to a list of joints using aim and up vectors.

    Args:
        joint_list (list): List of joints to orient
        up_hint (tuple): General up direction
        pole_vector (tuple): Position of pole vector if available

    Returns:
        bool: True if orientation was successful
    """
    if not joint_list or len(joint_list) < 2:
        return False

    # Get joint positions
    positions = []
    for joint in joint_list:
        if cmds.objExists(joint):
            pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)
            positions.append(pos)
        else:
            return False

    # Calculate aim and up vectors
    vectors = calculate_aim_up_vectors(positions, up_hint, pole_vector)

    # Apply orientations to each joint except the last
    for i in range(len(joint_list) - 1):
        aim_vector, up_vector = vectors[i]
        apply_orientation_to_joint(joint_list[i], aim_vector, up_vector)

    # Special case for end joint - maintain orientation from parent
    if len(joint_list) > 1:
        end_joint = joint_list[-1]
        end_parent = joint_list[-2]

        # Get the parent's orientation
        parent_matrix = cmds.xform(end_parent, query=True, matrix=True, worldSpace=True)

        # Calculate the local offset needed
        end_pos = positions[-1]
        parent_pos = positions[-2]

        # Apply orientation while maintaining position
        cmds.xform(end_joint, matrix=parent_matrix, worldSpace=True)
        cmds.xform(end_joint, translation=end_pos, worldSpace=True)
        cmds.setAttr(f"{end_joint}.rotate", 0, 0, 0)

    return True


def create_oriented_joint_chain(joint_names, positions, parent=None, up_hint=(0, 1, 0), pole_vector=None):
    """
    Create a chain of joints with proper orientation in a single operation.
    Simplified to ensure proper positioning.

    Args:
        joint_names (list): Names for the joints to create
        positions (list): World space positions for the joints
        parent (str): Parent for the root joint
        up_hint (tuple): General up direction
        pole_vector (tuple): Position of pole vector if available

    Returns:
        list: Created joint names
    """
    # Validate inputs
    if not joint_names or not positions or len(joint_names) != len(positions):
        print(f"ERROR: Invalid inputs to create_oriented_joint_chain")
        print(f"  joint_names: {joint_names}")
        print(f"  positions: {positions}")
        return []

    print(f"Creating joint chain with {len(joint_names)} joints")
    for i, (name, pos) in enumerate(zip(joint_names, positions)):
        print(f"  [{i}] {name} at {pos}")

    # Make copies of positions to avoid reference issues
    copied_positions = []
    for pos in positions:
        copied_positions.append([pos[0], pos[1], pos[2]])

    # Basic planar check
    if len(copied_positions) >= 3:
        if not is_planar_chain(copied_positions):
            print("Joint chain was not planar - projecting to best-fit plane")
            copied_positions = make_planar(copied_positions)
            print(f"Adjusted positions: {copied_positions}")

    # STEP 1: Create the joint chain directly with Maya cmds
    created_joints = []

    try:
        # Select the parent if specified
        if parent and cmds.objExists(parent):
            cmds.select(parent)
        else:
            cmds.select(clear=True)

        for i, (name, position) in enumerate(zip(joint_names, copied_positions)):
            # Create each joint explicitly
            if i == 0:
                # First joint - create at root position
                joint = cmds.joint(name=name)
                cmds.xform(joint, translation=position, worldSpace=True)
                created_joints.append(joint)
                print(f"  Created root joint: {joint} at {position}")
            else:
                # Select the previous joint
                cmds.select(created_joints[-1])

                # Create the joint
                joint = cmds.joint(name=name)
                cmds.xform(joint, translation=position, worldSpace=True)
                created_joints.append(joint)
                print(f"  Created child joint: {joint} at {position}")

        # STEP 2: Apply joint orientation using simple Maya command
        if len(created_joints) >= 2:
            cmds.select(created_joints[0])  # Select the root joint
            cmds.joint(edit=True, orientJoint="xyz", secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)
            print(f"  Applied default orientation to joint chain")

            # Check if we need to use pole vector or up vectors for custom orientation
            if pole_vector or up_hint:
                try:
                    fix_joint_orientations(created_joints, up_hint, pole_vector)
                    print(f"  Applied custom orientation to joint chain")
                except Exception as e:
                    print(f"  Warning: Custom orientation failed: {str(e)}")

        # Verify final positions and orientations
        print("Final joint chain created:")
        for i, joint in enumerate(created_joints):
            pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)
            orient = cmds.getAttr(f"{joint}.jointOrient")[0]
            print(f"  [{i}] {joint} at {pos} with orientation {orient}")

    except Exception as e:
        print(f"ERROR in create_oriented_joint_chain: {str(e)}")
        import traceback
        traceback.print_exc()

    return created_joints

def validate_pole_vector_placement(joint_positions, pole_position, min_angle_degrees=5.0):
    """
    Validate if a pole vector is placed at an appropriate position
    to avoid flipping issues.

    Args:
        joint_positions (list): Positions of joints in the chain (at least 3)
        pole_position (list/tuple): Position of the pole vector
        min_angle_degrees (float): Minimum acceptable angle

    Returns:
        tuple: (is_valid, angle_degrees, suggested_position)
    """
    if len(joint_positions) < 3:
        return False, 0, None

    # Get key joint positions
    root = joint_positions[0]
    mid = joint_positions[1]
    end = joint_positions[2]

    # Calculate bone vectors
    bone1 = vector_from_two_points(root, mid)
    bone2 = vector_from_two_points(mid, end)

    # Create a plane normal using the bones
    plane_normal = cross_product(bone1, bone2)
    normal_length = vector_length(plane_normal)

    if normal_length < 0.0001:
        # Chain is collinear, any perpendicular direction works
        plane_normal = [0, 1, 0]
        if abs(dot_product(normalize_vector(bone1), plane_normal)) > 0.9:
            plane_normal = [0, 0, 1]
    else:
        plane_normal = normalize_vector(plane_normal)

    # Vector from mid joint to pole
    to_pole = vector_from_two_points(mid, pole_position)
    to_pole_length = vector_length(to_pole)

    if to_pole_length < 0.0001:
        # Pole is at same position as mid joint
        return False, 0, [
            mid[0] + plane_normal[0] * 5.0,
            mid[1] + plane_normal[1] * 5.0,
            mid[2] + plane_normal[2] * 5.0
        ]

    # Calculate angle between to_pole and plane normal
    to_pole_norm = normalize_vector(to_pole)
    cos_angle = dot_product(to_pole_norm, plane_normal)
    angle_rad = math.acos(min(1.0, max(-1.0, cos_angle)))
    angle_deg = math.degrees(angle_rad)

    # Check if angle is sufficient
    is_valid = abs(angle_deg) >= min_angle_degrees

    # If not valid, calculate a suggested position
    if not is_valid:
        suggested_pole = [
            mid[0] + plane_normal[0] * 5.0,
            mid[1] + plane_normal[1] * 5.0,
            mid[2] + plane_normal[2] * 5.0
        ]
    else:
        suggested_pole = pole_position

    return is_valid, angle_deg, suggested_pole

def mirror_joint_orientations(source_joints, target_joints, mirror_axis='X'):
    """
    Copy orientations from source joints to target joints with appropriate mirroring.

    Args:
        source_joints (list): Source joint chain
        target_joints (list): Target joint chain
        mirror_axis (str): Axis to mirror across ('X', 'Y', or 'Z')

    Returns:
        bool: True if successful
    """
    if len(source_joints) != len(target_joints):
        return False

    # Create mirroring matrix based on axis
    mirror_values = [1, 1, 1, 0, 0, 0]
    if mirror_axis.upper() == 'X':
        mirror_values[0] = -1  # Negate X translation/rotation
    elif mirror_axis.upper() == 'Y':
        mirror_values[1] = -1  # Negate Y translation/rotation
    elif mirror_axis.upper() == 'Z':
        mirror_values[2] = -1  # Negate Z translation/rotation

    # Process each joint pair
    for src_jnt, tgt_jnt in zip(source_joints, target_joints):
        if not (cmds.objExists(src_jnt) and cmds.objExists(tgt_jnt)):
            continue

        # Get source orient values
        src_orient = cmds.getAttr(f"{src_jnt}.jointOrient")[0]

        # Apply mirroring for rotations
        mirrored_orient = [
            src_orient[0] * mirror_values[3],
            src_orient[1] * mirror_values[4],
            src_orient[2] * mirror_values[5]
        ]

        # Handle special case for YZ plane mirror (most common for character rigs)
        if mirror_axis.upper() == 'X':
            # For X-axis mirroring we need to adjust Y and Z rotations
            mirrored_orient = [src_orient[0], -src_orient[1], -src_orient[2]]

        # Set the target orientation
        cmds.setAttr(f"{tgt_jnt}.jointOrient", *mirrored_orient)

        # Zero out rotation
        cmds.setAttr(f"{tgt_jnt}.rotate", 0, 0, 0)

    return True


def fix_specific_joint_orientation(joint, aim_axis=PRIMARY_AXIS, up_axis=None,
                                   aim_vector=None, up_vector=None):
    """
    Fix orientation for a specific joint with explicit control over aim and up directions.

    Args:
        joint (str): Joint to fix
        aim_axis (str): Primary axis for the joint ('x', 'y', or 'z')
        up_axis (str): Secondary axis for the joint ('x', 'y', or 'z')
        aim_vector (list): Optional explicit aim vector
        up_vector (list): Optional explicit up vector

    Returns:
        bool: True if successful
    """
    if not cmds.objExists(joint):
        return False

    # Get child to determine aim direction if not provided
    if aim_vector is None:
        children = cmds.listRelatives(joint, children=True, type="joint")
        if children:
            child_pos = cmds.xform(children[0], query=True, translation=True, worldSpace=True)
            joint_pos = cmds.xform(joint, query=True, translation=True, worldSpace=True)

            # Calculate aim vector to child
            aim_vector = vector_from_two_points(joint_pos, child_pos)

            # Normalize
            aim_vector = normalize_vector(aim_vector)
        else:
            # No child, use parent's orientation
            parent = cmds.listRelatives(joint, parent=True, type="joint")
            if parent:
                # Get parent's matrix and extract aim axis
                parent_matrix = cmds.xform(parent[0], query=True, matrix=True, worldSpace=True)
                if aim_axis.lower() == 'x':
                    aim_vector = [parent_matrix[0], parent_matrix[1], parent_matrix[2]]
                elif aim_axis.lower() == 'y':
                    aim_vector = [parent_matrix[4], parent_matrix[5], parent_matrix[6]]
                else:  # z
                    aim_vector = [parent_matrix[8], parent_matrix[9], parent_matrix[10]]
            else:
                # No parent either, use default
                aim_vector = [1, 0, 0]

    # Get up vector if not provided
    if up_vector is None:
        if up_axis is None:
            # Default up vector based on aim direction
            if abs(aim_vector[1]) < 0.9:  # If not pointing mostly along Y
                up_vector = [0, 1, 0]  # Use world Y
            else:
                up_vector = [0, 0, 1]  # Use world Z if aim is along Y
        else:
            # Use axis from parent's orientation
            parent = cmds.listRelatives(joint, parent=True, type="joint")
            if parent:
                parent_matrix = cmds.xform(parent[0], query=True, matrix=True, worldSpace=True)
                if up_axis.lower() == 'x':
                    up_vector = [parent_matrix[0], parent_matrix[1], parent_matrix[2]]
                elif up_axis.lower() == 'y':
                    up_vector = [parent_matrix[4], parent_matrix[5], parent_matrix[6]]
                else:  # z
                    up_vector = [parent_matrix[8], parent_matrix[9], parent_matrix[10]]
            else:
                # No parent, use world up
                up_vector = [0, 1, 0]

    # Apply orientation
    return apply_orientation_to_joint(joint, aim_vector, up_vector,
                                     primary_axis=aim_axis,
                                     secondary_axis=up_axis if up_axis else SECONDARY_AXIS)