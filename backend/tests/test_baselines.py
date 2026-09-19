import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from app.modules.risk_scoring.baselines import recompute_baseline

@pytest.mark.asyncio
async def test_recompute_baseline_drops_non_finite_values():
    db = AsyncMock()
    # Mock the scalars().all() chain to return a list with nan
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [90.0, 91.0, 89.5, np.nan, 90.5, 88.0]
    db.scalars.return_value = mock_scalars

    res = await recompute_baseline(db, "squatting", "knee_flexion_angle")
    
    assert res["sample_size"] == 5
    assert res["dropped_non_finite"] == 1
