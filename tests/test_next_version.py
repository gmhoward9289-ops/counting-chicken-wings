"""Deciding the release number at merge time.

The rule these enforce is `docs/VERSIONING.md`'s: pick the number last. It was
written as an instruction to humans and lost the moment two sessions merged
minutes apart -- v1.5.0 and v1.6.0 were both taken out from under a branch in
review on 2026-07-30, and v1.9.1 and v1.10.0 were both skipped entirely on
2026-07-31 because the release job read a `pyproject.toml` that had already
moved on. Executing the rule is the only version of it that holds.
"""

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "next_version", ROOT / "tools" / "next_version.py")
nv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nv)


CHANGELOG = """# Changelog

## Unreleased

### Something shipped

Body.

## v1.11.0 — 2026-07-31

Older.
"""


# ---------------------------------------------------------------------------
# Is there anything to release?
# ---------------------------------------------------------------------------


def test_an_unreleased_section_with_content_is_a_release():
    assert "Something shipped" in nv.unreleased(CHANGELOG)


def test_the_section_stops_at_the_next_heading():
    assert "Older" not in nv.unreleased(CHANGELOG)


def test_no_unreleased_section_means_nothing_to_release():
    assert nv.unreleased("# Changelog\n\n## v1.11.0 — 2026-07-31\n\nx\n") is None


def test_an_empty_unreleased_section_is_not_a_release():
    """A merge that left the heading behind has not written a changelog."""
    assert nv.unreleased("# Changelog\n\n## Unreleased\n\n## v1.1.0 — x\n\ny\n") is None


# ---------------------------------------------------------------------------
# MAJOR.MINOR.MINOR, which is not SemVer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version,level,want", [
    ("1.11.0", "third",  "1.11.1"),
    ("1.11.0", "second", "1.12.0"),
    ("1.11.0", "major",  "2.0.0"),
    ("1.9.1",  "third",  "1.9.2"),
    ("1.9.1",  "second", "1.10.0"),
])
def test_bump(version, level, want):
    assert nv.bump(version, want and level) == want


def test_a_second_digit_bump_resets_the_third():
    """1.9.1 -> 1.10.0, not 1.10.1."""
    assert nv.bump("1.9.1", "second") == "1.10.0"


def test_a_major_bump_resets_both():
    assert nv.bump("3.4.5", "major") == "4.0.0"


def test_bumping_nothing_is_an_error_rather_than_a_silent_no_op():
    with pytest.raises(ValueError):
        nv.bump("1.0.0", "none")


def test_the_third_digit_is_not_treated_as_a_patch_level():
    """Guards the scheme itself.

    The old rule called this a patch and took the project 1.0.0 -> 1.7.0 in
    two days. If someone 'fixes' bump() into SemVer, second-digit moves stop
    resetting the third and this fails.
    """
    assert nv.bump("1.7.3", "second") == "1.8.0"


# ---------------------------------------------------------------------------
# Writing the number in
# ---------------------------------------------------------------------------


def test_rewrite_gives_the_section_its_number_and_date():
    out = nv.rewrite("1.12.0", CHANGELOG, "2026-08-01")
    assert "## v1.12.0 — 2026-08-01" in out
    assert "## Unreleased" not in out


def test_rewrite_leaves_older_releases_alone():
    out = nv.rewrite("1.12.0", CHANGELOG, "2026-08-01")
    assert "## v1.11.0 — 2026-07-31" in out


def test_rewrite_touches_only_the_first_heading():
    """Two Unreleased headings would mean a bad merge; do not paper over it."""
    doubled = CHANGELOG + "\n## Unreleased\n\nstray\n"
    assert nv.rewrite("1.12.0", doubled, "2026-08-01").count("## Unreleased") == 1


# ---------------------------------------------------------------------------
# The real file
# ---------------------------------------------------------------------------


