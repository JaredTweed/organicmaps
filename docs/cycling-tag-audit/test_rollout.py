"""Tests for the single-file cycling stack rollout launcher.

The launcher's local checks run against the real research checkout; GitHub and
git-push side effects are mocked, so these tests never touch a repository.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("rollout.sh")
DOCS = SCRIPT.parent

GH_MOCK = r'''#!/usr/bin/env python3
import json, os, sys
from urllib.parse import unquote

state = json.load(open(os.environ["MOCK_GH_STATE"]))
args = sys.argv[1:]

def write(marker, payload):
    with open(marker, "a") as out:
        out.write(json.dumps(payload) + "\n")

def branch(repo, ref):
    return state.get("branches", {}).get(f"{repo}|{unquote(ref)}", "")

if args[:2] == ["auth", "status"]:
    sys.exit(0)

if args[:2] == ["pr", "create"]:
    repo = args[args.index("--repo") + 1]
    base = args[args.index("--base") + 1]
    head = args[args.index("--head") + 1]
    title = args[args.index("--title") + 1]
    payload = {"repo": repo, "base": base, "head": head, "title": title,
               "draft": "--draft" in args}
    write(os.environ["MOCK_GH_MARKER"], payload)
    print(f"https://github.com/{repo}/pull/{state.get('next_pr', 900)}")
    sys.exit(0)

if args[:2] == ["pr", "edit"]:
    write(os.environ["MOCK_GH_MARKER"], {"edit": args})
    sys.exit(0)

if args[:2] == ["pr", "close"]:
    write(os.environ["MOCK_GH_MARKER"], {"close": args})
    sys.exit(0)

if args[:2] == ["pr", "view"]:
    number = args[2]
    print(f"https://github.com/x/y/pull/{number}")
    sys.exit(0)

if args and args[0] == "api":
    url = args[1]
    jq = args[args.index("--jq") + 1] if "--jq" in args else ""
    if "/branches/" in url:
        repo, ref = url.split("repos/", 1)[1].split("/branches/", 1)
        print(branch(repo, ref.split("?")[0]))
        sys.exit(0)
    if "/pulls?" in url:
        repo = url.split("repos/", 1)[1].split("/pulls?", 1)[0]
        query = dict(part.split("=", 1) for part in url.split("?", 1)[1].split("&"))
        key = f'{repo}|{unquote(query["head"])}|{unquote(query["base"])}'
        number = state.get("prs", {}).get(key)
        print(number if number else "")
        sys.exit(0)
    if "/pulls/" in url:
        number = url.rstrip("/").split("/")[-1]
        pr = state.get("pr", {}).get(number, {})
        field = {".state": "state", ".draft": "draft", ".base.ref": "base",
                 ".head.sha": "headSha"}.get(jq)
        value = pr.get(field, "")
        if field == "draft":
            print("true" if value else "false")
        else:
            print(value)
        sys.exit(0)

sys.exit("unexpected gh invocation: " + repr(args))
'''

GIT_MOCK = r'''#!/usr/bin/env bash
if [[ "$1" == "push" || "$1" == "fetch" ]]; then
  printf '%s\n' "$*" >> "$MOCK_GIT_MARKER"
  exit 0
fi
exec "$REAL_GIT" "$@"
'''


def read_pins():
    text = SCRIPT.read_text()
    pins = {}
    for name, value in re.findall(r"^readonly ([A-Z_]+)=([^\n]+)$", text, re.M):
        pins[name] = value.strip("'")
    return pins


PINS = read_pins()


def branch_map(overrides=None):
    data = {
        f"JaredTweed/organicmaps|{PINS['SELECTOR_BRANCH']}": PINS["SELECTOR_HEAD"],
        f"JaredTweed/organicmaps|{PINS['TAG_DATA_BRANCH']}": PINS["TAG_DATA_HEAD"],
        f"JaredTweed/organicmaps|{PINS['DASH_BRANCH']}": PINS["DASH_HEAD"],
        f"JaredTweed/organicmaps|{PINS['STYLE_BASE_BRANCH']}": PINS["STYLE_BASE_HEAD"],
        f"JaredTweed/organicmaps|{PINS['STYLE_BRANCH']}": PINS["STYLE_HEAD"],
        "organicmaps/organicmaps|master": "1b9a011b4272d69b002ee78b9d30d2483e50688d",
        "organicmaps/organicmaps|ab/cycling-style": PINS["STYLE_BASE_HEAD"],
    }
    data.update(overrides or {})
    return data


class RolloutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

        gh = self.tmp / "gh"
        gh.write_text(GH_MOCK)
        gh.chmod(0o755)
        git = self.tmp / "git"
        git.write_text(GIT_MOCK)
        git.chmod(0o755)

        self.state_path = self.tmp / "state.tsv"
        self.gh_state = self.tmp / "gh.json"
        self.gh_marker = self.tmp / "gh-calls.jsonl"
        self.git_marker = self.tmp / "git-calls"

    def run_script(self, args=("--check",), env=None, branches=None, prs=None,
                   pr_state=None, next_pr=900):
        state = {
            "branches": branch_map(branches),
            "prs": prs or {},
            "pr": pr_state or {},
            "next_pr": next_pr,
        }
        self.gh_state.write_text(json.dumps(state))
        full_env = dict(
            os.environ,
            PATH=f"{self.tmp}{os.pathsep}{os.environ['PATH']}",
            GH=str(self.tmp / "gh"),
            GIT=str(self.tmp / "git"),
            REAL_GIT=shutil.which("git"),
            MOCK_GH_STATE=str(self.gh_state),
            MOCK_GH_MARKER=str(self.gh_marker),
            MOCK_GIT_MARKER=str(self.git_marker),
            ROLLOUT_STATE_FILE=str(self.state_path),
            XDG_STATE_HOME=str(self.tmp / "xdg"),
        )
        full_env.update(env or {})
        result = subprocess.run(
            [str(SCRIPT), *args], cwd=REPO, env=full_env,
            text=True, capture_output=True,
        )
        return result

    def gh_calls(self):
        if not self.gh_marker.exists():
            return []
        return [json.loads(line) for line in self.gh_marker.read_text().splitlines()]

    def git_calls(self):
        return self.git_marker.read_text().splitlines() if self.git_marker.exists() else []

    # read-only behaviour -------------------------------------------------

    def test_check_is_read_only(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual(self.git_calls(), ["fetch --quiet upstream master"])

    def test_plan_lists_the_whole_stack_without_network(self):
        result = self.run_script(["--plan"])
        self.assertEqual(result.returncode, 0, result.stderr)
        for step in ("selector", "tag-data", "dash", "style", "style-base"):
            self.assertIn(step, result.stdout)
        self.assertEqual(self.gh_calls(), [])

    def test_dump_bodies_matches_checked_in_docs(self):
        out = self.tmp / "bodies"
        result = self.run_script(["--dump-bodies", str(out)])
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("selector-pr-body.md", "tag-data-pr-body.md",
                     "dash-pr-body.md", "style-pr-body.md"):
            self.assertEqual((out / name).read_text(), (DOCS / name).read_text(), name)

    # publish gates -------------------------------------------------------

    def test_publish_requires_explicit_opt_in(self):
        result = self.run_script(["--publish"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual(self.git_calls(), [])

    def test_publish_refuses_drifted_fork_branch(self):
        result = self.run_script(
            ["--publish"], {"PUBLISH_CYCLING_STACK": "YES"},
            branches={f"JaredTweed/organicmaps|{PINS['DASH_BRANCH']}": "0" * 40},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual([c for c in self.git_calls() if c.startswith("push")], [])

    def test_publish_refuses_moved_upstream_style_branch(self):
        result = self.run_script(
            ["--publish"], {"PUBLISH_CYCLING_STACK": "YES"},
            branches={"organicmaps/organicmaps|ab/cycling-style": "1" * 40},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.gh_calls(), [])

    def test_publish_refuses_forbidden_pr(self):
        result = self.run_script(
            ["--publish"], {"PUBLISH_CYCLING_STACK": "YES"},
            prs={f"organicmaps/organicmaps|JaredTweed:{PINS['SELECTOR_BRANCH']}|master": 12692},
            pr_state={"12692": {"state": "open", "draft": True,
                                "base": "master", "headSha": PINS["SELECTOR_HEAD"]}},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("12692", result.stderr)
        self.assertEqual(self.gh_calls(), [])

    def test_publish_refuses_non_draft_existing_pr(self):
        result = self.run_script(
            ["--publish"], {"PUBLISH_CYCLING_STACK": "YES"},
            prs={f"JaredTweed/organicmaps|{PINS['TAG_DATA_BRANCH']}|{PINS['SELECTOR_BRANCH']}": 12},
            pr_state={"12": {"state": "open", "draft": False,
                             "base": PINS["SELECTOR_BRANCH"], "headSha": PINS["TAG_DATA_HEAD"]}},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no longer a draft", result.stderr)
        self.assertEqual(self.gh_calls(), [])

    # publish happy path --------------------------------------------------

    def test_publish_creates_four_drafts_in_stack_order(self):
        result = self.run_script(["--publish"], {"PUBLISH_CYCLING_STACK": "YES"})
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.gh_calls()
        self.assertEqual(len(calls), 4, calls)
        expected = [
            ("organicmaps/organicmaps", "master", f"JaredTweed:{PINS['SELECTOR_BRANCH']}"),
            ("JaredTweed/organicmaps", PINS["SELECTOR_BRANCH"], PINS["TAG_DATA_BRANCH"]),
            ("JaredTweed/organicmaps", PINS["TAG_DATA_BRANCH"], PINS["DASH_BRANCH"]),
            ("JaredTweed/organicmaps", PINS["STYLE_BASE_BRANCH"], PINS["STYLE_BRANCH"]),
        ]
        for call, (repo, base, head) in zip(calls, expected):
            self.assertEqual(call["repo"], repo)
            self.assertEqual(call["base"], base)
            self.assertEqual(call["head"], head)
            self.assertTrue(call["draft"])
        state = self.state_path.read_text()
        self.assertEqual(len(state.strip().splitlines()), 4)
        self.assertNotIn("12692", state)

    def test_publish_pushes_only_missing_branches(self):
        missing = {f"JaredTweed/organicmaps|{PINS['STYLE_BASE_BRANCH']}": "",
                   f"JaredTweed/organicmaps|{PINS['STYLE_BRANCH']}": ""}
        result = self.run_script(["--publish"], {"PUBLISH_CYCLING_STACK": "YES"}, branches=missing)
        self.assertEqual(result.returncode, 0, result.stderr)
        pushes = [call for call in self.git_calls() if call.startswith("push")]
        self.assertEqual(len(pushes), 2, pushes)
        self.assertTrue(any(PINS["STYLE_BASE_BRANCH"] in push for push in pushes))
        self.assertTrue(any(PINS["STYLE_BRANCH"] in push for push in pushes))

    def test_publish_is_idempotent_and_never_edits_by_default(self):
        prs = {
            f"organicmaps/organicmaps|JaredTweed:{PINS['SELECTOR_BRANCH']}|master": 101,
            f"JaredTweed/organicmaps|{PINS['TAG_DATA_BRANCH']}|{PINS['SELECTOR_BRANCH']}": 102,
            f"JaredTweed/organicmaps|{PINS['DASH_BRANCH']}|{PINS['TAG_DATA_BRANCH']}": 103,
            f"JaredTweed/organicmaps|{PINS['STYLE_BRANCH']}|{PINS['STYLE_BASE_BRANCH']}": 104,
        }
        pr_state = {
            "101": {"state": "open", "draft": True, "base": "master", "headSha": PINS["SELECTOR_HEAD"]},
            "102": {"state": "open", "draft": True, "base": PINS["SELECTOR_BRANCH"], "headSha": PINS["TAG_DATA_HEAD"]},
            "103": {"state": "open", "draft": True, "base": PINS["TAG_DATA_BRANCH"], "headSha": PINS["DASH_HEAD"]},
            "104": {"state": "open", "draft": True, "base": PINS["STYLE_BASE_BRANCH"], "headSha": PINS["STYLE_HEAD"]},
        }
        result = self.run_script(["--publish"], {"PUBLISH_CYCLING_STACK": "YES"},
                                 prs=prs, pr_state=pr_state)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual(len(self.state_path.read_text().strip().splitlines()), 4)

    def test_publish_updates_body_only_when_explicitly_allowed(self):
        prs = {f"JaredTweed/organicmaps|{PINS['DASH_BRANCH']}|{PINS['TAG_DATA_BRANCH']}": 103}
        pr_state = {"103": {"state": "open", "draft": True,
                            "base": PINS["TAG_DATA_BRANCH"], "headSha": PINS["DASH_HEAD"]}}
        result = self.run_script(
            ["--publish"],
            {"PUBLISH_CYCLING_STACK": "YES", "UPDATE_PR_BODIES": "YES"},
            prs=prs, pr_state=pr_state,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        edits = [call for call in self.gh_calls() if "edit" in call]
        self.assertEqual(len(edits), 1, edits)
        self.assertEqual(edits[0]["edit"][2], "103")

    # verify / rollback ---------------------------------------------------

    def test_verify_reports_missing_pr(self):
        result = self.run_script(["--verify"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no PR exists", result.stderr)

    def test_rollback_requires_opt_in(self):
        result = self.run_script(["--rollback"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.gh_calls(), [])

    def test_rollback_closes_only_recorded_drafts(self):
        self.state_path.write_text(
            "selector\torganicmaps/organicmaps\t101\thttps://x/101\n"
            "tag-data\tJaredTweed/organicmaps\tnew\thttps://x/new\n"
        )
        result = self.run_script(
            ["--rollback"], {"ROLLBACK_CYCLING_STACK": "YES"},
            pr_state={"101": {"state": "open", "draft": True,
                              "base": "master", "headSha": PINS["SELECTOR_HEAD"]}},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        closes = [call for call in self.gh_calls() if "close" in call]
        self.assertEqual(len(closes), 1, closes)
        self.assertEqual(closes[0]["close"][2], "101")
        self.assertFalse(self.state_path.exists())

    def test_rollback_refuses_non_draft(self):
        self.state_path.write_text("selector\torganicmaps/organicmaps\t101\thttps://x/101\n")
        result = self.run_script(
            ["--rollback"], {"ROLLBACK_CYCLING_STACK": "YES"},
            pr_state={"101": {"state": "open", "draft": False,
                              "base": "master", "headSha": PINS["SELECTOR_HEAD"]}},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.gh_calls(), [])


if __name__ == "__main__":
    unittest.main()
