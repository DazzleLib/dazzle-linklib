"""Tests for the injectable target resolver (resolve_target).

Covers AC-3: ``resolve_target`` returns the first locator an injected
``ReachabilityResolver`` judges reachable, walking the record's locator order.
"""

from dazzle_linklib import (
    DazzleLinkData,
    ReachabilityResolver,
    default_reachability,
    resolve_target,
)


class FakeReachability:
    """Test double: reachable iff the value is in an allow-set. No I/O."""

    def __init__(self, reachable):
        self.reachable = set(reachable)
        self.seen = []

    def is_reachable(self, value):
        self.seen.append(value)
        return value in self.reachable


def test_fake_is_structural_protocol_instance():
    # Structural: a plain class with is_reachable satisfies the Protocol with
    # no base class and no stack import.
    assert isinstance(FakeReachability([]), ReachabilityResolver)


def test_resolve_returns_first_reachable():
    rec = DazzleLinkData()
    rec.add_locator("url", "https://a.example/x")
    rec.add_locator("ipfs", "QmGood")
    rec.add_locator("url", "https://b.example/y")
    checker = FakeReachability(["QmGood", "https://b.example/y"])

    chosen = resolve_target(rec, reachability=checker)
    assert chosen == {"kind": "ipfs", "value": "QmGood"}
    # It stopped at the first reachable candidate (didn't probe the later url).
    assert checker.seen == ["https://a.example/x", "QmGood"]


def test_resolve_prefers_locator_order():
    # Legacy path aliases come first in get_locators(); original_path -> 'path'.
    rec = DazzleLinkData()
    rec.data["link"]["target_representations"] = {"original_path": "/abs/first"}
    rec.add_locator("url", "https://later.example")
    checker = FakeReachability(["/abs/first", "https://later.example"])

    chosen = resolve_target(rec, reachability=checker)
    assert chosen == {"kind": "path", "value": "/abs/first"}


def test_resolve_none_when_nothing_reachable():
    rec = DazzleLinkData()
    rec.add_locator("ipfs", "QmNope")
    assert resolve_target(rec, reachability=FakeReachability([])) is None


def test_resolve_empty_record_is_none():
    assert resolve_target(DazzleLinkData(), reachability=FakeReachability([])) is None


def test_resolve_basic_record_with_only_target_path(tmp_path):
    # A record with target_path set but no explicit target_representations (the
    # common shape, e.g. a tool record with target_representations == {}) must
    # still resolve -- target_path is always seeded as the first 'path' locator.
    real = tmp_path / "exists.txt"
    real.write_text("hi", encoding="utf-8")
    rec = DazzleLinkData()
    rec.set_target_path(str(real))
    # target_representations stays the empty dict the constructor created.
    assert rec.get_target_representations() == {}

    chosen = resolve_target(rec)  # filesystem default
    assert chosen == {"kind": "path", "value": str(real)}


def test_get_locators_seeds_target_path_once(tmp_path):
    # target_path appears exactly once even when also present in reps.
    rec = DazzleLinkData()
    rec.set_target_path("/abs/p")
    rec.data["link"]["target_representations"] = {"original_path": "/abs/p"}
    paths = [loc for loc in rec.get_locators() if loc == {"kind": "path", "value": "/abs/p"}]
    assert len(paths) == 1


def test_default_reachability_uses_filesystem(tmp_path):
    real = tmp_path / "exists.txt"
    real.write_text("hi", encoding="utf-8")
    rec = DazzleLinkData()
    rec.add_locator("path", str(tmp_path / "missing.txt"))
    rec.add_locator("path", str(real))

    chosen = resolve_target(rec)  # no checker -> filesystem default
    assert chosen == {"kind": "path", "value": str(real)}


def test_default_reachability_rejects_non_path_locators():
    checker = default_reachability()
    assert checker.is_reachable("https://example.com/x") is False
    assert checker.is_reachable("") is False
