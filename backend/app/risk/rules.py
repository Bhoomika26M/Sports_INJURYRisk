"""Biomechanical risk rules for different activities."""

from typing import Dict, List, Optional


class RiskRuleSet:
    """Activity-specific risk rules and thresholds."""

    def squat_rules(self) -> Dict:
        return {
            "knee_valgus_threshold": 10.0,  # degrees of valgus (outward collapse)
            "excessive_trunk_lean": 20.0,  # degrees
            "min_acceptable_rom_knee": 80.0,  # deep squat target
            "max_acceptable_rom_knee": 130.0,
            "asymmetry_tolerance_deg": 5.0,
        }

    def jump_rules(self) -> Dict:
        return {
            "knee_valgus_threshold": 8.0,
            "asymmetry_tolerance_deg": 4.0,
            "excessive_trunk_lean": 15.0,
        }

    def running_rules(self) -> Dict:
        return {
            "knee_valgus_threshold": 12.0,
            "asymmetry_tolerance_deg": 6.0,
            "hip_drop_threshold": 5.0,  # Trendelenburg-like
        }
