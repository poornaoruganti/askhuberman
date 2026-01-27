import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import { ChatMessage as ChatMessageType, CitationMap } from "@/types/chat";
import { Bot, User, Loader2 } from "lucide-react";
import { ChatCitation } from "./chat-citation";
import { useState, useEffect } from "react";

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * REPLACEMENT LOGIC:
 * Finds [id] and replaces it with [[1]](url).
 * The number corresponds to the citation's order in the list.
 */
function formatContent(content: string, citations?: CitationMap) {
  if (!content || !citations) return content;

  // Get canonical order of IDs to assign numbers 1, 2, 3...
  const citationKeys = Object.keys(citations);

  return content.replace(/\[(.*?)\]/g, (match, capturedInside) => {
    const rawParts = capturedInside.split(",");
    const links: string[] = [];
    let foundAny = false;

    rawParts.forEach((part: string) => {
      const exactId = part.trim();
      const meta = citations[exactId];

      if (meta) {
        foundAny = true;
        // Find index for numbering (1-based)
        const index = citationKeys.indexOf(exactId) + 1;
        const label = index > 0 ? `${index}` : "?"; // Fallback safety
        
        // Markdown Link Format: [[1]](url)
        links.push(`[[${label}]](${meta.url})`);
      } else {
        links.push(exactId);
      }
    });

    if (foundAny) return ` ${links.join(" ")} `; // Space ensures separation
    return match;
  });
}

// "Analyzing..." Animation Component
function AnalyzingIndicator({ citations }: { citations: CitationMap }) {
  const topics = Array.from(new Set(Object.values(citations).map(c => c.topic).filter(Boolean)));
  const [currentTopicIndex, setCurrentTopicIndex] = useState(0);

  useEffect(() => {
    if (topics.length === 0) return;
    const interval = setInterval(() => {
      setCurrentTopicIndex((prev) => (prev + 1) % topics.length);
    }, 1500);
    return () => clearInterval(interval);
  }, [topics.length]);

  const currentTopic = topics[currentTopicIndex] || "Sources";

  return (
    <div className="flex items-center gap-2 text-sm text-gray-400 animate-pulse my-2">
      <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
      <span>Analyzing...</span>
      {currentTopic && (
        <span className="font-medium text-gray-600 bg-gray-100 px-1.5 py-0.5 rounded text-xs">
          {currentTopic}
        </span>
      )}
    </div>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const hasCitations = message.citations && Object.keys(message.citations).length > 0;
  const isAnalyzing = !isUser && hasCitations && !message.content;

  const displayContent = isUser
    ? message.content
    : formatContent(message.content, message.citations);

  return (
    <div className={cn("flex w-full gap-4 py-4", isUser ? "flex-row-reverse" : "flex-row")}>
      <div className={cn("flex items-center justify-center w-8 h-8 rounded-full border shadow-sm shrink-0", isUser ? "bg-gray-100 text-gray-500" : "bg-black text-white")}>
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      <div className={cn("flex flex-col max-w-[85%] sm:max-w-[75%]", isUser ? "items-end" : "items-start")}>
        <div className={cn("text-[15px] leading-relaxed", isUser ? "bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm" : "text-gray-800")}>
          
          {isAnalyzing ? (
            <AnalyzingIndicator citations={message.citations!} />
          ) : isUser ? (
            <div className="whitespace-pre-wrap">{displayContent}</div>
          ) : (
            <ReactMarkdown
              components={{
                a: ({ href, children }) => {
                  const isCitation = !isNaN(Number(children)); // Checks if child is a number like "1"
                  
                  if (isCitation) {
                    return (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center justify-center min-w-[18px] h-[18px] text-[10px] font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-full -translate-y-1 mx-0.5 no-underline border border-blue-200 select-none transition-colors"
                        title="View Source"
                      >
                        {children}
                      </a>
                    );
                  }
                  return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{children}</a>;
                }
              }}
            >
              {displayContent}
            </ReactMarkdown>
          )}
        </div>

        {/* Footer Citations - Only when done streaming */}
        {!isUser && message.citations && !message.isStreaming && (
          <ChatCitation citations={message.citations} />
        )}
      </div>
    </div>
  );
}