FAILING_JSON = """{
 "base": "v1.11.0",
 "required": "second",
 "actual": "none",
 "ok": false,
 "reasons": ["new domain(s): livestock"]
}

FAIL: version bump is none, but this diff requires second
"""


def test_a_failing_verdict_still_parses():
    """release_check prints a human line AFTER the object when it fails.

    That makes the stream two documents, and `json.loads` raises "Extra
    data". This is the normal path, not a corner case: under version-at-merge
    a branch never bumps pyproject, so `actual` is always "none" and every
    verdict reads as FAIL. Parsing only the leading object is what lets the
    number be computed at all.
    """
    level, reasons = nv.parse_verdict(FAILING_JSON)
    assert level == "second"
    assert reasons == ["new domain(s): livestock"]


def test_a_passing_verdict_parses_too():
    level, _ = nv.parse_verdict('{"required": "third", "reasons": []}\n')
    assert level == "third"


def test_a_missing_required_field_reads_as_none_rather_than_crashing():
    assert nv.parse_verdict('{"base": "v1.0.0"}')[0] == "none"


def test_the_levels_are_ordered_weakest_first():
    """`none` must sort below `third`; the floor rule depends on it."""
    assert nv.LEVELS.index("none") < nv.LEVELS.index("third") \
        < nv.LEVELS.index("second") < nv.LEVELS.index("major")


def test_the_base_tag_is_looked_up_among_version_tags_only(monkeypatch):
    """A marker tag must never become the base the next number counts from.

    `git describe --tags` takes the newest tag of ANY shape, so a
    `snapshot/...` or `checkpoint/...` pushed after the last release would be
    picked up here and the bump measured from a commit nobody released --
    silently, since `describe` reports no ambiguity. docs/VERSIONING.md
    ("Tags that are not releases") says every call site passes the filter;
    this one is the third and was added without it.
    """
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="v1.11.0\n", stderr="")

    monkeypatch.setattr(nv.subprocess, "run", fake_run)
    assert nv.latest_tag() == "v1.11.0"
    assert "--match" in seen["argv"]
    assert "v[0-9]*" in seen["argv"]
    # Excludes prereleases too, for the same reason: `v1.12.0-rc1` sorts
    # after v1.11.0 and is not a released number.
    assert "--exclude" in seen["argv"]
    assert "*-*" in seen["argv"]


def test_no_tag_at_all_reads_as_none_rather_than_empty_string(monkeypatch):
    """`--match` narrowing the set to nothing must look like "no tag"."""
    monkeypatch.setattr(nv.subprocess, "run",
                        lambda argv, **kw: subprocess.CompletedProcess(
                            argv, 128, stdout="", stderr="fatal: No names found"))
    assert nv.latest_tag() is None


def test_every_version_in_the_real_changelog_parses_as_three_digits():
    import re
    text = nv.CHANGELOG.read_text(encoding="utf-8")
    for v in re.findall(r"^## v(\S+)", text, re.M):
        assert len(v.split(".")) == 3, f"{v} is not MAJOR.MINOR.MINOR"


# ---------------------------------------------------------------------------
# Branch-side bump levels
#
# `release_check` diffs the corpus and the published answer, so a new view,
# endpoint or CLI flag is invisible to it -- docs/VERSIONING.md has always said
# so. Until this existed nothing could act on it: v1.15.1 shipped an endpoint
# and a database view under a third-digit bump, and MAJOR was unreachable
# entirely, since release_check never returns it.
#
# The declaration is a LEVEL, never a number. That is what makes it safe on a
# repo with eight live sessions: two branches may both declare `second` and
# neither collides, because the number is still resolved at merge.
# ---------------------------------------------------------------------------


def test_a_changeset_without_frontmatter_declares_nothing():
    """The common case. Most branches want the computed floor."""
    level, body = nv.parse_change("### A thing\n\nProse.\n")
    assert level is None
    assert body.startswith("### A thing")


