from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def calculate_totals(qty: Decimal, unit_price: Decimal, vat_percent: Decimal) -> dict:
    """Calculate subtotal, VAT amount, and total with 2dp Decimal rounding."""
    quant = Decimal("0.01")
    subtotal = (qty * unit_price).quantize(quant, rounding=ROUND_HALF_UP)
    vat_percent = vat_percent.quantize(quant, rounding=ROUND_HALF_UP)
    vat_amount = (subtotal * vat_percent / Decimal("100")).quantize(quant, rounding=ROUND_HALF_UP)
    total = (subtotal + vat_amount).quantize(quant, rounding=ROUND_HALF_UP)
    return {
        "subtotal": subtotal,
        "vat_amount": vat_amount,
        "total": total,
        "vat_percent": vat_percent,
    }


if __name__ == "__main__":
    qty = Decimal("3")
    unit = Decimal("346.00")
    vat = Decimal("24.00")
    totals = calculate_totals(qty, unit, vat)
    print(
        f"subtotal={totals['subtotal']}, vat={totals['vat_amount']}, total={totals['total']}"
    )
