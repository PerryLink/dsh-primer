#!/usr/bin/env node
// Freshness probe for the tag-pinned official-docs mirror (no checkout required).
//
// Why this exists, next to `check-docs-drift.ps1`: that script compares the
// upstream *branch tip* against the pinned commit, which is the right question
// only while the mirror tracks master. Since 0.4.6 the mirror is pinned to a
// **release tag** (`references/official-docs/SNAPSHOT.md` -> `Source ref`), so a
// branch-tip comparison is guaranteed red even with nothing to do: master is
// always ahead of the tag by construction.
//
// The right question for a tag pin is "is there a newer release tag than the one
// we mirrored?". This script asks it by version-sorting the remote `dsh-v*` tags
// and comparing the newest one with the pinned ref and commit. It never edits the
// mirror; drift is only reported.
//
// Usage:
//   node scripts/check-docs-drift.mjs [--repo <url>] [--snapshot <path>]
//                                     [--fail-on-drift] [--json]
// Exit codes: 0 = FRESH or report produced, 1 = DRIFT (with --fail-on-drift),
//             2 = probe could not run (snapshot/parse/fetch failure).
// In CI (when $GITHUB_OUTPUT is set) it appends `drift=yes|no|error`.

import { execFileSync } from 'node:child_process'
import { readFileSync, existsSync, appendFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const argv = process.argv.slice(2)
const flag = (name, fallback) => {
  const i = argv.indexOf(name)
  return i >= 0 ? (argv[i + 1] ?? true) : fallback
}
const asJson = argv.includes('--json')
const failOnDrift = argv.includes('--fail-on-drift')
const repo = flag('--repo', 'https://github.com/deepseek-ai/deepseek-harness.git')
const snapshotPath = join(root, flag('--snapshot', 'references/official-docs/SNAPSHOT.md'))

const emit = (driftState) => {
  if (process.env.GITHUB_OUTPUT) {
    appendFileSync(process.env.GITHUB_OUTPUT, `drift=${driftState}\n`)
  }
}

const fail2 = (message) => {
  if (asJson) console.log(JSON.stringify({ state: 'error', message }))
  else console.log(`ERROR: ${message}`)
  emit('error')
  process.exit(2)
}

if (!existsSync(snapshotPath)) fail2(`snapshot not found: ${snapshotPath}`)
const snapshot = readFileSync(snapshotPath, 'utf8')
const pinnedCommit = /^\|\s*Source commit\s*\|\s*`([0-9a-f]{40})`\s*\|/m.exec(snapshot)?.[1]
const pinnedRef = /^\|\s*Source ref\s*\|\s*`([^`]+)`\s*\|/m.exec(snapshot)?.[1]
if (!pinnedCommit) fail2(`cannot parse the pinned "Source commit" from ${snapshotPath}`)
if (!pinnedRef) fail2(`cannot parse the pinned "Source ref" from ${snapshotPath}`)

let result
if (/^dsh-v/.test(pinnedRef)) {
  // Tag pin: the newest release tag is the freshness authority.
  let newest
  try {
    const out = execFileSync('git', ['ls-remote', '--tags', '--refs', '--sort=-v:refname', repo, 'refs/tags/dsh-v*'], {
      encoding: 'utf8',
      timeout: 60_000,
    })
    newest = out
      .split('\n')
      .map((line) => /^([0-9a-f]{40})\trefs\/tags\/(.+)$/.exec(line))
      .filter(Boolean)
      .map((m) => ({ sha: m[1], tag: m[2] }))[0]
  } catch (error) {
    fail2(`cannot reach upstream ${repo}: ${error.message.split('\n')[0]}`)
  }
  if (!newest) fail2(`no dsh-v* tags found at ${repo}`)
  const fresh = newest.tag === pinnedRef && newest.sha === pinnedCommit
  result = {
    state: fresh ? 'fresh' : 'drift',
    mode: 'tag',
    pinnedRef,
    pinnedCommit,
    upstreamRef: newest.tag,
    upstreamCommit: newest.sha,
  }
  if (!fresh && newest.tag === pinnedRef) {
    result.message = `the pinned tag ${pinnedRef} now points to ${newest.sha}, not the mirrored ${pinnedCommit}`
  }
} else {
  // Legacy branch pin (e.g. origin/master): compare the branch tip.
  const branch = pinnedRef.replace(/^origin\//, '')
  let tip
  try {
    const out = execFileSync('git', ['ls-remote', repo, `refs/heads/${branch}`], { encoding: 'utf8', timeout: 60_000 })
    tip = /^([0-9a-f]{40})\t/.exec(out)?.[1]
  } catch (error) {
    fail2(`cannot reach upstream ${repo}: ${error.message.split('\n')[0]}`)
  }
  if (!tip) fail2(`cannot resolve ${branch} at ${repo}`)
  const fresh = tip === pinnedCommit
  result = { state: fresh ? 'fresh' : 'drift', mode: 'branch', pinnedRef, pinnedCommit, upstreamRef: branch, upstreamCommit: tip }
}

if (result.state === 'fresh') {
  if (asJson) console.log(JSON.stringify(result))
  else {
    console.log(`pinned (SNAPSHOT.md): ${result.pinnedRef} @ ${result.pinnedCommit}`)
    console.log('FRESH: references/official-docs is pinned to the newest official release tag')
  }
  emit('no')
  process.exit(0)
}

if (asJson) console.log(JSON.stringify(result))
else {
  console.log(`pinned (SNAPSHOT.md): ${result.pinnedRef} @ ${result.pinnedCommit}`)
  console.log(`upstream:             ${result.upstreamRef} @ ${result.upstreamCommit}`)
  console.log(`DRIFT: ${result.message ?? 'a newer official release tag exists than the one mirrored'}`)
  console.log(`Action: run  pwsh -File scripts/sync-official-docs.ps1 -Ref ${result.upstreamRef}  to refresh the mirror (do not hand-edit it).`)
}
emit('yes')
process.exit(failOnDrift ? 1 : 0)
