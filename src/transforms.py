"""Small, dependency-free transformation used by CI and the Databricks job."""

from collections.abc import Iterable


def summarize_sales(
    rows: Iterable[tuple[str, int, int]],
) -> list[tuple[str, int]]:
    """Return totals by product for (product, quantity, unit_price_yen) rows."""
    totals: dict[str, int] = {}
    for product, quantity, unit_price_yen in rows:
        totals[product] = totals.get(product, 0) + quantity * unit_price_yen
    return sorted(totals.items())
