// check_face.cjs <main.lua> -- generic watch-face source check.
//
// usage: node check_face.cjs C:\path\to\main.lua
//
// WHY A SEPARATE CHECKER.  lint_lua.cjs is deliberately specific to the mouse
// face: it asserts that particular symbols exist and that deleted ones do not.
// A second face cannot use it.  What EVERY face needs is the things that cannot
// be caught after the fact on the device:
//
//   1. IT MUST PARSE.  A syntax error is a black screen with no text anywhere.
//
//   2. IT MUST FIT IN MAXVARS.  Lua allows 200 active local variables per
//      function and a CHUNK IS A FUNCTION, so every top-level `local` competes
//      for the same 200 slots.  Exceeding it is NOT a catchable error -- the
//      whole chunk fails to COMPILE, so the face never runs: black screen, no
//      text, empty log, every time.  Two delivered builds died exactly this way.
//      luaparse does not implement the limit, so it must be counted by hand.
//      Declarations are counted, not names: `local a, b` is two slots.
//
//   3. NOTHING MAY READ A NAME THAT IS DECLARED `local` LATER IN THE CHUNK.
//      Lua has no hoisting, so such a read silently resolves to the GLOBAL, which
//      is nil.  This shipped in the first cut of btinject/main.lua and would have
//      cost a flash cycle.
//        (a) inside a closure:  `local function fn() return EXEC end` written
//            ABOVE `local EXEC = 0` captures the global, and every call dies with
//            "attempt to perform arithmetic on a nil value" on the device.
//        (b) in a PLAIN TOP-LEVEL statement: no closure is involved, so an
//            earlier version of this checker did not look -- and the hardware log
//            caught it instead, with a boot line that read "module=nil" because it
//            mentioned MODERR, declared hundreds of lines below.  Both are now
//            checked; (b) is the one that matters when the name is used for
//            arithmetic rather than only for output.
//      It is a pure syntactic property, so it is checked here.
//
//   4. Top-level locals should keep real headroom below MAXVARS, not sit at 199.
const fs = require('fs');
const luaparse = require(process.env.LUAPARSE_PATH||'luaparse');

const LIMIT = 190;   // headroom under Lua's hard 200

const path = process.argv[2];
if (!path) { console.error('usage: node check_face.cjs <main.lua>'); process.exit(2); }
// Strip a UTF-8 BOM.  PowerShell 5.1's `Set-Content -Encoding UTF8` writes one,
// and luaparse then fails with an internal error rather than a clean parse error
// ("Cannot read properties of undefined (reading 'range')"), which sends you
// looking for a syntax bug that is not there.  A BOM in a face's main.lua is a
// real defect too, so it is reported rather than silently accepted.
let src = fs.readFileSync(path, 'utf8');
const hadBOM = src.charCodeAt(0) === 0xFEFF;
if (hadBOM) src = src.slice(1);

let ast;
try {
  // NO `ranges: true`.  luaparse has an internal crash ("Cannot read properties of
  // undefined (reading 'range')") with that option on some constructs, and it
  // fails at PARSE time, which would make this checker reject perfectly good
  // source.  Line/column from `locations` is enough: every offset needed here is
  // a comparison between two positions in the same file, and line*BIG + column
  // orders them correctly without converting to a byte offset at all.
  ast = luaparse.parse(src, { luaVersion: '5.3', comments: false, locations: true });
} catch (e) {
  console.error(`PARSE ERROR in ${path}: ${e.message}`);
  process.exit(1);
}
const posOf = (node) => node.loc.start.line * 100000 + node.loc.start.column;
// posOf() encodes line*100000 + column, so the line comes straight back out.
const declLineOf = (p) => Math.floor(p / 100000);

