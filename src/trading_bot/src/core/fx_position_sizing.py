"""
FX Position Sizing Utilities - compute broker units from dollar risk using
instrument pip location and home conversion rate.
"""
from decimal import Decimal


def compute_units_from_risk(
    pip_location: float,
    conversion_rate: float,
    entry_price: Decimal,
    stop_loss: Decimal,
    risk_amount: Decimal,
) -> float:
    """Compute units to trade based on risk amount and SL distance.

    Args:
        pip_location: Instrument pip location (e.g., 0.0001 for most majors, 0.01 for JPY pairs).
        conversion_rate: Home conversion rate (buy_conv for BUY, sell_conv for SELL).
        entry_price: Proposed entry price.
        stop_loss: Proposed stop loss price.
        risk_amount: Dollar risk per trade.

    Returns:
        float: units to trade. Returns 0.0 when inputs are invalid.
    """
    try:
        if pip_location is None or conversion_rate is None:
            return 0.0
        pip_location_f = float(pip_location)
        conversion_rate_f = float(conversion_rate)
        if pip_location_f <= 0 or conversion_rate_f <= 0:
            return 0.0

        entry_f = float(entry_price)
        stop_f = float(stop_loss)
        risk_amount_f = float(risk_amount)

        loss = abs(entry_f - stop_f)
        if loss <= 0:
            return 0.0

        num_pips = loss / pip_location_f
        if num_pips <= 0:
            return 0.0

        per_pip_loss = risk_amount_f / num_pips
        units = per_pip_loss / (conversion_rate_f * pip_location_f)

        return max(0.0, units)
    except Exception:
        return 0.0


