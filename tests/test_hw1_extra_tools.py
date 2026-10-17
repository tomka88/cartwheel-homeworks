"""Tests for the additional HW1 tools added beyond the five required ones."""

from __future__ import annotations

import sqlite3

from agent import tools
from agent.agent import TOOLS_BY_ROLE
from agent.auth import AuthContext

SHOPPER_1 = AuthContext(user_id=1, role="shopper")
SHOPPER_2 = AuthContext(user_id=2, role="shopper")
MERCHANT_STORE_1 = AuthContext(user_id=9001, role="merchant", store_id=1)
MERCHANT_STORE_2 = AuthContext(user_id=9002, role="merchant", store_id=2)
SUPPORT = AuthContext(user_id=9501, role="support")


def _product_title(db_path, order_id: int) -> str:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT p.title FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ?",
            (order_id,),
        ).fetchone()[0]
    finally:
        conn.close()


def test_get_order_item_names_the_product_for_authorized_roles(world: dict) -> None:
    title = _product_title(world["db"], 4127)
    for ctx in (SHOPPER_1, MERCHANT_STORE_1, SUPPORT):
        result = tools.get_order_item(ctx, 4127)
        assert result["ok"] is True
        assert result["order_id"] == 4127
        assert result["title"] == title
        assert result["store_name"] == "Blue Heron Ceramics"
        assert result["quantity"] >= 1
        assert result["data_issues"] == []


def test_get_order_item_denies_out_of_scope_callers(world: dict) -> None:
    for ctx in (SHOPPER_2, MERCHANT_STORE_2):
        result = tools.get_order_item(ctx, 4127)
        assert result["ok"] is False
        assert result["error"] == "permission_denied"
        # The denial must not leak anything about the order's contents.
        assert "title" not in result
        assert _product_title(world["db"], 4127) not in result["reason"]


def test_get_order_item_unknown_order(world: dict) -> None:
    result = tools.get_order_item(SHOPPER_1, 999_999)
    assert result["ok"] is False
    assert result["error"] == "not_found"


def test_get_order_item_reports_amount_paid_separately_from_catalog_price(world: dict) -> None:
    # Pinned demo order 4127 was paid at a different price than today's list price.
    result = tools.get_order_item(SHOPPER_1, 4127)
    conn = sqlite3.connect(world["db"])
    try:
        total_cents = conn.execute("SELECT total_cents FROM orders WHERE id = 4127").fetchone()[0]
    finally:
        conn.close()
    assert result["total_usd"] == total_cents / 100
    assert result["catalog_price_usd"] != result["total_usd"]


def test_get_order_item_flags_missing_title_and_invalid_price(world_copy) -> None:
    # Seeded data-quality defects: product 3 has an empty title, product 4 a negative price.
    conn = sqlite3.connect(world_copy)
    try:
        order_id = conn.execute("SELECT id FROM orders ORDER BY id LIMIT 1").fetchone()[0]
        conn.execute("UPDATE orders SET product_id = 3, store_id = 1 WHERE id = ?", (order_id,))
        conn.commit()
    finally:
        conn.close()
    missing_title = tools.get_order_item(SUPPORT, order_id)
    assert missing_title["ok"] is True
    assert missing_title["title"] is None
    assert missing_title["data_issues"]

    conn = sqlite3.connect(world_copy)
    try:
        conn.execute("UPDATE orders SET product_id = 4 WHERE id = ?", (order_id,))
        conn.commit()
    finally:
        conn.close()
    invalid_price = tools.get_order_item(SUPPORT, order_id)
    assert invalid_price["catalog_price_usd"] is None
    assert invalid_price["data_issues"]


def test_get_order_item_refuses_store_mismatch(world: dict) -> None:
    # Seeded data-quality defect: order 8003 references another store's product.
    result = tools.get_order_item(SUPPORT, 8003)
    assert result["ok"] is False
    assert result["error"] == "inconsistent_record"


def test_get_order_item_is_registered_for_every_role() -> None:
    for role, role_tools in TOOLS_BY_ROLE.items():
        assert "get_order_item" in {tool.name for tool in role_tools}, role
