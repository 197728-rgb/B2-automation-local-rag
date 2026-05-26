import mammoth from "mammoth";
import fs from "node:fs";

/** Semantic HTML for Analyst LLM — not authoritative for write coordinates (see Python docx_structure). */
export async function extractDocxSemanticHtml(
  docxPath: string,
  maxChars = 120_000
): Promise<string> {
  const buf = fs.readFileSync(docxPath);
  const result = await mammoth.convertToHtml({ buffer: buf });
  const html = result.value || "";
  return html.length > maxChars ? html.slice(0, maxChars) + "\n<!-- truncated -->" : html;
}
