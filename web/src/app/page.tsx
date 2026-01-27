"use client";

import { useEffect, useRef } from "react";
import { useChatStream } from "@/hooks/use-chat-stream";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatInput } from "@/components/chat/chat-input";



export default function Home() {
  const { messages, isLoading, sendMessage, stopGeneration } = useChatStream({
  apiEndpoint: "https://huberman.azurewebsites.net/api/v1/chat",
});

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom only if we are already near the bottom 
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading]);

  return (
    // h-[100dvh] fixes mobile scrolling issues (Safari/Chrome address bar)
    <main className="flex flex-col h-[100dvh] bg-white overflow-hidden">
      
      {/* Header - Fixed Height */}
      <header className="flex-none p-4 border-b bg-white/80 backdrop-blur-md z-10 flex items-center justify-between shadow-sm">
        <h1 className="text-lg font-bold text-gray-800">Ask Huberman</h1>
      </header>

      {/* Chat Area - Takes all remaining space and scrolls internally */}
      <div className="flex-1 overflow-y-auto p-4 scroll-smooth">
        <div className="max-w-3xl mx-auto space-y-6 pb-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-[50vh] text-center text-gray-400">
              <p className="text-lg font-medium">Ready to assist.</p>
              <p className="text-sm">Ask me anything about the video content.</p>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          
          {/* Invisible anchor for auto-scrolling */}
          <div ref={scrollRef} className="h-1" />
        </div>
      </div>

      {/* Input Area - Fixed at bottom */}
      <div className="flex-none bg-white border-t p-3 sm:p-4">
        <div className="max-w-3xl mx-auto">
          <ChatInput 
            isLoading={isLoading} 
            onSend={sendMessage} 
            onStop={stopGeneration} 
          />
        </div>
      </div>
    </main>
  );
}