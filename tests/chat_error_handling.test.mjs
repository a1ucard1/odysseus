import { readFileSync } from 'node:fs';
import { strict as assert } from 'node:assert';

const source = readFileSync(new URL('../static/js/chat.js', import.meta.url), 'utf8');
const start = source.indexOf('        let errText = `Error ${res.status}`;');
const end = source.indexOf("        typewriterInto(holder.querySelector('.body'), errText);", start);
assert(start >= 0 && end > start);
const handle = new Function('res', 'document', 'Storage',
  `return (async () => { ${source.slice(start, end)} return errText; })();`);

let changed = false;
const document = { getElementById() { changed = true; return null; } };
const storage = {};
const response = (status, detail) => ({ status, text: async () => JSON.stringify({ detail }) });

assert.equal(await handle(response(409, 'This tool approval is invalid or expired.'), document, storage),
  'This tool approval is invalid or expired.');
assert.equal(changed, false);
assert.match(await handle(response(400, 'This model does not support tools'), document, storage), /switched to Chat mode/);
assert.equal(changed, true);
