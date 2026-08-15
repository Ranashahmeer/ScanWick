"""Manual smoke test for the Flutterwave client — NOT run in CI.

Hits the real Flutterwave API (test mode, if you're using a test secret key
— which you should be, this creates a real checkout link), so it needs a
valid FLUTTERWAVE_SECRET_KEY in .env. Run by hand:

    python scripts/smoke_test_flutterwave.py

What this checks: `initialize_payment` returns a real `authorization_url`
and `reference` in the shape `flutterwave_client.py` expects — the response
shape was written from Flutterwave's public docs, not verified against a
live account, so this is the first real check of that assumption. Prints
the full raw response too, so you can compare field-by-field against what
`initialize_payment`/`verify_transaction` in flutterwave_client.py actually
reads.
"""

import asyncio

from app.services.flutterwave_client import (
    FlutterwaveAPIError,
    initialize_payment,
    verify_transaction,
)


async def main() -> None:
    print("Initializing a test transaction...")
    try:
        result = await initialize_payment(
            email="smoke-test@example.com",
            amount_kobo=899000,  # NGN 8,990.00
            callback_url="http://localhost:5173/account?tab=billing",
            metadata={"user_id": "smoke-test"},
        )
    except FlutterwaveAPIError as exc:
        print(f"FAILED — Flutterwave API error: {exc}")
        return

    print("Parsed result (what our client extracts):")
    print(f"  authorization_url: {result['authorization_url']}")
    print(f"  reference:         {result['reference']}")

    if not result.get("authorization_url"):
        print(
            "\nWARNING: authorization_url is empty — the response shape our "
            "client parses (`data.link`) may not match what Flutterwave "
            "actually returned. Check the raw response above/below."
        )
        return

    print(f"\nOpen this URL in a browser to see the real hosted checkout page:\n  {result['authorization_url']}")

    print("\nVerifying the (still-unpaid) transaction by reference...")
    raw = await verify_transaction(result["reference"])
    print("Raw verify_transaction response (compare field names against flutterwave_client.py's parsing):")
    print(raw)


if __name__ == "__main__":
    asyncio.run(main())
