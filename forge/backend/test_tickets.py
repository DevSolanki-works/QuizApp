"""
Simple smoke test for Forge generation tickets.

Run from forge/backend:
    python test_tickets.py
"""

from __future__ import annotations

import os
import tempfile


def main() -> None:
    tmpdir = tempfile.TemporaryDirectory()
    os.environ["PROFILE_STORE_PATH"] = os.path.join(tmpdir.name, "profiles.json")

    from app.services.profiles import apply_delta
    from app.services.tickets import (
        TicketError,
        buy_tickets_with_coins,
        get_or_reset_tickets,
        grant_ad_ticket,
        spend_ticket,
    )

    user_id = "ticket-test-user"

    state = get_or_reset_tickets(user_id)
    assert state["tickets_today"] == 3, state

    state = spend_ticket(user_id)
    assert state["tickets_today"] == 2, state

    grant_results = [grant_ad_ticket(user_id) for _ in range(6)]
    assert all(result["ok"] for result in grant_results[:5]), grant_results
    assert grant_results[-1]["ok"] is False, grant_results[-1]
    assert grant_results[-1]["ad_tickets_used_today"] == 5, grant_results[-1]

    apply_delta(user_id, coins_delta=50)
    state = buy_tickets_with_coins(user_id, 1)
    assert state["tickets_today"] == 8, state
    assert state["coins"] == 200.0, state

    for _ in range(8):
        spend_ticket(user_id)
    try:
        spend_ticket(user_id)
    except TicketError:
        pass
    else:
        raise AssertionError("Expected TicketError when tickets are exhausted")

    tmpdir.cleanup()
    print("Ticket smoke test passed.")


if __name__ == "__main__":
    main()