def test_a_changeset_declares_a_level_and_keeps_its_prose():
    level, body = nv.parse_change("---\nbump: second\n---\n### A thing\n\nProse.\n")
    assert level == "second"
    assert body == "### A thing\n\nProse."
    assert "bump" not in body, "frontmatter leaked into the changelog"


@pytest.mark.parametrize("level", ["third", "second", "major"])
def test_every_declarable_level_is_accepted(level):
    assert nv.parse_change(f"---\nbump: {level}\n---\nx\n")[0] == level


def test_a_version_number_is_refused_with_the_reason():
    """The mistake worth its own message: a number is the race, not a shortcut."""
    with pytest.raises(SystemExit) as e:
        nv.parse_change("---\nbump: 1.16.0\n---\nx\n", "b.md")
    msg = str(e.value)
    assert "LEVEL, not a number" in msg
    assert "1.5.0" in msg, "the error does not say why numbers are refused"


def test_none_is_not_declarable():
    """A declaration may raise the floor; it must not be a way to lower it."""
    with pytest.raises(SystemExit):
        nv.parse_change("---\nbump: none\n---\nx\n", "b.md")


def test_a_typo_in_the_key_fails_rather_than_being_ignored():
    """A silently-dropped declaration ships under a number someone corrected."""
    with pytest.raises(SystemExit) as e:
        nv.parse_change("---\nbumps: second\n---\nx\n", "b.md")
    assert "unknown frontmatter key" in str(e.value)


def _changes(*levels):
    return [nv.Change(Path(f"{i}.md"), lv, "body") for i, lv in enumerate(levels)]


def test_the_strongest_declaration_wins():
    """Two branches in one release: the union, not the weaker of the two."""
    assert nv.declared_level(_changes("third", "second"))[0] == "second"
    assert nv.declared_level(_changes("second", "major"))[0] == "major"


def test_undeclared_changesets_are_not_a_declaration():
    assert nv.declared_level(_changes(None, None))[0] is None
    assert nv.declared_level(_changes(None, "third"))[0] == "third"


def test_the_declaration_names_itself_in_the_reasons():
    """`--explain` has to say which file moved the number."""
    _, why = nv.declared_level([nv.Change(Path("mine.md"), "second", "b")])
    assert any("mine.md" in r and "second" in r for r in why)


def test_the_levels_a_branch_may_declare_are_a_subset_of_the_verdicts():
    """DECLARABLE and LEVELS must not drift apart."""
    assert set(nv.DECLARABLE) < set(nv.LEVELS)
    assert "none" not in nv.DECLARABLE
    assert nv.RANK["major"] > nv.RANK["second"] > nv.RANK["third"] > nv.RANK["none"]


# ---------------------------------------------------------------------------
# Assembling the section
# ---------------------------------------------------------------------------


def test_splice_replaces_an_unreleased_section_with_every_body():
    """A release holding both mechanisms is ONE section, not two."""
    out = nv.splice("1.16.0", CHANGELOG, "2026-08-01",
                    ["### Legacy\n\nOld.", "### From a file\n\nNew."])
    assert "## v1.16.0 — 2026-08-01" in out
    assert "## Unreleased" not in out
    assert "### Legacy" in out and "### From a file" in out
    assert out.count("## v1.16.0") == 1
    assert "## v1.11.0 — 2026-07-31" in out, "older releases disturbed"


def test_splice_inserts_a_section_when_there_is_no_unreleased_one():
    """The end state: changesets only, no shared section to rename."""
    text = "# Changelog\n\n## v1.11.0 — 2026-07-31\n\nOlder.\n"
    out = nv.splice("1.16.0", text, "2026-08-01", ["### New\n\nProse."])
    assert out.startswith("# Changelog\n")
    assert out.index("## v1.16.0") < out.index("## v1.11.0"), \
        "the new release must come first"
    assert "### New" in out


def test_splice_keeps_the_order_it_was_given():
    out = nv.splice("1.16.0", CHANGELOG, "2026-08-01", ["### A\n\na", "### B\n\nb"])
    assert out.index("### A") < out.index("### B")


