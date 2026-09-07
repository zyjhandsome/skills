// Shared helpers: Playwright resolution, IO, normalization.
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';

const PW_NAMES = ['playwright', 'playwright-core', '@playwright/test'];

function cheapRoots() {
  const roots = (process.env.NODE_PATH || '').split(path.delimiter);
  if (process.env.APPDATA) roots.push(path.join(process.env.APPDATA, 'npm', 'node_modules'));
  roots.push(
    path.join(os.homedir(), '.npm-global', 'lib', 'node_modules'),
    '/usr/local/lib/node_modules',
    '/usr/lib/node_modules',
    '/opt/homebrew/lib/node_modules',
  );
  return roots;
}

function npmGlobalRoot() {
  try {
    const bin = process.platform === 'win32' ? 'npm.cmd' : 'npm';
    const r = spawnSync(bin, ['root', '-g'], { encoding: 'utf8', timeout: 20000 });
    return [(r.stdout || '').trim()];
  } catch {
    return [];
  }
}

async function tryRoots(roots, cwd) {
  const dirs = [...new Set([cwd, ...roots].filter((p) => p && fs.existsSync(p)))];
  for (const dir of dirs) {
    for (const name of PW_NAMES) {
      let href;
      try {
        const req = createRequire(path.join(dir, '__resolve__.js'));
        href = pathToFileURL(req.resolve(name)).href;
      } catch {
        continue;
      }
      try {
        const mod = await import(href);
        const api = mod.default?.chromium ? mod.default : mod;
        if (api?.chromium) return { ...api, source: `${name} @ ${dir}` };
      } catch { /* broken install; try next candidate */ }
    }
  }
  return null;
}

/**
 * Resolve a Playwright module from the project, then from global installs.
 * Returns { chromium, firefox, webkit, devices, source } or null.
 */
export async function loadPlaywright(cwd = process.cwd()) {
  return (await tryRoots(cheapRoots(), cwd)) || (await tryRoots(npmGlobalRoot(), cwd));
}

export function browserCacheDir() {
  if (process.env.PLAYWRIGHT_BROWSERS_PATH) return process.env.PLAYWRIGHT_BROWSERS_PATH;
  if (process.platform === 'win32') return path.join(os.homedir(), 'AppData', 'Local', 'ms-playwright');
  if (process.platform === 'darwin') return path.join(os.homedir(), 'Library', 'Caches', 'ms-playwright');
  return path.join(os.homedir(), '.cache', 'ms-playwright');
}

export const ensureDir = (p) => fs.mkdirSync(p, { recursive: true });

export function writeJson(file, data) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

export function readJson(file, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

export function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const eq = a.indexOf('=');
      if (eq > -1) args[a.slice(2, eq)] = a.slice(eq + 1);
      else if (argv[i + 1] && !argv[i + 1].startsWith('--')) args[a.slice(2)] = argv[++i];
      else args[a.slice(2)] = true;
    } else args._.push(a);
  }
  return args;
}

/** Strip origin + volatile query/hash noise so two hosts compare equal. */
export function normalizeUrl(url, origins = []) {
  if (typeof url !== 'string' || !url) return url;
  let out = url;
  for (const o of origins.filter(Boolean)) out = out.split(o).join('{origin}');
  return out
    .replace(/([?&])(_t|_|timestamp|ts|rnd|random|v|cacheBust)=[^&#]*/gi, '$1$2={volatile}')
    .replace(/\b\d{13}\b/g, '{epoch-ms}')
    .replace(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi, '{uuid}');
}

/** Mask values that legitimately differ between two environments. */
export function normalizeText(text, patterns = []) {
  if (typeof text !== 'string') return text;
  let out = text.replace(/\s+/g, ' ').trim();
  for (const p of patterns) {
    try {
      out = out.replace(new RegExp(p, 'g'), '{masked}');
    } catch { /* invalid user regex is ignored, reported by caller */ }
  }
  return out
    .replace(/\d{4}[-/]\d{1,2}[-/]\d{1,2}([ T]\d{1,2}:\d{2}(:\d{2})?)?/g, '{date}')
    .replace(/\b\d{2}:\d{2}(:\d{2})?\b/g, '{time}');
}

export const slug = (s) => String(s).replace(/[^\w.-]+/g, '-').replace(/^-|-$/g, '') || 'x';

/** Stable JSON used to prove both captures and compare used the same contract. */
export function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  if (value && typeof value === 'object') {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${stableStringify(value[k])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function configFingerprint(config) {
  return crypto.createHash('sha256').update(stableStringify(config)).digest('hex');
}
