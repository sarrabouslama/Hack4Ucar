"""
Compatibility wrapper for ranking and scoring.
"""

from app.modules.finance_partnerships_hr.rankings.scoring import (  # noqa: F401
    compute_composite_score,
    get_anonymous_rankings,
    get_full_rankings,
)
