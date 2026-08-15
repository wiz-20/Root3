"""
Shared math for turning a predicted share into (total_wallet, gap) - used by both
elastic_net.py (training/notebook) and predict_wallet.py (inference). Kept in its own
module with no other top-level code so importing it never re-runs training or touches
machine_learning/models/*.pkl - unlike importing elastic_net.py, which runs the full
hyperparameter search and refit as top-level script code.
"""

import numpy as np


def derive_wallet_and_gap(internal_value, predicted_share):
    """
    The 5 ElasticNet targets are all `share = internal / external`, where `internal`
    (Syn Bank's own activity) is already known for any client being predicted on. That means
    predicted_share alone throws away information for free: total_wallet = internal / share,
    gap = total_wallet - internal - the exact relationship the top-down model (Sections 6-7)
    already uses. This turns a share-only prediction into the same (share, total_wallet, gap)
    triple the top-down model reports, which is the useful form for a client where the
    top-down external benchmark is missing or low-reliability - this model only needs internal
    activity, which is always available.

    ElasticNet has no positivity constraint, so predicted_share can come out <= 0 for a thin/
    noisy target (see FX in elastic_net.py). Dividing by a non-positive share would produce an
    inverted or infinite "total wallet", so those cases are reported as not computable (NaN)
    rather than a fabricated number - consistent with how every other reliability gap in this
    project is handled (see PLAN.md, docs/genai/README.md) rather than papered over.

    Accepts and returns either scalars or same-shaped array-likes.
    """
    internal_value = np.asarray(internal_value, dtype=float)
    predicted_share = np.asarray(predicted_share, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        total_wallet = np.where(predicted_share > 0, internal_value / predicted_share, np.nan)
    gap = total_wallet - internal_value
    if total_wallet.ndim == 0:
        return float(total_wallet), float(gap)
    return total_wallet, gap
