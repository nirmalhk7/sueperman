import { readableLabel } from "@/lib/labels";

const productFields = new Set(["product_name", "brand", "model_number", "date_purchased", "merchant"]);

// Older team drafts embed a Python string dictionary. Read only their known
// fact fields and keep the original text if the whole block cannot be read.
function embeddedFacts(markdown: string): [string, string][] {
  const block = markdown.match(/^## Verified product facts\r?\n([^\r\n]+)/m)?.[1].trim();
  if (!block) return [];
  const pairs = /(?:^\{\s*|,\s*)'([a-z_]+)':\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')(?=\s*[,}])/g;
  const entries: [string, string][] = [];
  let offset = 0;
  for (const match of block.matchAll(pairs)) {
    if (match.index !== offset || !productFields.has(match[1])) return [];
    const value = match[2].slice(1, -1).replace(
      /\\(?:x([0-9a-f]{2})|u([0-9a-f]{4})|U([0-9a-f]{8})|([\\'"nrt]))/g,
      (escaped, hex, wide, codepoint, character) => {
        if (character) return ({ n: "\n", r: "\r", t: "\t" } as Record<string, string>)[character] ?? character;
        const code = parseInt(hex ?? wide ?? codepoint, 16);
        return code <= 0x10ffff ? String.fromCodePoint(code) : escaped;
      },
    );
    entries.push([match[1], value]);
    offset += match[0].length;
  }
  return block.slice(offset).trim() === "}" ? entries : [];
}

// Render the server's draft format as text and semantic blocks. The export
// remains the original Markdown bound to the user's approval.
export function RemedyDraft({ markdown, facts }: { markdown: string; facts?: Record<string, unknown> }) {
  const entries = facts ? Object.entries(facts).filter(([, value]) => typeof value === "string" && value.trim())
    : embeddedFacts(markdown);
  const factsTitle = /^## Verified product facts\s*$/m.test(markdown) ? "Verified product facts"
    : /^Known user-provided purchase facts:/m.test(markdown) ? "Purchase details you provided" : "";
  const seen = new Set<string>();
  const sections = markdown.trim().split(/^## /m).flatMap((section, index) => {
    const [first, ...rest] = section.trim().split(/\r?\n/);
    const title = index > 0 ? first : "";
    if (entries.length && title === "Verified product facts") return [];
    const lines = (index > 0 || first.startsWith("# ") ? rest : [first, ...rest]).filter(line =>
      !entries.length || !line.startsWith("Known user-provided purchase facts:"));
    const blocks = lines.join("\n").trim().split(/\n\s*\n|\n(?=- \[ \])/).flatMap(block => {
      const text = block.trim();
      const key = text.replace(/\s+/g, " ");
      if (!text || seen.has(key)) return [];
      seen.add(key);
      return [text];
    });
    return blocks.length ? [{ title, blocks }] : [];
  });
  return <article className="panel remedy-draft" aria-label="Remedy draft">
    {factsTitle && entries.length > 0 && <section>
      <h3>{factsTitle}</h3>
      <dl>{entries.map(([key, value]) => <div key={key}><dt>{readableLabel(key)}</dt><dd>{String(value)}</dd></div>)}</dl>
    </section>}
    {sections.map(({ title, blocks }, index) => {
      const checklist = blocks.filter(block => block.startsWith("- [ ] "));
      return <section key={index}>
        {title && <h3>{title}</h3>}
        {blocks.filter(block => !block.startsWith("- [ ] ")).map(block => <p key={block}>{block}</p>)}
        {checklist.length > 0 && <ul>{checklist.map(item => <li key={item}>{item.slice(6)}</li>)}</ul>}
      </section>;
    })}
  </article>;
}
