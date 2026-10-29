export const meta = {
  name: 'production-sweep',
  description: 'QA every READINESS.md flow as a real user in parallel, refute each failure, return row verdicts',
  whenToUse: 'After flows are built, before deploy, or as the final regression pass. args: {url, flows:[{id, flow, surfaces}], widths?}',
  phases: [
    { title: 'QA', detail: 'one skeptical user per flow, mobile and desktop' },
    { title: 'Refute', detail: 'two independent agents try to refute each failure' },
  ],
}

// Usage (Claude Code, workflows enabled):
//   Workflow({ name: 'production-sweep', args: { url: 'http://localhost:3000',
//     flows: [{ id: 'F1', flow: 'Sign up and land on a useful first screen', surfaces: 'web' }], widths: [375, 1440] } })
const url = args && args.url
const flows = (args && args.flows) || []
const widths = (args && args.widths) || [375, 1440]
if (!url || !flows.length) throw new Error('args.url and args.flows are required')

const VERDICT = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    passed: { type: 'boolean' },
    steps: { type: 'string', description: 'what was done, as a user' },
    defects: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string', description: 'user words' }, repro: { type: 'string' }, width: { type: 'number' }, evidence: { type: 'string' } },
      required: ['title', 'repro'] } },
    evidence: { type: 'array', items: { type: 'string' }, description: 'paths under qa/' },
  },
  required: ['id', 'passed', 'steps', 'defects', 'evidence'],
}
const REFUTE = { type: 'object', properties: { refuted: { type: 'boolean' }, why: { type: 'string' } }, required: ['refuted', 'why'] }

const results = await pipeline(
  flows,
  (f) => agent(
    `You are a skeptical first-time user testing flow ${f.id}: "${f.flow}" (surfaces: ${f.surfaces || 'web'}) at ${url}.
Follow the qa-flows skill. Use the built-in browser or Chrome DevTools tools (load them with ToolSearch). Test at widths ${widths.join(' and ')}px.
Fresh state, happy path, then unhappy paths (wrong/empty input, double submit, refresh mid-flow, back button). Watch the console and network.
Save screenshots under qa/${f.id}/ and write qa/${f.id}/notes.md. Do not fix anything; report what you saw.`,
    { label: `qa:${f.id}`, phase: 'QA', schema: VERDICT }),
  async (v, f) => {
    if (!v) return null
    if (v.passed || !v.defects.length) return { ...v, confirmed: [] }
    const confirmed = []
    for (const d of v.defects) {
      const votes = (await parallel([0, 1].map((i) => () => agent(
        `Flow ${f.id} "${f.flow}" at ${url}. A tester reported: "${d.title}" (repro: ${d.repro}, width ${d.width || widths[0]}px).
Try to refute it by reproducing exactly those steps yourself in the browser (perspective ${i === 0 ? 'correctness: does the product really misbehave?' : 'tester error: wrong URL, stale state, impatience?'}).
refuted=true only if you reproduced the steps and the product behaved correctly.`,
        { label: `refute:${f.id}`, phase: 'Refute', schema: REFUTE, effort: 'low' })))).filter(Boolean)
      const stands = votes.filter((x) => !x.refuted).length >= 1 && votes.filter((x) => x.refuted).length < 2
      if (stands) confirmed.push(d)
    }
    return { ...v, confirmed }
  },
)

const rows = results.filter(Boolean).map((r) => ({
  id: r.id,
  status: r.confirmed.length === 0 && r.passed ? 'verified' : 'todo',
  defects: r.confirmed,
  evidence: r.evidence,
}))
log(`${rows.filter((r) => r.status === 'verified').length}/${flows.length} flows verified; ${rows.reduce((n, r) => n + r.defects.length, 0)} confirmed defects`)
return { rows, skipped: flows.length - results.filter(Boolean).length }
