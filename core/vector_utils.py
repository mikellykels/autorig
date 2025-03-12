"""
Modular Rig System
Vector Math Utilities

This module provides vector math operations without requiring numpy.
Uses Maya's native vector capabilities and Python's math module.

Author: Mikaela Carino
Date: 2025
"""

import maya.cmds as cmds
import math
import maya.api.OpenMaya as om


def vector_from_two_points(point1, point2):
    """
    Calculate a vector from point1 to point2.

    Args:
        point1 (list/tuple): First point (x, y, z)
        point2 (list/tuple): Second point (x, y, z)

    Returns:
        list: The vector [x, y, z]
    """
    return [
        point2[0] - point1[0],
        point2[1] - point1[1],
        point2[2] - point1[2]
    ]


def vector_length(vector):
    """
    Calculate the length (magnitude) of a vector.

    Args:
        vector (list/tuple): Vector [x, y, z]

    Returns:
        float: The length of the vector
    """
    return math.sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2])


def normalize_vector(vector):
    """
    Normalize a vector to unit length.

    Args:
        vector (list/tuple): Vector [x, y, z]

    Returns:
        list: Normalized vector
    """
    length = vector_length(vector)
    if length < 0.0001:  # Avoid division by zero
        return [0, 0, 0]

    return [
        vector[0] / length,
        vector[1] / length,
        vector[2] / length
    ]


def dot_product(vector1, vector2):
    """
    Calculate dot product of two vectors.

    Args:
        vector1 (list/tuple): First vector [x, y, z]
        vector2 (list/tuple): Second vector [x, y, z]

    Returns:
        float: Dot product
    """
    return (vector1[0] * vector2[0] +
            vector1[1] * vector2[1] +
            vector1[2] * vector2[2])


def cross_product(vector1, vector2):
    """
    Calculate cross product of two vectors.

    Args:
        vector1 (list/tuple): First vector [x, y, z]
        vector2 (list/tuple): Second vector [x, y, z]

    Returns:
        list: Cross product vector
    """
    return [
        vector1[1] * vector2[2] - vector1[2] * vector2[1],
        vector1[2] * vector2[0] - vector1[0] * vector2[2],
        vector1[0] * vector2[1] - vector1[1] * vector2[0]
    ]


def scale_vector(vector, scalar):
    """
    Multiply a vector by a scalar.

    Args:
        vector (list/tuple): Vector [x, y, z]
        scalar (float): Scaling factor

    Returns:
        list: Scaled vector
    """
    return [
        vector[0] * scalar,
        vector[1] * scalar,
        vector[2] * scalar
    ]


def add_vectors(vector1, vector2):
    """
    Add two vectors.

    Args:
        vector1 (list/tuple): First vector [x, y, z]
        vector2 (list/tuple): Second vector [x, y, z]

    Returns:
        list: Sum vector
    """
    return [
        vector1[0] + vector2[0],
        vector1[1] + vector2[1],
        vector1[2] + vector2[2]
    ]


def subtract_vectors(vector1, vector2):
    """
    Subtract vector2 from vector1.

    Args:
        vector1 (list/tuple): First vector [x, y, z]
        vector2 (list/tuple): Second vector [x, y, z]

    Returns:
        list: Difference vector (vector1 - vector2)
    """
    return [
        vector1[0] - vector2[0],
        vector1[1] - vector2[1],
        vector1[2] - vector2[2]
    ]


def get_midpoint(point1, point2):
    """
    Calculate the midpoint between two points.

    Args:
        point1 (list/tuple): First point [x, y, z]
        point2 (list/tuple): Second point [x, y, z]

    Returns:
        list: Midpoint [x, y, z]
    """
    return [
        (point1[0] + point2[0]) / 2.0,
        (point1[1] + point2[1]) / 2.0,
        (point1[2] + point2[2]) / 2.0
    ]


def angle_between_vectors(vector1, vector2):
    """
    Calculate the angle between two vectors in radians.

    Args:
        vector1 (list/tuple): First vector [x, y, z]
        vector2 (list/tuple): Second vector [x, y, z]

    Returns:
        float: Angle in radians
    """
    dot = dot_product(vector1, vector2)
    mag1 = vector_length(vector1)
    mag2 = vector_length(vector2)

    # Avoid division by zero
    if mag1 < 0.0001 or mag2 < 0.0001:
        return 0

    # Clamp to valid range to avoid floating point errors
    cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.acos(cos_angle)


def angle_between_vectors_deg(vector1, vector2):
    """
    Calculate the angle between two vectors in degrees.

    Args:
        vector1 (list/tuple): First vector [x, y, z]
        vector2 (list/tuple): Second vector [x, y, z]

    Returns:
        float: Angle in degrees
    """
    return math.degrees(angle_between_vectors(vector1, vector2))


