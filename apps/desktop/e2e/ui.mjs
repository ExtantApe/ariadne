// The real window against the real tool in a throwaway home: real mouse drags, real moves, no real files. Run: pnpm --filter ariadne-desktop e2e (after a build).
import { webkit } from 'playwright';
import http from 'http'; import fs from 'fs'; import path from 'path'; import os from 'os'; import { execFileSync, spawnSync } from 'child_process';
const DIST = new URL('../dist', import.meta.url).pathname, CLI = new URL('../../../tools/cli.py', import.meta.url).pathname, OUT = process.env.E2E_SHOTS || fs.mkdtempSync(os.tmpdir() + '/ariadne-e2e-');
const H = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'ariadne-ui-'));
const env = { ...process.env, HOME: H, ARIADNE_HOME: H + '/ws' };
const cli = (...a) => spawnSync('/usr/bin/python3', [CLI, ...a], { env, encoding: 'utf8' });
const w = (rel, t = 'x') => { const p = H + '/' + rel; fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, t); };
fs.mkdirSync(H + '/Desktop'); fs.mkdirSync(H + '/Documents'); cli('init');
for (const f of ['a.pdf', 'b.pdf', 'c.pdf', 'd.pdf']) w('Downloads/' + f, f);
w('Documents/30 Legal/clash.pdf', 'keep'); w('Downloads/clash.pdf', 'new');
const plan = JSON.parse(cli('new-plan', '--name', 'ui').stdout).plan.replace('~', H);
fs.appendFileSync(plan, [['a.pdf', '20 Finance/23 Taxes/a renamed.pdf'], ['b.pdf', '20 Finance/23 Taxes/b.pdf'], ['c.pdf', '10 Home/c.pdf'], ['d.pdf', '10 Home/d.pdf']].map(([s, d]) => `,${H}/Downloads/${s},${H}/Documents/${d},test reason\n`).join(''));
const srv = http.createServer((q, r) => {
  if (q.url === '/invoke') { let b = ''; q.on('data', d => b += d); q.on('end', () => { const { cmd, args } = JSON.parse(b);
    if (cmd === 'cli') { const p = cli(...args.args); r.writeHead(p.status === 0 ? 200 : 500); r.end(p.status === 0 ? p.stdout : (p.stdout || p.stderr)); }
    else if (cmd === 'job_status') { r.end(JSON.stringify({ running: null, last_folder: '', last_ok: null, last_output: '' })); } else r.end('null'); }); return; }
  const f = DIST + (q.url === '/' ? '/index.html' : q.url.split('?')[0]); if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { 'content-type': f.endsWith('.js') ? 'text/javascript' : f.endsWith('.css') ? 'text/css' : 'text/html' }); r.end(fs.readFileSync(f));
}).listen(0);
const url = `http://127.0.0.1:${srv.address().port}/`;
const b = await webkit.launch(); const p = await b.newPage({ viewport: { width: 1100, height: 760 }, colorScheme: 'light' });
const errs = []; p.on('pageerror', e => errs.push(String(e)));
await p.addInitScript(() => { window.__TAURI_INTERNALS__ = { invoke: async (cmd, args) => { const r = await fetch('/invoke', { method: 'POST', body: JSON.stringify({ cmd, args }) }); const t = await r.text(); if (!r.ok) throw t; return cmd === 'cli' ? t : JSON.parse(t); }, transformCallback: () => 0 }; });
const ok = (n, c) => { console.log((c ? 'PASS ' : 'FAIL ') + n); if (!c) process.exitCode = 1; };
const ex = rel => fs.existsSync(H + '/' + rel);
await p.goto(url); await p.waitForSelector('text=items waiting to be filed'); ok('To file shows the count', (await p.innerText('.big-count')) === '5'); await p.screenshot({ path: OUT + '/1-tofile.png' });
await p.click('nav >> text=Plans'); await p.waitForSelector('text=Ready to review'); await p.screenshot({ path: OUT + '/2-plans.png' });
await p.click('.item >> text=Ui'); await p.waitForSelector('text=4 of 4 selected'); await p.screenshot({ path: OUT + '/3-review.png' });
ok('rename is shown', await p.isVisible('text=was a.pdf'));
ok('nothing moved just by opening', ex('Downloads/a.pdf'));
{ const box = await p.locator('.line',{hasText:'c.pdf'}).boundingBox(); const dest = await p.locator('details',{hasText:'23 Taxes'}).locator('summary').boundingBox();
  await p.mouse.move(box.x+120,box.y+10); await p.mouse.down(); await p.mouse.move(box.x+130,box.y+30,{steps:3}); await p.mouse.move(dest.x+200,dest.y+14,{steps:6}); await p.mouse.up(); await p.waitForSelector('.toast');
  const planText=()=>fs.readFileSync(plan,'utf8'); ok('drag sends a file to another folder', /c\.pdf,[^,]*20 Finance\/23 Taxes\/c\.pdf/.test(planText())); ok('nothing moved on disk by dragging', ex('Downloads/c.pdf')); ok('correction recorded', fs.readFileSync(H+'/ws/filing-rules.md','utf8').includes('c.pdf →'));
  await p.screenshot({path:OUT+'/3b-dragged.png'}); const rulesBefore=fs.readFileSync(H+'/ws/filing-rules.md','utf8'); await p.click('.toast button'); await p.waitForSelector('.toast',{state:'detached'}); ok('undo puts it back', /c\.pdf,[^,]*10 Home\/c\.pdf/.test(planText())); ok('undo takes the correction back out', !fs.readFileSync(H+'/ws/filing-rules.md','utf8').includes('c.pdf →')); ok('selection kept', await p.isVisible('text=4 of 4 selected')); }
