// One entry point for Windows development and Linux/Lightsail checkouts.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { spawn, spawnSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const project = join(root, 'purchase-order-agent');
const args = process.argv.slice(2);
const flags = new Set(args);
if (!existsSync(join(project, 'purchase_demo', 'demo_app.py')) || args.some(a => !['--setup', '--test', '--public'].includes(a))) {
  console.error('Run npm start from the StockPilot repository. Options: --setup, --test, --public.');
  process.exit(1);
}
const python = join(project, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const requirements = join(project, 'purchase_demo', 'requirements.txt');
const marker = join(project, '.venv', '.stockpilot-requirements');
const fingerprint = createHash('sha256').update(readFileSync(requirements)).digest('hex');
function run(command, commandArgs) {
  const result = spawnSync(command, commandArgs, { cwd: project, stdio: 'inherit', shell: false });
  if (result.error || result.status !== 0) {
    console.error(result.error?.message || `Command failed (exit ${result.status}).`);
    process.exit(result.status || 1);
  }
}
if (!existsSync(python)) {
  const choices = process.env.STOCKPILOT_PYTHON ? [[process.env.STOCKPILOT_PYTHON, []]] :
    (process.platform === 'win32' ? [['py', ['-3']], ['python', []]] : [['python3', []], ['python', []]]);
  const selected = choices.find(([cmd, prefix]) => spawnSync(cmd, [...prefix, '-c',
    'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'], { stdio: 'ignore' }).status === 0);
  if (!selected) {
    console.error('Install Python 3.10+ (3.12/3.13 recommended), then retry. On Ubuntu also install python3-venv.');
    process.exit(1);
  }
  console.log('Creating the local Python environment…');
  run(selected[0], [...selected[1], '-m', 'venv', join(project, '.venv')]);
}
if (!existsSync(marker) || readFileSync(marker, 'utf8').trim() !== fingerprint || flags.has('--setup')) {
  console.log('Checking/installing Python dependencies. First setup needs internet…');
  run(python, ['-m', 'pip', 'install', '-r', requirements]);
  writeFileSync(marker, fingerprint + '\n');
}
if (flags.has('--test')) {
  run(python, ['-m', 'pytest', 'purchase_demo/tests', '-q', '-p', 'no:cacheprovider']);
  process.exit(0);
}
if (flags.has('--setup')) { console.log('StockPilot is ready. Run npm start.'); process.exit(0); }
const port = process.env.PORT || '8504';
if (!/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65535) {
  console.error('PORT must be an integer between 1 and 65535.'); process.exit(1);
}
console.log(`Starting ${join(project, 'purchase_demo', 'demo_app.py')}`);
console.log(`Open http://localhost:${port} — press Ctrl+C to stop.`);
const child = spawn(python, ['-m', 'streamlit', 'run', 'purchase_demo/demo_app.py',
  '--server.address', flags.has('--public') ? '0.0.0.0' : '127.0.0.1', '--server.port', port,
  '--server.headless', 'true', '--browser.gatherUsageStats', 'false', '--theme.base', 'light',
  '--theme.primaryColor', '#28785f', '--theme.backgroundColor', '#f6f8f6',
  '--theme.secondaryBackgroundColor', '#eef3ef', '--theme.textColor', '#21372f'],
  { cwd: project, stdio: 'inherit', shell: false });
child.on('error', error => { console.error(error.message); process.exitCode = 1; });
child.on('exit', code => { process.exitCode = code ?? 0; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