def test_changesets_are_read_in_a_deterministic_order(tmp_path, monkeypatch):
    """Two entries must not swap places between a dry run and the real one."""
    monkeypatch.setattr(nv, "CHANGES", tmp_path)
    for name in ("zeta.md", "alpha.md", "middle.md"):
        (tmp_path / name).write_text(f"### {name}\n", encoding="utf-8")
    assert [c.name for c in nv.read_changes()] == \
        ["alpha.md", "middle.md", "zeta.md"]


def test_the_conventions_own_readme_is_not_an_entry(tmp_path, monkeypatch):
    """`.changes/README.md` documents the mechanism; it is not a release note."""
    monkeypatch.setattr(nv, "CHANGES", tmp_path)
    (tmp_path / "README.md").write_text("# how to write one\n", encoding="utf-8")
    (tmp_path / "real.md").write_text("### Real\n", encoding="utf-8")
    assert [c.name for c in nv.read_changes()] == ["real.md"]


def test_no_changes_directory_is_not_an_error(tmp_path, monkeypatch):
    """The overlap has to survive a repo that has not adopted it yet."""
    monkeypatch.setattr(nv, "CHANGES", tmp_path / "nope")
    assert nv.read_changes() == []


# ---------------------------------------------------------------------------
# The real tree
# ---------------------------------------------------------------------------


def test_every_changeset_in_this_repo_parses():
    """A bad declaration must fail on its own branch, not mid-release.

    This is the CI gate: `pytest` runs on every PR, so a typo in `bump:` is
    caught by the branch that wrote it rather than three merges later.
    """
    for c in nv.read_changes():
        assert c.body.strip(), f"{c.name} declares a bump but says nothing"
        assert c.level is None or c.level in nv.DECLARABLE


# ---------------------------------------------------------------------------
# Raise only, never lower
# ---------------------------------------------------------------------------


def test_a_declaration_raises_the_computed_floor():
    """The case this exists for: an endpoint the corpus diff cannot see."""
    level, reasons, warn = nv.resolve_level(
        "third", ["corpus identical"], _changes("second"))
    assert level == "second"
    assert warn is None
    assert any("second" in r for r in reasons)


def test_a_declaration_cannot_lower_the_computed_floor():
    """Someone who writes `third` on a branch that added a species is wrong.

    release_check saw a real change to the corpus; a declaration speaks only
    for what it is blind to.
    """
    level, reasons, warn = nv.resolve_level(
        "second", ["new species(s): silkworm"], _changes("third"))
    assert level == "second", "a branch talked the release down"
    assert warn and "requires second" in warn
    assert any("new species" in r for r in reasons), "the real reason was lost"


def test_major_is_reachable_only_by_declaring_it():
    """release_check never returns major, so nothing else can produce one.

    The MAJOR criterion is the MEANING of a published figure changing rather
    than its value, which no diff can detect -- so before this, a 2.0.0 could
    not be released at all except by hand-editing a number onto a branch,
    which the whole design forbids.
    """
    assert nv.resolve_level("third", [], _changes("major"))[0] == "major"
    assert nv.bump("1.15.1", "major") == "2.0.0"


def test_no_declaration_leaves_the_verdict_exactly_as_it_was():
    """The regression guard: most releases must behave as they did before."""
    reasons = ["rows changed, no new kind: fact 56->57"]
    assert nv.resolve_level("third", reasons, _changes(None, None)) == \
        ("third", reasons, None)
    assert nv.resolve_level("third", reasons, []) == ("third", reasons, None)


def test_agreeing_with_the_floor_is_not_a_warning():
    level, _, warn = nv.resolve_level("second", [], _changes("second"))
    assert level == "second" and warn is None


# ---------------------------------------------------------------------------
# --apply, which is the destructive half
# ---------------------------------------------------------------------------


