import { useState, useRef } from "react";
import { ChatMessage, ChatRequest, CitationMap, VideoMetadata } from "@/types/chat";
import { parseStreamChunk } from "@/lib/stream-parser";

//flattenCitations helper function
function flattenCitations(rawList: Array<Record<string, VideoMetadata>>): CitationMap {
  const map: CitationMap = {};
  if (!Array.isArray(rawList)) return map;
  rawList.forEach((item) => {
    const keys = Object.keys(item);
    if (keys.length > 0) {
      const videoId = keys[0];
      map[videoId] = item[videoId];
    }
  });
  return map;
}

export function useChatStream({
  apiEndpoint,
  initialMessages = [],
}: {
  apiEndpoint: string;
  initialMessages?: ChatMessage[];
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = async (query: string) => {
    setIsLoading(true);
    abortControllerRef.current = new AbortController();

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: query,
    };

    const aiMessagePlaceholder: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: "model",
      content: "",
      citations: {},
      isStreaming: true, //  Start loading
    };

    setMessages((prev) => [...prev, userMessage, aiMessagePlaceholder]);

    try {
      // Fetch logic
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const payload: ChatRequest = { query, history, top_k: 5 };

      const response = await fetch(apiEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: abortControllerRef.current.signal,
      });

      if (!response.body) throw new Error("ReadableStream not supported.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunkValue = decoder.decode(value, { stream: true });
        const events = parseStreamChunk(chunkValue);

        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMsgIndex = newMessages.length - 1;
          if (lastMsgIndex < 0) return prev;

          const lastMsg = { ...newMessages[lastMsgIndex] };

          events.forEach((event) => {
            if (event.event === "citation") {
              lastMsg.citations = flattenCitations(event.data);
            } else if (event.event === "content") {
              lastMsg.content += event.data;
            } else if (event.event === "error") {
              lastMsg.content += `\n\n[Error: ${event.data}]`;
            }
          });

          newMessages[lastMsgIndex] = lastMsg;
          return newMessages;
        });
      }
    } catch (error: any) {
       // Error handling
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
      
      //  FINAL STEP: Mark the message as finished so the Footer appears
      setMessages((prev) => {
        const newMessages = [...prev];
        const lastMsgIndex = newMessages.length - 1;
        if (lastMsgIndex >= 0) {
           newMessages[lastMsgIndex] = { ...newMessages[lastMsgIndex], isStreaming: false };
        }
        return newMessages;
      });
    }
  };

  const stopGeneration = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
  };

  return { messages, isLoading, sendMessage, stopGeneration };
}