import "dotenv/config";

export const config = {
  llmProvider: (process.env.LLM_PROVIDER || "google").toLowerCase(),
  geminiApiKey: process.env.GEMINI_API_KEY || "",
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || "",
  geminiModel: process.env.GEMINI_MODEL || "gemini-2.5-pro",
};
