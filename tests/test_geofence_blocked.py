"""Blocked-list geofence enforcement.

``--block-countries`` / ``--block-regions`` used to be accepted and then
ignored: the values were substituted into the loader template but the
Geofence class only accepted allow-lists, so an operator who believed a
country was blocked had armed nothing.  The emitted class now enforces
blocks.  These tests exec the real ``GEOFENCE_SOURCE`` (placeholder
renames applied by targeted replaces, the way ``apply_vars`` does) with
the location cache primed, so no network is touched.
"""

from obfuscator.core.sources import GEOFENCE_SOURCE


def _make(allowed_c=(), allowed_r=(), blocked_c=(), blocked_r=(), location=None):
    src = GEOFENCE_SOURCE
    for placeholder, name in (
            ("{GEOFENCE_CLS}", "GEOFENCE"),
            ("{METHOD_GET_LOCATION}", "get_loc"),
            ("{METHOD_CHECK_ALLOWED}", "check"),
            ("{METHOD_GET_LOCATION_KEY}", "loc_key")):
        src = src.replace(placeholder, name)
    ns = {}
    exec(compile(src, "<geofence>", "exec"), ns)
    geo = ns["GEOFENCE"](list(allowed_c), list(allowed_r),
                         list(blocked_c), list(blocked_r))
    geo._location_cache = location
    return geo


def test_blocked_country_blocks():
    geo = _make(blocked_c=["RU"], location={"country": "RU", "region": "X"})
    assert geo.check() is False


def test_blocked_region_blocks():
    geo = _make(blocked_r=["Moscow"], location={"country": "US", "region": "Moscow"})
    assert geo.check() is False


def test_allow_list_still_allows_the_listed_country():
    geo = _make(allowed_c=["US"], location={"country": "US", "region": "CA"})
    assert geo.check() is True


def test_allow_list_still_rejects_unlisted_country():
    geo = _make(allowed_c=["US"], location={"country": "RU", "region": "X"})
    assert geo.check() is False


def test_block_wins_over_allow():
    geo = _make(allowed_c=["US"], blocked_c=["US"],
                location={"country": "US", "region": "CA"})
    assert geo.check() is False


def test_no_lists_allows_any_location():
    geo = _make(location={"country": "RU", "region": "X"})
    assert geo.check() is True


def test_loader_gate_passes_blocked_lists_to_the_class():
    # The instantiation site in LOADER_BODY must actually hand the blocked
    # lists to the class; otherwise the enforcement above never runs in a
    # real artefact.
    from obfuscator.core.sources import LOADER_BODY
    assert "{VAR_GEOFENCE_CLS}({allowed_countries}, {allowed_regions}, " \
           "{blocked_countries}, {blocked_regions})" in LOADER_BODY


def test_expire_gate_reads_the_embedded_date():
    # --expire used to embed the date into VAR_EXP_DATE where nothing read
    # it: an operator setting an expiry armed nothing. The boot sequence
    # now checks it with the sibling-gate pattern.
    from obfuscator.core.sources import LOADER_BODY
    assert "if {VAR_EXP_DATE} and _nixon_時間시간.time() > {VAR_EXP_DATE}:" \
        in LOADER_BODY
    assert '_nx_strict_fail("expired")' in LOADER_BODY


def test_expire_zero_disables_the_gate():
    # {VAR_EXP_DATE} is 0 when no --expire is given; the gate must be a
    # no-op then, not an always-fail.
    from obfuscator.core.sources import LOADER_BODY
    assert "if {VAR_EXP_DATE} and _nixon_時間시간.time()" in LOADER_BODY
