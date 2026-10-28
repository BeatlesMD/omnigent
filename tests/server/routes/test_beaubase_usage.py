"""Run in pinned upstream pytest to verify the retired-agent Usage fallback."""
import pytest

from omnigent.errors import ErrorCode, OmnigentError
from omnigent.server.routes.usage import _build_usage_report
from omnigent.stores.conversation_store.sqlalchemy_store import SqlAlchemyConversationStore
from tests.server.routes.test_usage_report import _add_session


def test_invalid_retired_agent_keeps_usage(db_uri, monkeypatch):
    store = SqlAlchemyConversationStore(db_uri)
    session_id = _add_session(store, monkeypatch, ts=1_784_678_400, cost=1.25,
                              by_model={"historic-model": {"total_cost_usd": 1.25}},
                              title="retired agent")
    store.add_daily_cost("local", "2026-07-22", 1.25)
    def unavailable(_conv):
        raise OmnigentError("function tool has no resolved callable", code=ErrorCode.INVALID_INPUT)
    monkeypatch.setattr("omnigent.server.routes.usage._resolve_harness_impl", unavailable)
    monkeypatch.setattr("omnigent.server.routes.usage._resolve_llm_model", unavailable)
    report = _build_usage_report(store, None, include_page_details=True)
    session = next(s for s in report.sessions if s.id == session_id)
    assert report.total_cost_usd == 1.25
    assert session.cost_usd == 1.25
    assert session.models == {"historic-model": 1.25}
    assert session.harness is None and session.llm_model is None


@pytest.mark.parametrize("resolver", ["_resolve_harness_impl", "_resolve_llm_model"])
@pytest.mark.parametrize("code", [ErrorCode.INTERNAL_ERROR, ErrorCode.FORBIDDEN])
def test_other_errors_still_propagate(db_uri, monkeypatch, resolver, code):
    store = SqlAlchemyConversationStore(db_uri)
    _add_session(store, monkeypatch, ts=1_784_678_400, cost=1.0,
                 by_model={}, title="broken dependency")
    def unavailable(_conv):
        raise OmnigentError("real failure", code=code)
    monkeypatch.setattr("omnigent.server.routes.usage." + resolver, unavailable)
    with pytest.raises(OmnigentError) as error:
        _build_usage_report(store, None, include_page_details=True)
    assert error.value.code == code