// ---------------------------------------------------------------- MAXVARS count
// Walk only the chunk's own statements; a nested function gets its own 200 slots.
let count = 0;
function countLocals(node) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) { for (const n of node) countLocals(n); return; }
  if (node.type === 'FunctionDeclaration') {
    if (node.isLocal) count += 1;
    return; // body has its own limit, not the enclosing chunk's
  }
  if (node.type === 'LocalStatement') count += node.variables.length;
  for (const k of Object.keys(node)) {
    if (k === 'type' || k === 'loc' || k === 'range') continue;
    countLocals(node[k]);
  }
}for (const stmt of ast.body) {
  countLocals(stmt);
}

// ------------------------------------------------- top-level local declaration order
// name -> source offset at which it becomes a local
const declAt = new Map();
for (const stmt of ast.body) {
  if (stmt.type === 'FunctionDeclaration' && stmt.isLocal && stmt.identifier) {
    declAt.set(stmt.identifier.name, posOf(stmt));
  }
  if (stmt.type === 'LocalStatement') {
    for (const v of stmt.variables) {
      if (!declAt.has(v.name)) declAt.set(v.name, posOf(stmt));
    }
  }
}

// ------------------------------------------------------- closures capturing later locals
const problems = [];

function identifiersIn(node, out, skipDeclNames) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) { for (const n of node) identifiersIn(n, out, skipDeclNames); return; }
  if (node.type === 'Identifier') { out.push(node); return; }
  if (node.type === 'MemberExpression') {
    // `a.b` -- only `a` is a variable read
    identifiersIn(node.base, out, skipDeclNames);
    return;
  }
  for (const k of Object.keys(node)) {
    if (k === 'type' || k === 'loc' || k === 'range') continue;
    identifiersIn(node[k], out, skipDeclNames);
  }
}

// Collect every function created at the chunk's top level, with the offset at
// which the closure is CREATED (that is when capture happens).
function topLevelFunctions() {
  const out = [];
  for (const stmt of ast.body) {
    if (stmt.type === 'FunctionDeclaration') {
      out.push({ name: stmt.identifier && stmt.identifier.name, node: stmt, at: posOf(stmt) });
    } else if (stmt.type === 'LocalStatement') {
      for (let i = 0; i < stmt.init.length; i++) {
        const init = stmt.init[i];
        if (init && (init.type === 'FunctionExpression' || init.type === 'FunctionDeclaration')) {
          const v = stmt.variables[i] || stmt.variables[0];
          out.push({ name: v && v.name, node: init, at: posOf(stmt) });
        }
      }
    }
  }
  return out;
}

for (const f of topLevelFunctions()) {
  // Names this function itself declares (params + its own locals) shadow outer
  // ones and must not be reported.
  const shadow = new Set();
  const body = f.node.body || [];
  const walkShadow = (n) => {
    if (!n || typeof n !== 'object') return;
    if (Array.isArray(n)) { for (const x of n) walkShadow(x); return; }
    if (n.type === 'LocalStatement') for (const v of n.variables) shadow.add(v.name);
    if (n.type === 'FunctionDeclaration' && n.identifier) shadow.add(n.identifier.name);
    for (const k of Object.keys(n)) {
      if (k === 'type' || k === 'loc' || k === 'range') continue;
      walkShadow(n[k]);
    }
  };
  if (f.node.parameters) for (const p of f.node.parameters) if (p.name) shadow.add(p.name);
  walkShadow(body);

  const ids = [];
  identifiersIn(body, ids, shadow);
  const reported = new Set();
  for (const id of ids) {
    if (shadow.has(id.name)) continue;
    const d = declAt.get(id.name);
    if (d === undefined) continue;              // a genuine global: not our business
    if (d > f.at && !reported.has(id.name)) {   // declared AFTER the closure was created
      reported.add(id.name);
      problems.push({
        fn: f.name || '<anonymous>',
        name: id.name,
        line: id.loc.start.line,
        declLine: declLineOf(d),
      });
    }
  }
}

