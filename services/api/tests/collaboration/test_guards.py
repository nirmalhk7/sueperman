"""Catch model laundering, invented conditions, sensitive payloads and wasted questions."""

import pytest

from app.schemas import ProductInput


def roles():
    try:
        from app.collaboration import roles

        return roles
    except ImportError:
        pytest.fail("Bounded offline roles missing")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model,expected",
    [
        ("ZHX-PB22", "verified_match"),
        ("ZHX-PB23", "rejected"),
        ("ZHX-PB22-A", "rejected"),
        ("ZHXPB22", "rejected"),
        ("ZHX.PB22", "rejected"),
        (None, "needs_review"),
    ],
)
async def test_supported_model_boundary_is_exact(model, expected):
    r = roles()
    scout = await r.scout(
        ProductInput(product_name="Portable Power Bank", brand="NEWDERY", model_number=model)
    )
    challenge = r.skeptic(
        ProductInput(product_name="Portable Power Bank", brand="NEWDERY", model_number=model), scout
    )
    assert challenge.status == expected


def test_message_projection_excludes_receipts_orders_and_unneeded_purchase_facts():
    r = roles()
    product = ProductInput(
        product_name="Power Bank",
        brand="NEWDERY",
        model_number="ZHX-PB22",
        merchant="PRIVATE",
        order_reference_redacted="PRIVATE-ORDER",
        date_purchased="2024-06-12",
        region="PRIVATE-REGION",
    )
    assert r.public_facts(product) == {
        "product_name": "Power Bank",
        "brand": "NEWDERY",
        "model_number": "ZHX-PB22",
    }


def test_one_question_skips_conditions_not_required_by_notice():
    r = roles()
    assert r.next_question(["region", "date_purchased", "batch", "model_number"]) == "model_number"
    assert r.next_question(["region", "date_purchased", "batch"]) == "batch"
    assert r.next_question(["unsupported_source_conditions"]) is None


@pytest.mark.asyncio
async def test_unknown_notice_and_changed_restrictions_require_review():
    r = roles()
    product = ProductInput(product_name="Power Bank", brand="NEWDERY", model_number="ZHX-PB22")
    recall = await r.scout(product)
    for changed in ({"reference": "99-999"}, {"excerpt": recall.excerpt + " Only batch X is affected."}):
        challenge = r.skeptic(product, recall.model_copy(update=changed))
        assert challenge.status == "needs_review"
        assert any(
            c.name == "unsupported_source_conditions" and c.status == "unknown" for c in challenge.conditions
        )


@pytest.mark.asyncio
async def test_builder_rejects_agent_pass_assertions_for_false_or_unknown_gates():
    r = roles()
    from app.collaboration.contracts import CaseResult, Finding

    for model in ("ZHX-PB23", None):
        product = ProductInput(product_name="Power Bank", brand="NEWDERY", model_number=model)
        recall = await r.scout(product)
        fabricated = CaseResult(
            task_id="task",
            case_id="case",
            revision=1,
            provider="offline_rules",
            mode="replay",
            status="completed",
            source_refs=["26-792"],
            findings=[Finding(code="condition_passed", condition="model_number", source_ref="26-792")],
        )
        with pytest.raises(ValueError, match="challenge"):
            r.builder(product, recall, fabricated)
