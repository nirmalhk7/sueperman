"""Pure transition and redelivery invariants, without database or transport doubles."""

from dataclasses import replace
from uuid import UUID

import pytest
from test_local_core import core, fixture_data, inputs


def researched():
    module = core()
    products, recall = fixture_data()
    state = module.CaseState(inputs(products[0], recall))
    state, commands = module.reduce_case(state, module.Start())
    request = commands[0].message
    report = module.actor_reply(request, state.context)
    return module, state, report


def test_duplicate_delivery():
    module, state, report = researched()
    accepted, _ = module.reduce_case(state, report)
    repeated, commands = module.reduce_case(accepted, report)
    assert repeated == accepted
    assert commands == ()


def test_conflicting_duplicate():
    module, state, report = researched()
    accepted, _ = module.reduce_case(state, report)
    bad = report.model_copy(update={"payload": report.payload.model_copy(update={"truncated": True})})
    with pytest.raises(ValueError, match="Conflicting"):
        module.reduce_case(accepted, bad)


def test_wrong_sender_revision():
    module, state, report = researched()
    for bad in [report.model_copy(update={"sender": "builder"}),
                report.model_copy(update={"expected_case_revision": 99}),
                report.model_copy(update={"task_id": UUID(int=900)})]:
        with pytest.raises(ValueError):
            module.reduce_case(state, bad)


def test_terminal_late_message():
    module, state, report = researched()
    state = replace(state, phase="DONE", outcome="rejected")
    assert module.reduce_case(state, report) == (state, ())


def test_completed_task_new_message_is_noop():
    module, state, report = researched()
    accepted, _ = module.reduce_case(state, report)
    repeated = report.model_copy(update={"message_id": UUID(int=999)})
    assert module.reduce_case(accepted, repeated) == (accepted, ())


def followup_state():
    module = core()
    products, recall = fixture_data()
    recall = recall.model_copy(update={"models": []})
    context = inputs(products[0], recall)
    state = module.CaseState(context)
    state, commands = module.reduce_case(state, module.Start())
    state, commands = module.reduce_case(state, module.actor_reply(commands[0].message, context))
    review = module.actor_reply(commands[0].message, context)
    return module, state, review


def test_public_followup():
    module, state, review = followup_state()
    following, commands = module.reduce_case(state, review)
    assert following.phase == "FOLLOWUP"
    assert following.followups == 1
    assert commands[0].message.type == "FollowUpRequested"
    assert commands[0].message.payload.requested_fields == ["affected_models"]


def test_unresolved_second_review():
    module, state, review = followup_state()
    state, commands = module.reduce_case(state, review)
    state, commands = module.reduce_case(state, module.actor_reply(commands[0].message, state.context))
    state, commands = module.reduce_case(state, module.actor_reply(commands[0].message, state.context))
    assert state.phase == "DONE"
    assert state.outcome == "needs_review"
    assert state.followups == 1
    assert not any(c.message for c in commands)


def test_review_cannot_override_matcher():
    module, state, review = followup_state()
    forged = review.model_copy(update={"payload": review.payload.model_copy(
        update={"rule_result": "verified_match", "requested_fields": []})})
    with pytest.raises(ValueError, match="authoritative"):
        module.reduce_case(state, forged)


def test_failure_must_come_from_assigned_actor():
    module, state, report = researched()
    failed = report.model_copy(update={"sender": "skeptic", "type": "TaskFailed",
        "payload": module.failure_reply(module.request(state, "ResearchRequested",
            {"product_ref": "p"}, "RESEARCHING")[1][0].message, "INVALID_RESULT").payload})
    with pytest.raises(ValueError, match="assigned actor"):
        module.reduce_case(state, failed)


def test_unavailable_research_is_not_a_no_match():
    module, state, report = researched()
    unavailable = report.model_copy(update={"source_refs": [], "payload": report.payload.model_copy(
        update={"candidate_refs": [], "coverage": "unavailable"})})
    final, _ = module.reduce_case(state, unavailable)
    assert final.outcome is None
    assert final.failure == "SOURCE_UNAVAILABLE"


def test_public_followup_facts_are_consumed():
    module = core()
    products, complete = fixture_data()
    missing = complete.model_copy(update={"models": []})
    context = replace(inputs(products[0], missing), records_json=(missing.model_dump_json(), complete.model_dump_json()))
    state, commands = module.reduce_case(module.CaseState(context), module.Start())
    request = commands[0].message
    # Recorded source adapter initially supplies only the incomplete snapshot.
    first_ref, second_ref = context.sources
    report = module.reply(request, "ResearchReport", {"candidate_refs": [first_ref],
        "coverage": "supported_scope", "truncated": False}, [first_ref])
    state, commands = module.reduce_case(state, report)
    state, commands = module.reduce_case(state, module.actor_reply(commands[0].message, context))
    followup = module.reply(commands[0].message, "FollowUpReport",
        {"evidence_refs": [second_ref], "unavailable_reason": None}, [second_ref])
    state, commands = module.reduce_case(state, followup)
    state, commands = module.reduce_case(state, module.actor_reply(commands[0].message, context))
    assert state.phase == "BUILDING"
    assert state.source_refs == (second_ref,)
    assert state.followups == 1


def test_review_must_cite_assigned_snapshot():
    module, state, review = followup_state()
    uncited = review.model_copy(update={"source_refs": []})
    with pytest.raises(ValueError, match="assigned snapshot"):
        module.reduce_case(state, uncited)
