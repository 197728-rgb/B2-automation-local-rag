import "dotenv/config";
import { GoogleGenAI } from "@google/genai";

export class LlmClient {
  private ai: GoogleGenAI;
  private defaultModel: string;

  constructor() {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY is not set");
    }
    this.ai = new GoogleGenAI({ apiKey });
    this.defaultModel = process.env.GEMINI_MODEL || "gemini-2.5-pro";
  }

  async generateStructuredJson<T>(
    prompt: string,
    jsonSchema: Record<string, unknown>,
    temperature = 0.1
  ): Promise<T> {
    const response = await this.ai.models.generateContent({
      model: this.defaultModel,
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: jsonSchema,
        temperature,
      },
    });
    if (!response.text) {
      throw new Error("Empty response returned from Gemini.");
    }
    return JSON.parse(response.text) as T;
  }
}
