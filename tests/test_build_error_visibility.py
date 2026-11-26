"""Build-driver fatal-error visibility regression tests."""

def test_log_error_is_counted(capsys):
    import scripts.common as common
    old = common.ERROR_COUNT
    try:
        common.ERROR_COUNT = 0
        common.log("ERROR", "forced phase failure")
        assert common.ERROR_COUNT == 1
        common.log("DONE", "not an error")
        assert common.ERROR_COUNT == 1
    finally:
        common.ERROR_COUNT = old
    assert "forced phase failure" in capsys.readouterr().out


def test_build_driver_refuses_success_after_phase_errors():
    src = open("scripts/build.py", encoding="utf-8").read()
    assert "_scripts_common.ERROR_COUNT = 0" in src
    assert "if _scripts_common.ERROR_COUNT:" in src
    assert "refusing successful exit" in src
    assert "sys.exit(1)" in src
    final = src.index('log("DONE", "Pipeline complete")')
    assert src.index("if _scripts_common.ERROR_COUNT:") < final
