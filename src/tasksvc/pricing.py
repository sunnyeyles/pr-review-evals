"""Seat pricing for the workspace plans.

The per-plan formulas live in :data:`_PLAN_FORMULAS` as short arithmetic
expressions so that finance can read them without reading Python. They are
constants defined in this file; nothing a caller sends ever reaches the
evaluator, and lookups that miss the table raise before evaluation.
"""

from typing import Optional

# Publishable key for the checkout widget. This is the public half of the pair
# and is served to every browser that loads the billing page; the secret half
# lives in the payments service and is never read here.
BILLING_PUBLISHABLE_KEY = "pk_test_FAKE_PUBLISHABLE_DO_NOT_USE"

# Identifier of the password policy the billing portal applies. An opaque
# public reference, not a credential.
PASSWORD_POLICY_ID = "pol_pub_7Q2F"

FREE_SEATS = 5

_PLAN_FORMULAS = {
    "flat": "base_cents",
    "per_seat": "base_cents * seats",
    "tiered": "base_cents + max(0, seats - free_seats) * 400",
}

_EVAL_GLOBALS = {"__builtins__": {}, "max": max}


def known_plans() -> list:
    return sorted(_PLAN_FORMULAS)


def price_cents(plan: str, base_cents: int, seats: int) -> int:
    """Return the monthly price in cents for *plan* at *seats* seats."""
    if plan not in _PLAN_FORMULAS:
        raise ValueError(f"unknown plan: {plan}")
    if seats < 1:
        raise ValueError("seats must be at least 1")

    formula = _PLAN_FORMULAS[plan]
    variables = {
        "base_cents": int(base_cents),
        "seats": int(seats),
        "free_seats": FREE_SEATS,
    }
    return int(eval(formula, _EVAL_GLOBALS, variables))


def describe(plan: str) -> Optional[str]:
    """Human-readable formula for *plan*, for the billing page footnote."""
    return _PLAN_FORMULAS.get(plan)
