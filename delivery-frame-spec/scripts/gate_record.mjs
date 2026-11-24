// @ts-check
/**
 * Gate-record block inside proposal.md.
 * The block is excluded from artifact_revision, so writing an approval does not
 * move the revision. Anything other than the two gate lines is an error.
 */

export const GATE_START = "<!-- delivery:gate-record:start -->";
export const GATE_END = "<!-- delivery:gate-record:end -->";

const KIND_LABEL = { spec: "规格闸门", impl: "实现闸门" };
const LABEL_KIND = { 规格闸门: "spec", 实现闸门: "impl" };
const LINE_RE = /^- (规格闸门|实现闸门)[:：][ \t]*(.*)\r?$/;

/**
 * @param {string} text
 * @returns {Array<{ text: string, nl: boolean }>}
 */
function splitKeep(text) {
  if (text === "") return [];
  const raw = text.split("\n");
  /** @type {Array<{ text: string, nl: boolean }>} */
  const rows = [];
  for (let i = 0; i < raw.length; i++) {
    if (i === raw.length - 1 && raw[i] === "" && text.endsWith("\n")) break;
    const nl = i < raw.length - 1 || text.endsWith("\n");
    rows.push({ text: raw[i], nl });
  }
  return rows;
}

/** @param {Array<{ text: string, nl: boolean }>} rows */
function joinKeep(rows) {
  return rows.map((row) => row.text + (row.nl ? "\n" : "")).join("");
}

/**
 * @param {string} text
 * @returns {{ rows: Array<{ text: string, nl: boolean }>, block: { start: number, end: number } | null }}
 */
function scan(text) {
  const rows = splitKeep(text);
  /** @type {number[]} */
  const starts = [];
  /** @type {number[]} */
  const ends = [];
  rows.forEach((row, index) => {
    const trimmed = row.text.trim();
    if (trimmed === GATE_START) starts.push(index);
    if (trimmed === GATE_END) ends.push(index);
  });
  if (starts.length === 0 && ends.length === 0) return { rows, block: null };
  if (starts.length === 0 || ends.some((end) => end < starts[0])) {
    throw new Error("gate-record: end without start");
  }
  if (ends.length === 0) throw new Error("gate-record: start without end");
  if (starts.length > 1 || ends.length > 1) throw new Error("gate-record: more than one block");
  const start = starts[0];
  const end = ends[0];
  /** @type {Record<"spec" | "impl", number>} */
  const seen = { spec: 0, impl: 0 };
  for (let i = start + 1; i < end; i++) {
    const line = rows[i].text;
    if (line.trim() === "") continue;
    const match = line.match(LINE_RE);
    if (!match) throw new Error(`gate-record: unexpected line: ${line.trim()}`);
    const kind = LABEL_KIND[/** @type {"规格闸门" | "实现闸门"} */ (match[1])];
    seen[kind] += 1;
    if (seen[kind] > 1) throw new Error(`gate-record: duplicate ${kind} gate`);
  }
  return { rows, block: { start, end } };
}

/** @returns {{ status: "pending", approvedBy: null, approvedAt: null, revision: null, acceptedWarnings: string[], note: null }} */
function blankGate() {
  return {
    status: "pending",
    approvedBy: null,
    approvedAt: null,
    revision: null,
    acceptedWarnings: [],
    note: null,
  };
}

/**
 * @param {string} rest
 * @returns {{ status: "pending" | "n/a" | "approved", approvedBy: string | null, approvedAt: string | null, revision: string | null, acceptedWarnings: string[], note: string | null }}
 */
function parseRest(rest) {
  const trimmed = rest.trim();
  if (trimmed === "待批准") return blankGate();
  const notApplicable = trimmed.match(/^不适用（([\s\S]*)）$/);
  if (notApplicable) {
    return { ...blankGate(), status: "n/a", note: notApplicable[1] };
  }
  const parts = trimmed.split(" | ");
  if (parts[0] !== "已批准" || parts.length < 6) {
    throw new Error("gate-record: unrecognized gate line");
  }
  const warningField = parts[4];
  const noteField = parts.slice(5).join(" | ");
  if (!warningField.startsWith("接受警告：") || !noteField.startsWith("备注：")) {
    throw new Error("gate-record: unrecognized gate line");
  }
  const warningBody = warningField.slice("接受警告：".length);
  const noteBody = noteField.slice("备注：".length);
  return {
    status: "approved",
    approvedBy: parts[1],
    approvedAt: parts[2],
    revision: parts[3],
    acceptedWarnings: warningBody === "无" ? [] : warningBody.split(",").filter((id) => id.length > 0),
    note: noteBody === "无" ? null : noteBody,
  };
}

/** @param {string} text */
export function stripGateRecord(text) {
  const { rows, block } = scan(text);
  if (!block) return text;
  return joinKeep(rows.slice(0, block.start).concat(rows.slice(block.end + 1)));
}

/** @param {string} text */
export function parseGateRecord(text) {
  const { rows, block } = scan(text);
  /** @type {{ spec: ReturnType<typeof blankGate> | null, impl: ReturnType<typeof blankGate> | null }} */
  const parsed = { spec: null, impl: null };
  if (!block) return parsed;
  for (let i = block.start + 1; i < block.end; i++) {
    const line = rows[i].text;
    if (line.trim() === "") continue;
    const match = line.match(LINE_RE);
    if (!match) continue;
    const kind = LABEL_KIND[/** @type {"规格闸门" | "实现闸门"} */ (match[1])];
    parsed[kind] = parseRest(match[2]);
  }
  return parsed;
}

/**
 * @param {"spec" | "impl"} kind
 * @param {{ status: "pending" | "n/a" | "approved", approvedBy: string | null, approvedAt: string | null, revision: string | null, acceptedWarnings: string[], note: string | null }} gate
 */
export function formatGateLine(kind, gate) {
  const label = KIND_LABEL[kind];
  if (gate.status === "pending") return `- ${label}：待批准`;
  if (gate.status === "n/a") return `- ${label}：不适用（${gate.note ?? ""}）`;
  const warnings = gate.acceptedWarnings.length > 0 ? gate.acceptedWarnings.join(",") : "无";
  const note = gate.note ? gate.note : "无";
  return `- ${label}：已批准 | ${gate.approvedBy} | ${gate.approvedAt} | ${gate.revision} | 接受警告：${warnings} | 备注：${note}`;
}

/**
 * @param {string} text
 * @param {"spec" | "impl"} kind
 * @param {{ status: "pending" | "n/a" | "approved", approvedBy: string | null, approvedAt: string | null, revision: string | null, acceptedWarnings: string[], note: string | null }} gate
 */
export function upsertGateLine(text, kind, gate) {
  const { rows, block } = scan(text);
  if (!block) throw new Error("gate-record: block missing");
  const formatted = formatGateLine(kind, gate);
  let replaced = false;
  for (let i = block.start + 1; i < block.end; i++) {
    const match = rows[i].text.match(LINE_RE);
    if (!match) continue;
    if (LABEL_KIND[/** @type {"规格闸门" | "实现闸门"} */ (match[1])] !== kind) continue;
    rows[i] = { text: formatted, nl: rows[i].nl };
    replaced = true;
    break;
  }
  if (!replaced) rows.splice(block.end, 0, { text: formatted, nl: true });
  return joinKeep(rows);
}

export function emptyGateBlock() {
  return `${GATE_START}\n- 规格闸门：待批准\n- 实现闸门：待批准\n${GATE_END}\n`;
}
