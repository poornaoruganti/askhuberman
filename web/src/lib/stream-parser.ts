import { StreamEvent } from "@/types/chat";

/**
 * Parses a raw chunk string (which might contain partial JSON or multiple lines)
 * and returns an array of valid parsed events.
 */
export function parseStreamChunk(chunk: string): StreamEvent[] {
  const lines = chunk.split("\n").filter((line) => line.trim() !== "");
  const events: StreamEvent[] = [];

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const jsonStr = line.replace("data: ", "");
      try {
        const parsed = JSON.parse(jsonStr) as StreamEvent;
        events.push(parsed);
      } catch (e) {
        console.error("Failed to parse stream event:", line, e);
      }
    }
  }

  return events;
}