@pytest.fixture
def applied(tmp_path, monkeypatch):
    """Run the real --apply against a throwaway tree.

    Everything but `release_check` and the tag lookup is exercised, because
    those two shell out to git and the corpus; what matters here is what gets
    written and what gets deleted.
    """
    changes = tmp_path / ".changes"
    changes.mkdir()
    (changes / "README.md").write_text("# the convention\n", encoding="utf-8")
    (changes / "a-thing.md").write_text(
        "---\nbump: second\n---\n### A thing\n\nProse about it.\n", encoding="utf-8")
    (changes / "b-thing.md").write_text("### B thing\n\nMore prose.\n", encoding="utf-8")

    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "1.15.1"\n', encoding="utf-8")

    monkeypatch.setattr(nv, "CHANGES", changes)
    monkeypatch.setattr(nv, "CHANGELOG", changelog)
    monkeypatch.setattr(nv, "PYPROJECT", pyproject)
    monkeypatch.setattr(nv, "latest_tag", lambda: "v1.15.1")
    monkeypatch.setattr(nv, "required_level",
                        lambda base: ("third", ["corpus identical"]))
    monkeypatch.setattr("sys.argv", ["next_version.py", "--apply"])
    assert nv.main() == 0
    return changes, changelog, pyproject


def test_apply_takes_the_declared_level_not_the_computed_one(applied):
    _, changelog, pyproject = applied
    assert 'version = "1.16.0"' in pyproject.read_text(encoding="utf-8")
    assert "## v1.16.0" in changelog.read_text(encoding="utf-8")


def test_apply_merges_every_body_into_one_section(applied):
    _, changelog, _ = applied
    text = changelog.read_text(encoding="utf-8")
    assert text.count("## v1.16.0") == 1
    for wanted in ("### Something shipped", "### A thing", "### B thing"):
        assert wanted in text, f"{wanted} was dropped"
    assert "## Unreleased" not in text
    assert "bump: second" not in text, "frontmatter reached the changelog"


def test_apply_consumes_the_changesets(applied):
    """They have been merged into the changelog; leaving them re-releases them."""
    changes, _, _ = applied
    assert not list(changes.glob("*.md")) or \
        [p.name for p in changes.glob("*.md")] == ["README.md"]
    assert (changes / "README.md").exists(), "the convention's docs were eaten"


def test_apply_leaves_older_releases_alone(applied):
    _, changelog, _ = applied
    assert "## v1.11.0 — 2026-07-31" in changelog.read_text(encoding="utf-8")


def test_apply_stages_the_deletions_it_made(tmp_path, monkeypatch):
    """A deletion has to be committed or it did not happen.

    The release commit stages explicit pathspecs so a stray file cannot be
    swept into a commit nobody reviews. If the consumed changesets are not
    among them the notes ship, the files stay on master, and the NEXT release
    publishes every one of them a second time. Staging them here means the
    workflow cannot drop that path in a later edit and quietly reintroduce it.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    changes = tmp_path / ".changes"
    changes.mkdir()
    entry = changes / "gone.md"
    entry.write_text("### Gone\n\nProse.\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "seed"], cwd=tmp_path, check=True)

    monkeypatch.setattr(nv, "ROOT", tmp_path)
    monkeypatch.setattr(nv, "CHANGES", changes)
    entry.unlink()
    nv.stage_consumed([nv.Change(entry, None, "body")])

    staged = subprocess.run(["git", "diff", "--cached", "--name-status"],
                            cwd=tmp_path, capture_output=True, text=True).stdout
    assert staged.startswith("D\t.changes/gone.md"), \
        f"deletion not staged: {staged!r}"


def test_staging_outside_a_repository_is_not_fatal(tmp_path, monkeypatch):
    """--apply runs on developer machines too; the files are gone regardless."""
    monkeypatch.setattr(nv, "ROOT", tmp_path)
    nv.stage_consumed([nv.Change(tmp_path / "nope.md", None, "b")])
