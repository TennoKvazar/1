"""Pure geometry helpers used by OrthoSim. Coordinates are assumed to be mm."""
from __future__ import annotations

import numpy as np


def translation(dx: float = 0, dy: float = 0, dz: float = 0) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = (dx, dy, dz)
    return m


def rotation(axis: str, degrees: float) -> np.ndarray:
    theta = np.deg2rad(degrees)
    c, s = np.cos(theta), np.sin(theta)
    r = np.eye(4)
    if axis == 'x':
        r[:3, :3] = [[1, 0, 0], [0, c, -s], [0, s, c]]
    elif axis == 'y':
        r[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    elif axis == 'z':
        r[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    else:
        raise ValueError('Axis must be x, y, or z')
    return r


def apply_at_current_center(matrix: np.ndarray, original_center, axis: str, degrees: float):
    """Pre-multiply rotation around the current position of the source center."""
    point = np.append(np.asarray(original_center, dtype=float), 1.0)
    current_center = (matrix @ point)[:3]
    return (translation(*current_center) @ rotation(axis, degrees)
            @ translation(*(-current_center)) @ matrix)


def apply_translation(matrix: np.ndarray, axis: str, distance_mm: float) -> np.ndarray:
    vector = dict(x=(distance_mm, 0, 0), y=(0, distance_mm, 0), z=(0, 0, distance_mm))
    if axis not in vector:
        raise ValueError('Axis must be x, y, or z')
    return translation(*vector[axis]) @ matrix
