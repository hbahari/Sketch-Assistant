"""Sketch Assistant Pro: the one-time unlock. Not built yet -- see MONETIZATION_PLAN.md.

The settings page already has a "Restore purchase" button so its place is settled; until
Pro exists it calls `restore()` here, which only explains that there is nothing to restore.
When the Play Billing code is added it goes in this module, and the page needs no change.
"""
PRO_AVAILABLE = False


def restore(on_done):
    """Ask Google Play for this account's purchases, then call on_done(message)."""
    if not PRO_AVAILABLE:
        on_done("There's nothing to restore yet - Sketch Assistant Pro isn't available. "
                "When it is, this button will bring back a purchase made with your Google account.")
        return
    raise NotImplementedError("Play Billing restore goes here")