// ------------------------------------- top-level reads of a LATER top-level local
// ⚠ THE SAME BUG AS (3), IN THE ONE PLACE THE CLOSURE CHECK CANNOT SEE.
// A plain top-level statement is not a closure, so nothing above looks at it --
// and the hardware log proved that gap is real: the boot line read "module=nil"
// because it mentioned MODERR, which is declared hundreds of lines further down.
// Harmless in THAT instance; the identical pattern with EXEC, CFG or MOD would be
// a dead face, because those are read for arithmetic rather than only for output.
//
// Function bodies are skipped here on purpose -- a read inside one is a closure
// capture and belongs to the check above, which also knows where the closure was
// created.  This pass is only about code that runs in the chunk's own body.
function readsOutsideFunctions(node, out) {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) { for (const n of node) readsOutsideFunctions(n, out); return; }
  if (node.type === 'FunctionDeclaration' || node.type === 'FunctionExpression') return;
  if (node.type === 'Identifier') { out.push(node); return; }
  if (node.type === 'MemberExpression') { readsOutsideFunctions(node.base, out); return; }
  for (const k of Object.keys(node)) {
    if (k === 'type' || k === 'loc' || k === 'range') continue;
    readsOutsideFunctions(node[k], out);
  }
}

const forward = [];
const seenFwd = new Set();
for (const stmt of ast.body) {
  if (stmt.type === 'FunctionDeclaration') continue;   // covered by the closure check
  const at = posOf(stmt);
  const ids = [];
  if (stmt.type === 'LocalStatement') {
    // Only the initialisers: the NAMES on the left are the declaration itself.
    for (const init of stmt.init) readsOutsideFunctions(init, ids);
  } else {
    readsOutsideFunctions(stmt, ids);
  }
  for (const id of ids) {
    const d = declAt.get(id.name);
    if (d === undefined || d <= at) continue;          // global, or already declared
    const key = id.name + '@' + id.loc.start.line + ':' + id.loc.start.column;
    if (seenFwd.has(key)) continue;
    seenFwd.add(key);
    forward.push({ name: id.name, line: id.loc.start.line, declLine: declLineOf(d) });
  }
}

// ------------------------------------------------------------------------ report
console.log(`file        : ${path}`);console.log(`source      : ${src.length} bytes, ${src.split('\n').length} lines`);
if (hadBOM) console.log('note        : a UTF-8 BOM was present and has been ignored');
console.log(`top-level   : ${count} local declarations / ${LIMIT} allowed (Lua hard limit 200)`);
console.log(`headroom    : ${LIMIT - count} slots (${Math.round(count / LIMIT * 100)}% used)`);

let failed = false;

if (count > LIMIT) {
  console.error(`FAIL: ${count} top-level locals exceeds ${LIMIT}.`);
  console.error('      On the device this is a COMPILE failure: black screen, no text, empty log.');
  console.error('      Fix: move construction into functions, or collect locals into one table.');
  failed = true;
}

if (problems.length) {
  console.error('');
  console.error(`FAIL: ${problems.length} closure(s) capture a GLOBAL that is declared ` +
                '`local` LATER in the chunk.');
  console.error('      Lua has no hoisting, so the closure sees nil, not the local.');
  for (const p of problems) {
    console.error(`        ${p.fn}() line ${p.line} uses '${p.name}', ` +
                  `declared local at line ${p.declLine}`);
  }
  console.error('      Fix: move the `local` declaration above the function.');
  failed = true;
}

if (forward.length) {
  console.error('');
  console.error(`FAIL: ${forward.length} top-level statement(s) read a name that is declared ` +
                '`local` LATER in the chunk.');
  console.error('      Lua has no hoisting, so they read the GLOBAL (nil), not the local.');
  for (const p of forward) {
    console.error(`        line ${p.line} uses '${p.name}', ` +
                  `declared local at line ${p.declLine}`);
  }
  console.error('      Fix: move the `local` declaration above the first use.');
  failed = true;
}

if (failed) process.exit(1);
console.log('OK');