// untick one row, then one whole group
await p.locator('.line', { hasText: 'b.pdf' }).locator('input').click(); await p.waitForSelector('text=3 of 4 selected');
await p.locator('summary', { hasText: '10 Home' }).locator('input').click(); await p.waitForSelector('text=1 of 4 selected');
await p.click('text=Move 1 item…'); ok('first click only asks', ex('Downloads/a.pdf') && await p.isVisible('text=Yes, move 1 item')); await p.screenshot({ path: OUT + '/4-confirm.png' });
await p.click('text=Yes, move 1 item'); await p.waitForSelector('text=Undo in History');
ok('only the ticked row moved', ex('Documents/20 Finance/23 Taxes/a renamed.pdf') && !ex('Downloads/a.pdf') && ex('Downloads/b.pdf') && ex('Downloads/c.pdf') && ex('Downloads/d.pdf'));
await p.screenshot({ path: OUT + '/5-moved.png' });
ok('rest stays waiting, not re-ticked', await p.isVisible('text=0 of 3 selected'));
await p.locator('.line', { hasText: 'b.pdf' }).locator('input').click(); await p.click('text=Move 1 item…'); await p.click('text=Yes, move 1 item'); await p.waitForSelector('text=0 of 2 selected');
ok('second pass moved only the new tick', ex('Documents/20 Finance/23 Taxes/b.pdf') && ex('Downloads/c.pdf'));
await p.locator('.btn', { hasText: 'Undo in History' }).click(); await p.waitForSelector('text=Undo…'); await p.locator('.btn', { hasText: 'Undo…' }).first().click(); await p.waitForSelector('text=Yes, put them back'); ok('undo asks first', !ex('Downloads/a.pdf')); await p.screenshot({ path: OUT + '/6-undo.png' });
await p.click('text=Yes, put them back'); await p.waitForSelector('text=Put back 2 items'); ok('undo restored both', ex('Downloads/a.pdf') && ex('Downloads/b.pdf') && !ex('Documents/20 Finance/23 Taxes/a renamed.pdf')); ok('batch shows undone', await p.isVisible('.pill >> text=Put back'));
// a clash is refused and shown
const plan2 = JSON.parse(cli('new-plan', '--name', 'clash').stdout).plan.replace('~', H); fs.appendFileSync(plan2, `,${H}/Downloads/clash.pdf,${H}/Documents/30 Legal/clash.pdf,clash\n`);
await p.click('nav >> text=Plans'); await p.click('.item >> text=Clash'); await p.waitForSelector('text=1 of 1 selected'); await p.click('text=Move 1 item…'); await p.click('text=Yes, move 1 item'); await p.waitForSelector('text=would be overwritten');
ok('error shown once', await p.locator('text=would be overwritten').count() === 1);
ok('clash refused and explained', fs.readFileSync(H + '/Documents/30 Legal/clash.pdf', 'utf8') === 'keep' && ex('Downloads/clash.pdf')); await p.screenshot({ path: OUT + '/7-clash.png' });
await p.click('nav >> text=Setup'); await p.waitForSelector('text=Read the Notes database'); await p.screenshot({ path: OUT + '/8-setup.png' });
ok('no page errors', errs.length === 0); if (errs.length) console.log(errs);
fs.writeFileSync(H + '/ws/plans/2026-01-01-broken.csv', 'approve,current_path,proposed_path,reason\nY,a,b,c,too,many\n'); await p.click('nav >> text=History'); await p.click('nav >> text=Plans'); await p.waitForSelector("text=Can't be read"); ok('a broken plan is listed, and the others stay', await p.isVisible('.item >> text=Clash') && await p.isVisible('text=2026-01-01-broken.csv'));
await b.close(); srv.close(); fs.rmSync(H, { recursive: true, force: true });
