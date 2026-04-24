// Minimal Markdown → HTML converter for our article subset.
// Supports: #/##/### headings, paragraphs, **bold**, [text](url), - lists,
// > blockquotes, --- hr, and GitHub-style tables.
export function mdToHtml(md: string): string {
  const lines = md.split("\n");
  const out: string[] = [];

  const esc = (s: string): string =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const inline = (raw: string): string => {
    let s = esc(raw);
    s = s.replace(
      /\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    );
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    return s;
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // Table: a line starting with "|" followed by a separator row
    if (
      line.startsWith("|") &&
      i + 1 < lines.length &&
      /^\|[-:\s|]+\|$/.test(lines[i + 1])
    ) {
      const headers = line
        .split("|")
        .slice(1, -1)
        .map((s) => s.trim());
      out.push(
        '<div class="md-table-wrap"><table class="md-table"><thead><tr>' +
          headers.map((h) => `<th>${inline(h)}</th>`).join("") +
          "</tr></thead><tbody>",
      );
      i += 2;
      while (i < lines.length && lines[i].startsWith("|")) {
        const cells = lines[i]
          .split("|")
          .slice(1, -1)
          .map((s) => s.trim());
        out.push(
          "<tr>" +
            cells.map((c) => `<td>${inline(c)}</td>`).join("") +
            "</tr>",
        );
        i++;
      }
      out.push("</tbody></table></div>");
      continue;
    }

    // Unordered list
    if (line.startsWith("- ")) {
      const items: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        items.push(`<li>${inline(lines[i].slice(2))}</li>`);
        i++;
      }
      out.push("<ul>" + items.join("") + "</ul>");
      continue;
    }

    // Blockquote (supports consecutive lines)
    if (line.startsWith("> ")) {
      const parts: string[] = [];
      while (i < lines.length && lines[i].startsWith("> ")) {
        parts.push(inline(lines[i].slice(2)));
        i++;
      }
      out.push(`<blockquote>${parts.join("<br>")}</blockquote>`);
      continue;
    }

    if (line.startsWith("### ")) out.push(`<h3>${inline(line.slice(4))}</h3>`);
    else if (line.startsWith("## ")) out.push(`<h2>${inline(line.slice(3))}</h2>`);
    else if (line.startsWith("# ")) out.push(`<h1>${inline(line.slice(2))}</h1>`);
    else if (line.trim() === "---") out.push("<hr />");
    else if (line.trim() === "") {
      // skip blank line
    } else {
      out.push(`<p>${inline(line)}</p>`);
    }
    i++;
  }

  return out.join("\n");
}
