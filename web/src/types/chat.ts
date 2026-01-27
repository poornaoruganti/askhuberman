export type Role = "user" | "model";

//  The structure of a single video source (from your Backend Dict)
export interface VideoMetadata {
  title: string;
  topic?: string; // Optional because sometimes it might be missing
  url: string;
}

//  The efficient Lookup Map: "videoId" -> Metadata
export type CitationMap = Record<string, VideoMetadata>;

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  citations?: CitationMap;
  isStreaming?: boolean; // Stores the flattened map
}

export interface ChatRequest {
  query: string;
  history: Array<{ role: Role; content: string }>;
  top_k?: number;
}

export type StreamEvent =
  | { event: "citation"; data: Array<Record<string, VideoMetadata>> } // List of Dicts
  | { event: "content"; data: string }
  | { event: "error"; data: string };