# Release Checklist

Run through this checklist before cutting a release. The aim is a clean,
public-safe release with no internal context, no raw material, and a fresh,
reviewable history.

## Quality gates

- [ ] **Tests** pass on a clean checkout.
- [ ] **Lint** passes with no warnings.
- [ ] **Typecheck** passes.
- [ ] **Security scan** passes (dependency audit and static analysis).
- [ ] **Coverage check** passes (if a coverage gate applies).

## Documentation

- [ ] **Docs check** — README and usage reflect the released behavior and
      version.
- [ ] **Changelog updated** — the release entry is present and accurate.
- [ ] Public examples still run and produce the documented output.

## Leak and hygiene scan

- [ ] **Leak scan** — no private names, internal URLs, credentials, tokens, or
      project-specific data anywhere in the release surface.
- [ ] **Fresh-history check** — the release branch has a clean, intentional
      commit history with no stray or experimental commits.
- [ ] **No raw logs or media** — no logs, recordings, audio/video captures,
      screenshots, or zip bundles are committed.
- [ ] **No private context** — nothing from `.private/` (handoffs, decisions,
      private prompts, real fixtures, eval or incident notes) is included.
- [ ] **No internal agent notes** — no agent scratchpads, handoffs, or
      operator-only working notes are committed.
- [ ] **No local machine paths** — no absolute user/home paths or private
      machine names appear in tracked files.
- [ ] **No secret-like placeholders** — no values that look like real keys or
      tokens; placeholders are obviously fake.
- [ ] **No old branch history** — no leftover content carried over from
      abandoned or internal branches.
- [ ] **No internal artifacts** — no generated debug outputs, internal tooling
      config, or operator-only files.

## Final confirmation

- [ ] If anything above is uncertain, it was treated as private and excluded.
- [ ] Version number and release notes are correct and final.
- [ ] A fresh clone of the release builds and runs from scratch.

## PyPI publication and recovery

- [ ] Publish production artifacts by publishing the GitHub Release. The
      release event rebuilds the tag, runs `make release-verify`, and pauses at
      the protected `pypi` environment before Trusted Publishing.
- [ ] If artifact verification passed but the publisher failed before upload,
      fix and review the workflow on `main`, then create a new immutable
      `<release-tag>-pypi-recovery-N` tag from that exact green main commit. Run
      the manual **Publish to PyPI** workflow from the recovery tag and pass the
      existing release tag as its `tag` input. The recovery tag keeps the
      protected environment's `v*` tag rule effective; it is not a package
      version and must not receive a GitHub Release.
- [ ] The recovery path accepts only a strict semver release tag that matches
      `pyproject.toml`, checks out that tag by its qualified `refs/tags/...` ref,
      equals the peeled tag commit, is reachable from `origin/main`, and already
      has a published, non-prerelease GitHub Release. It also proves that the
      numbered recovery tag and loaded workflow come from the same main commit.
- [ ] Never move, delete, or reuse a public release tag to retry publication.
- [ ] After workflow success, verify the version and file digests through the
      PyPI JSON API, then install the exact version from PyPI in a clean
      environment and run the CLI smoke checks.
