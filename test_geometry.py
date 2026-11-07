import unittest
import numpy as np
from geometry import translation, rotation, apply_translation, apply_at_current_center


class GeometryTests(unittest.TestCase):
    def test_translation(self):
        m = apply_translation(np.eye(4), 'x', 0.25)
        np.testing.assert_allclose(m @ [1, 2, 3, 1], [1.25, 2, 3, 1])

    def test_rotate_about_center(self):
        m = translation(2, 0, 0)
        center = [10, 0, 0]
        r = apply_at_current_center(m, center, 'z', 90)
        np.testing.assert_allclose(r @ [10, 0, 0, 1], [12, 0, 0, 1], atol=1e-10)
        np.testing.assert_allclose(r @ [11, 0, 0, 1], [12, 1, 0, 1], atol=1e-10)

    def test_rotation_preserves_length(self):
        m = rotation('y', 37)
        p = m @ [2, 3, 4, 0]
        self.assertAlmostEqual(np.linalg.norm(p[:3]), np.sqrt(29))


if __name__ == '__main__':
    unittest.main()
