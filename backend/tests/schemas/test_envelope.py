from app.schemas.envelope import error_response, success_response


def test_success_response_minimal_shape():
    result = success_response({"foo": "bar"})

    assert result == {
        "success": True,
        "data": {"foo": "bar"},
        "meta": {
            "missing_fields": [],
            "disabled_features": [],
            "analysis_run_id": None,
            "plan_access": None,
        },
    }


def test_success_response_with_meta_fields():
    result = success_response(
        {"foo": "bar"},
        missing_fields=["cogs"],
        disabled_features=[{"feature_name": "unit_margin", "reason": "COGS missing", "data_needed": "cogs"}],
        analysis_run_id="run-123",
    )

    assert result["success"] is True
    assert result["data"] == {"foo": "bar"}
    assert result["meta"]["missing_fields"] == ["cogs"]
    assert result["meta"]["disabled_features"] == [
        {"feature_name": "unit_margin", "reason": "COGS missing", "data_needed": "cogs"}
    ]
    assert result["meta"]["analysis_run_id"] == "run-123"


def test_error_response_minimal_shape():
    result = error_response("MISSING_COGS", "Unit margin analysis is disabled.")

    assert result == {
        "success": False,
        "error": {
            "code": "MISSING_COGS",
            "message": "Unit margin analysis is disabled.",
            "details": {},
        },
    }


def test_error_response_with_details():
    result = error_response("MISSING_COGS", "Unit margin analysis is disabled.", details={"missing_pct": 22.7})

    assert result["error"]["details"] == {"missing_pct": 22.7}
