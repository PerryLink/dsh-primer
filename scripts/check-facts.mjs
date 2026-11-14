// Assert that the numbers this project states about itself match reality.
//
// Why this exists: the audits found the same class of defect repeatedly, always
// a number stated in prose that no longer matched the thing it described.
//   * the family roster was written four different ways in four files;
//   * the pitfall list was "30+" in English and "20+" in three translations;
//   * the mirror was described as "215 pages" long after it reached 429;
//   * `unfixed-issues.md` carried four separate arithmetic slips ("4 items ...
//     5 items").
// None of those are content errors — they are drift between a claim and its
// source. `data/facts.json` is the single home for the numbers; this script
// checks the claims a machine can verify.
//
// Usage: node scripts/check-facts.mjs [--json]

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const root = process.cwd()
const asJson = process.argv.includes('--json')
const facts = JSON.parse(readFileSync(join(root, 'data', 'facts.json'), 'utf8'))

const failures = []
const checked = []
const ok = (name, detail) => checked.push(`${name}: ${detail}`)
const bad = (name, detail) => failures.push(`${name}: ${detail}`)

const read = (p) => readFileSync(join(root, p), 'utf8')

/** Count `## ` sections in a document. */
const sections = (text) => text.split(/\r?\n/).filter((l) => /^##\s/.test(l)).length

/** Count top-level bullets inside the H2 section at `ordinal` (0 = preamble). */
function bulletsInSection(text, ordinal) {
  const lines = text.split(/\r?\n/)
  let index = 0
  let inside = false
  let count = 0
  for (const line of lines) {
    if (/^##\s/.test(line)) {
      index++
      inside = index === ordinal
      continue
    }
    if (inside && /^- \S/.test(line)) count++
  }
  return count
}

// ---- 1. README structure claims -------------------------------------------------
// The five READMEs no longer share ENGLISH headings: README.md is the Chinese
// source and README.<lang>.md translate the headings, so a frozen section count
// in data/facts.json is not comparable across files. What must hold — and what
// this checks now — is cross-file equality: every translation carries the same
// H2 count and the same number of entries in the capabilities section (the
// fourth H2 of the family layout: preamble, what-it-is, setup, capabilities).
{
  const files = ['README.md', 'README.en.md', 'README.es.md', 'README.pt.md', 'README.hi.md']
  const texts = files.map((f) => read(f))
  const sectionCounts = texts.map((t) => sections(t))
  const sectionRef = sectionCounts[0]
  const sectionDrift = files.filter((f, i) => sectionCounts[i] !== sectionRef)
  if (sectionDrift.length > 0) bad('README sections', `${sectionDrift.join(', ')} do not carry ${sectionRef} sections like README.md`)
  else ok('README sections', `${sectionRef} in all ${files.length} languages`)

  const capabilityCounts = texts.map((t) => bulletsInSection(t, 3))
  const capabilityRef = capabilityCounts[0]
  const capabilityDrift = files.filter((f, i) => capabilityCounts[i] !== capabilityRef)
  if (capabilityDrift.length > 0) bad('README capabilities entries', `${capabilityDrift.join(', ')} do not carry ${capabilityRef} entries like README.md`)
  else ok('README capabilities entries', `${capabilityRef} in all ${files.length} languages`)
}

// ---- 2. Knowledge-base inventory -------------------------------------------------
{
  const guide = readdirSync(join(root, 'guide')).filter((f) => f.endsWith('.md')).length
  if (guide !== facts.knowledgeBase.guideDocuments) bad('guide/ documents', `${guide} vs ${facts.knowledgeBase.guideDocuments}`)
  else ok('guide/ documents', String(guide))

  const refs = readdirSync(join(root, 'references'))
    .filter((f) => f.endsWith('.md') && statSync(join(root, 'references', f)).isFile()).length
  if (refs !== facts.knowledgeBase.referenceDocuments) bad('references/ documents', `${refs} vs ${facts.knowledgeBase.referenceDocuments}`)
  else ok('references/ documents', String(refs))
}

// ---- 3. Mirror claims ------------------------------------------------------------
{
  const snap = read('references/official-docs/SNAPSHOT.md')
  const commit = /^\|\s*Source commit\s*\|\s*`([0-9a-f]{40})`\s*\|/m.exec(snap)?.[1]
  if (commit !== facts.mirror.pinnedCommit) bad('mirror pinned commit', `${commit} in SNAPSHOT.md vs ${facts.mirror.pinnedCommit} in facts.json`)
  else ok('mirror pinned commit', commit.slice(0, 7))

  // A snapshot pinned to a release tag must say so: the old 'origin/master' ref is what let a
  // master sync commit get labelled as a release tag.
  const ref = /^\|\s*Source ref\s*\|\s*`([^`]+)`\s*\|/m.exec(snap)?.[1]
  if (ref !== facts.mirror.pinnedTag) bad('mirror pinned tag', `${ref} in SNAPSHOT.md vs ${facts.mirror.pinnedTag} in facts.json`)
  else ok('mirror pinned tag', ref)

  // Count the mirrored markdown pages and the zh pairs independently.
  let md = 0
  let zh = 0
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, e.name)
      if (e.isDirectory()) walk(p)
      else if (e.name.endsWith('.md')) {
        md++
        if (e.name.endsWith('.zh.md')) zh++
      }
    }
  }
  walk(join(root, 'references', 'official-docs', 'docs'))
  if (md !== facts.mirror.mdPages) bad('mirror md pages', `${md} counted vs ${facts.mirror.mdPages} in facts.json`)
  else ok('mirror md pages', String(md))
  if (zh !== facts.mirror.zhPairs) bad('mirror zh pairs', `${zh} counted vs ${facts.mirror.zhPairs} in facts.json`)
  else ok('mirror zh pairs', String(zh))

  // Any document quoting a page count must quote the current one.
  for (const f of ['guide/quick-reference.md', 'guide/quick-reference.zh-CN.md', 'references/sources.md']) {
    let t
    try { t = read(f) } catch { continue }
    const stale = /\b(215|369|182)\s*(?:md|pages|篇)/i.exec(t)
    if (stale) bad(`${f} stale page count`, `states "${stale[0]}" but the mirror has ${facts.mirror.mdPages} pages`)
  }
}

// ---- 4. Host line and the rc.3 upgrade-guide counts -------------------------------
// The facts.json host block is the one home for the published line. Two things drift:
// the dist-tags are restated in six prose files, and the "46 guides in rc.3" count only
// holds if the 13 v0.2.2-rc.2 guides stay out of it.
{
  const host = facts.host
  const guideDir = join(root, 'references', 'official-docs', 'docs', 'upgrade-guide')
  const counts = {}
  for (const version of Object.keys(host.rc3GuideCounts).filter((v) => v !== 'total')) {
    let dirs = []
    try {
      dirs = readdirSync(join(guideDir, `v${version}`), { withFileTypes: true })
    } catch {
      bad('rc.3 guide directories', `missing docs/upgrade-guide/v${version} in the mirror`)
      continue
    }
    counts[version] = dirs.filter((e) => e.isDirectory()).length
    const want = host.rc3GuideCounts[version]
    if (counts[version] !== want) bad(`rc.3 guides v${version}`, `${counts[version]} dirs vs ${want} in facts.json`)
    else ok(`rc.3 guides v${version}`, String(counts[version]))
  }
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  if (total !== host.rc3GuideCounts.total) bad('rc.3 guides total', `${total} vs ${host.rc3GuideCounts.total} in facts.json`)
  else ok('rc.3 guides total', String(total))

  // The next-version guides are master-only; they must not be in the mirror at all.
  const nextDir = join(guideDir, `v${host.nextVersion.authoredAt}`)
  let nextPresent = false
  try { readdirSync(nextDir); nextPresent = true } catch { /* absent, as expected */ }
  if (nextPresent) bad('next-version guides in mirror', `docs/upgrade-guide/v${host.nextVersion.authoredAt} is present but belongs after the rc.3 tag`)
  else ok('next-version guides absent from mirror', host.nextVersion.authoredAt)

  // Every prose file that states the host line must restate these exact tokens.
  const docFiles = ['README.md', 'README.en.md', 'README.es.md', 'README.pt.md', 'README.hi.md', 'SKILL.md', 'guide/version-matrix.md']
  const tokens = [host.npmLatest, host.npmNext, host.npmAlpha, host.newestTag, String(host.npmVersionCount), String(host.githubReleaseCount)]
  for (const f of docFiles) {
    const t = read(f)
    const missing = tokens.filter((token) => !t.includes(token))
    if (missing.length) bad(`${f} host line`, `missing ${missing.join(', ')}`)
    else ok(`${f} host line`, `${host.npmLatest}/${host.npmNext}/${host.npmAlpha}`)
  }

  // The mirror pin and its counts are restated in the same places.
  const pinFiles = ['README.md', 'README.en.md', 'README.es.md', 'README.pt.md', 'README.hi.md', 'SKILL.md', 'references/sources.md', 'references/official-docs/README.md', 'guide/quick-reference.md', 'guide/quick-reference.zh-CN.md', 'guide/quick-reference.es.md', 'guide/quick-reference.pt.md', 'guide/quick-reference.hi.md']
  const pinTokens = [facts.mirror.pinnedCommit.slice(0, 8), String(facts.mirror.mdPages), String(facts.mirror.zhPairs)]
  for (const f of pinFiles) {
    const t = read(f)
    const missing = pinTokens.filter((token) => !t.includes(token))
    if (missing.length) bad(`${f} mirror pin`, `missing ${missing.join(', ')}`)
    else ok(`${f} mirror pin`, facts.mirror.pinnedCommit.slice(0, 8))
  }
}

// ---- 5. CLI check counts ---------------------------------------------------------
{
  const src = read('src/cli/skill-sections.ts')
  const n = [...src.matchAll(/^\s*'[a-z0-9-]+':\s*\{/gm)].length
  if (n !== facts.cli.staticChecks) bad('CLI static checks', `${n} citations vs ${facts.cli.staticChecks} in facts.json`)
  else ok('CLI static checks', String(n))
}

// ---- 6. Seam index consistency ---------------------------------------------------
{
  const idx = JSON.parse(read('data/seams/index.json'))
  const corridor = idx.seams.filter((s) => /^L\d+$/.test(s.id)).length
  if (corridor !== facts.seams.corridorL) bad('corridor L seams', `${corridor} vs ${facts.seams.corridorL}`)
  else ok('corridor L seams', String(corridor))

  const areas = idx.capabilities.filter((c) => /^A\d+$/.test(c.id)).length
  if (areas !== facts.seams.capabilityAreas) bad('capability areas', `${areas} vs ${facts.seams.capabilityAreas}`)
  else ok('capability areas', String(areas))

  const corridorSeams = idx.seams.filter((s) => /^L\d+$/.test(s.id))
  const detectable = corridorSeams.filter((s) => s.detectable).length
  const advisory = corridorSeams.length - detectable
  if (detectable !== facts.seams.staticallyDetectable) bad('statically detectable seams', `${detectable} vs ${facts.seams.staticallyDetectable}`)
  else ok('statically detectable seams', String(detectable))
  if (advisory !== facts.seams.advisoryOnly) bad('advisory-only seams', `${advisory} vs ${facts.seams.advisoryOnly}`)
  else ok('advisory-only seams', String(advisory))

  // The 0.2.2 line covered by the rc.3 tag: 46 K seams, and the 13 master-only rc.2 guides
  // recorded separately rather than smuggled into the rc.3 count.
  const kSeams = idx.seams.filter((s) => /^K\d+$/.test(s.id))
  if (kSeams.length !== facts.seams.corridorK) bad('corridor K seams', `${kSeams.length} vs ${facts.seams.corridorK}`)
  else ok('corridor K seams', String(kSeams.length))
  const kDetectable = kSeams.filter((s) => s.detectable).length
  if (kDetectable !== facts.seams.corridorKDetectable) bad('corridor K detectable', `${kDetectable} vs ${facts.seams.corridorKDetectable}`)
  else ok('corridor K detectable', String(kDetectable))
  const kAdvisory = kSeams.length - kDetectable
  if (kAdvisory !== facts.seams.corridorKAdvisory) bad('corridor K advisory', `${kAdvisory} vs ${facts.seams.corridorKAdvisory}`)
  else ok('corridor K advisory', String(kAdvisory))
  const unreleased = Array.isArray(idx.unreleased) ? idx.unreleased.length : -1
  if (unreleased !== facts.seams.unreleased) bad('unreleased seams', `${unreleased} vs ${facts.seams.unreleased}`)
  else ok('unreleased seams', String(unreleased))

  // The seam index must baseline on the same release the mirror is pinned to.
  if (idx.hostBaseline !== facts.mirror.pinnedTag) bad('seam host baseline', `${idx.hostBaseline} vs ${facts.mirror.pinnedTag}`)
  else ok('seam host baseline', idx.hostBaseline)
}

// ---- 7. Release consistency ------------------------------------------------------
{
  const pkg = JSON.parse(read('package.json'))
  const changelog = read('CHANGELOG.md')
  if (!changelog.includes(`## [${pkg.version}]`)) {
    bad('CHANGELOG section', `no "## [${pkg.version}]" section for the current package.json version`)
  } else ok('CHANGELOG section', pkg.version)
}

if (asJson) {
  console.log(JSON.stringify({ facts: facts.schema, checked, failures }, null, 2))
} else {
  for (const c of checked) console.log(`  ok    ${c}`)
  if (failures.length) {
    console.error('\ncheck-facts: FAIL')
    for (const f of failures) console.error(`  - ${f}`)
    console.error('\nEvery number above has one home: data/facts.json. Update it, then update the prose.')
  } else {
    console.log(`\ncheck-facts OK (${checked.length} assertions against data/facts.json)`)
  }
}
process.exit(failures.length ? 1 : 0)