def project_vector_onto_plane(vector, plane_normal):
    """
    Project a vector onto a plane defined by its normal.

    Args:
        vector (list/tuple): Vector to project [x, y, z]
        plane_normal (list/tuple): Normal vector of the plane [x, y, z]

    Returns:
        list: Projected vector
    """
    normal = normalize_vector(plane_normal)
    dot = dot_product(vector, normal)

    return [
        vector[0] - normal[0] * dot,
        vector[1] - normal[1] * dot,
        vector[2] - normal[2] * dot
    ]


def make_vectors_planar(vectors, preserve_length=True):
    """
    Project a list of vectors onto a best-fit plane.

    Args:
        vectors (list): List of 3D vectors [[x1,y1,z1], [x2,y2,z2], ...]
        preserve_length (bool): Whether to maintain original vector lengths

    Returns:
        list: Adjusted vectors that are planar
    """
    if len(vectors) < 3:
        return vectors  # Too few vectors to determine a plane

    # Convert to Maya MVector objects for easier manipulation
    mvectors = [om.MVector(v[0], v[1], v[2]) for v in vectors]

    # Calculate an approximate plane normal by using the first three points
    v1 = mvectors[1] - mvectors[0]
    v2 = mvectors[2] - mvectors[0]
    normal = v1 ^ v2  # Cross product in Maya API syntax

    if normal.length() < 0.0001:
        # Points are collinear, try another combination
        for i in range(1, len(mvectors) - 1):
            v1 = mvectors[i] - mvectors[0]
            v2 = mvectors[i + 1] - mvectors[0]
            normal = v1 ^ v2
            if normal.length() >= 0.0001:
                break

    # If still couldn't find a good normal, use the world up vector
    if normal.length() < 0.0001:
        normal = om.MVector(0, 1, 0)

    normal.normalize()

    # Project each vector onto the plane
    planar_vectors = []

    for i, mvector in enumerate(mvectors):
        # Project onto plane
        dot = mvector * normal  # Dot product in Maya API syntax
        projection = mvector - normal * dot

        # Preserve original length if requested
        if preserve_length and i > 0:
            original_length = (mvectors[i] - mvectors[i - 1]).length()
            direction = projection - om.MVector(planar_vectors[-1])
            if direction.length() > 0.0001:
                direction.normalize()
                projection = om.MVector(planar_vectors[-1]) + direction * original_length

        planar_vectors.append([projection.x, projection.y, projection.z])

    return planar_vectors


def is_planar(positions, tolerance=0.01):
    """
    Check if a set of positions forms a planar arrangement.

    Args:
        positions (list): List of 3D positions [[x1,y1,z1], [x2,y2,z2], ...]
        tolerance (float): Maximum allowed deviation from planarity

    Returns:
        bool: True if the positions are approximately planar
    """
    if len(positions) < 4:
        return True  # Three or fewer points are always planar

    # Convert to Maya MVectors
    mvectors = [om.MVector(p[0], p[1], p[2]) for p in positions]

    # Calculate plane normal from first three points
    v1 = mvectors[1] - mvectors[0]
    v2 = mvectors[2] - mvectors[0]
    normal = v1 ^ v2  # Cross product

    if normal.length() < 0.0001:
        # First three points are collinear, try another triple
        for i in range(1, len(mvectors) - 2):
            v1 = mvectors[i] - mvectors[0]
            v2 = mvectors[i + 1] - mvectors[0]
            normal = v1 ^ v2
            if normal.length() >= 0.0001:
                break

    # If we couldn't find a valid normal, consider it planar
    if normal.length() < 0.0001:
        return True

    normal.normalize()

    # Check if all points are within tolerance of the plane
    for mvector in mvectors[3:]:
        # Calculate distance to plane
        distance = abs((mvector - mvectors[0]) * normal)  # Dot product with normal
        if distance > tolerance:
            return False

    return True


def create_rotation_matrix(aim_vector, up_vector):
    """
    Create a rotation matrix from aim and up vectors.

    Args:
        aim_vector (list): Aim vector (typically X axis)
        up_vector (list): Up vector (typically Y axis)

    Returns:
        list: 16-element list representing 4x4 transformation matrix
    """
    # Convert to Maya API vectors for easier manipulation
    aim = om.MVector(aim_vector[0], aim_vector[1], aim_vector[2])
    up = om.MVector(up_vector[0], up_vector[1], up_vector[2])

    # Normalize vectors
    aim.normalize()
    up.normalize()

    # Calculate side vector (equivalent to cross product)
    side = aim ^ up
    side.normalize()

    # Recalculate up to ensure orthogonality
    up = side ^ aim
    up.normalize()

    # Create transformation matrix
    matrix = [
        aim.x, aim.y, aim.z, 0,
        up.x, up.y, up.z, 0,
        side.x, side.y, side.z, 0,
        0, 0, 0, 1
    ]

    return matrix