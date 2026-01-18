from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def compute_totals(quantity: Decimal, unit_price: Decimal, vat_percent: Decimal) -> dict:
    """Compute subtotal, VAT amount, and total with 2dp Decimal rounding."""
    quant = Decimal("0.01")
    subtotal = (quantity * unit_price).quantize(quant, rounding=ROUND_HALF_UP)
    vat_percent = vat_percent.quantize(quant, rounding=ROUND_HALF_UP)
    vat_amount = (subtotal * vat_percent / Decimal("100")).quantize(
        quant, rounding=ROUND_HALF_UP
    )
    total = (subtotal + vat_amount).quantize(quant, rounding=ROUND_HALF_UP)
    return {
        "subtotal_ex_vat": subtotal,
        "vat_amount": vat_amount,
        "total_inc_vat": total,
        "vat_percent": vat_percent,
    }


def calculate_totals(qty: Decimal, unit_price: Decimal, vat_percent: Decimal) -> dict:
    """Backward compatible totals with legacy key names."""
    totals = compute_totals(qty, unit_price, vat_percent)
    return {
        "subtotal": totals["subtotal_ex_vat"],
        "vat_amount": totals["vat_amount"],
        "total": totals["total_inc_vat"],
        "vat_percent": totals["vat_percent"],
    }


if __name__ == "__main__":
    qty = Decimal("3")
    unit = Decimal("346.00")
    vat = Decimal("24.00")
    totals = compute_totals(qty, unit, vat)
    print(
        f"subtotal={totals['subtotal_ex_vat']}, vat={totals['vat_amount']}, total={totals['total_inc_vat']}"
    )
