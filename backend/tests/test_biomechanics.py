import pytest
import numpy as np
from app.pose.estimator import Keypoint
from app.biomechanics.calculator import BiomechanicsCalculator


class TestBiomechanicsCalculator:
    """Test biomechanical calculations with synthetic data."""
    
    @pytest.fixture
    def calculator(self):
        return BiomechanicsCalculator()
    
    @pytest.fixture
    def synthetic_keypoints(self):
        """Create synthetic keypoints for testing."""
        keypoints = []
        for i in range(17):
            keypoints.append(Keypoint(x=100.0 + i, y=200.0 + i, confidence=0.9, name=f"keypoint_{i}"))
        return keypoints
    
    def test_joint_angle_calculation(self, calculator, synthetic_keypoints):
        """Test joint angle calculation."""
        # Create a right angle (90 degrees)
        point_a = Keypoint(x=0, y=0, confidence=0.9, name="a")
        point_b = Keypoint(x=10, y=0, confidence=0.9, name="b")
        point_c = Keypoint(x=10, y=10, confidence=0.9, name="c")
        
        angle = calculator.calculate_joint_angle(point_a, point_b, point_c)
        
        assert angle is not None
        assert 85 < angle < 95  # Should be approximately 90 degrees
    
    def test_joint_angle_with_low_confidence(self, calculator, synthetic_keypoints):
        """Test that low confidence keypoints return None."""
        point_a = Keypoint(x=0, y=0, confidence=0.1, name="a")
        point_b = Keypoint(x=10, y=0, confidence=0.9, name="b")
        point_c = Keypoint(x=10, y=10, confidence=0.9, name="c")
        
        angle = calculator.calculate_joint_angle(point_a, point_b, point_c)
        
        assert angle is None
    
    def test_joint_angle_zero_vector(self, calculator):
        """Test handling of zero-length vectors."""
        point_a = Keypoint(x=10, y=0, confidence=0.9, name="a")
        point_b = Keypoint(x=10, y=0, confidence=0.9, name="b")  # Same as a
        point_c = Keypoint(x=10, y=10, confidence=0.9, name="c")
        
        angle = calculator.calculate_joint_angle(point_a, point_b, point_c)
        
        assert angle is None
    
    def test_rom_calculation(self, calculator):
        """Test range of motion calculation."""
        angles = [90, 100, 110, 105, 95]
        
        rom = calculator.calculate_rom(angles)
        
        assert rom["min_angle"] == 90
        assert rom["max_angle"] == 110
        assert rom["rom"] == 20
    
    def test_rom_with_none_values(self, calculator):
        """Test ROM calculation with None values."""
        angles = [90, None, 110, None, 95]
        
        rom = calculator.calculate_rom(angles)
        
        assert rom["min_angle"] == 90
        assert rom["max_angle"] == 110
        assert rom["rom"] == 20
    
    def test_asymmetry_calculation(self, calculator):
        """Test left-right asymmetry calculation."""
        left_values = [90, 92, 88, 91]
        right_values = [85, 87, 83, 86]
        
        asymmetry = calculator.calculate_asymmetry(left_values, right_values)
        
        assert "mean_asymmetry" in asymmetry
        assert "max_asymmetry" in asymmetry
        assert "std_asymmetry" in asymmetry
        assert asymmetry["mean_asymmetry"] > 0
    
    def test_asymmetry_with_none_values(self, calculator):
        """Test asymmetry with None values."""
        left_values = [90, None, 88]
        right_values = [85, 87, None]
        
        asymmetry = calculator.calculate_asymmetry(left_values, right_values)
        
        # Should calculate based on valid pairs
        assert asymmetry["mean_asymmetry"] >= 0
    
    def test_velocity_calculation(self, calculator):
        """Test velocity calculation."""
        values = [10, 20, 30, 40]
        timestamps = [0.0, 1.0, 2.0, 3.0]
        
        velocities = calculator.calculate_velocity(values, timestamps)
        
        assert len(velocities) == len(values)
        assert velocities[0] is None  # First frame has no velocity
        assert velocities[1] == 10.0  # (20-10)/1.0
        assert velocities[2] == 10.0  # (30-20)/1.0
    
    def test_acceleration_calculation(self, calculator):
        """Test acceleration calculation."""
        velocities = [None, 10, 20, 30]
        timestamps = [0.0, 1.0, 2.0, 3.0]
        
        accelerations = calculator.calculate_acceleration(velocities, timestamps)
        
        assert len(accelerations) == len(velocities)
        assert accelerations[0] is None
        assert accelerations[1] is None
        assert accelerations[2] == 10.0  # (20-10)/1.0
