import fs from "node:fs";
import path from "node:path";

const EXT = new Set([".txt", ".md", ".json", ".pdf", ".docx", ".csv", ".log"]);

export function loadSourceDocumentsContext(sourceFolder: string, maxChars = 200_000): string {
  const root = path.resolve(sourceFolder);
  if (!fs.existsSync(root)) {
    return "";
  }
  const parts: string[] = [];
  let total = 0;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (!entry.isFile()) continue;
    const ext = path.extname(entry.name).toLowerCase();
    if (!EXT.has(ext)) continue;
    const full = path.join(root, entry.name);
    let text = "";
    if (ext === ".pdf") {
      text = `[PDF file: ${entry.name} — extract via Python b2 run-autonomous for full PDF text]`;
    } else {
      try {
        text = fs.readFileSync(full, "utf8");
      } catch {
        text = `[binary or unreadable: ${entry.name}]`;
      }
    }
    const chunk = `--- FILE: ${entry.name} ---\n${text}\n`;
    if (total + chunk.length > maxChars) break;
    parts.push(chunk);
    total += chunk.length;
  }
  return parts.join("\n");
}
