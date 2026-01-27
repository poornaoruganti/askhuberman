import { Send, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea"; 
import { useState, KeyboardEvent, useRef, useEffect } from "react";

interface ChatInputProps {
  isLoading: boolean;
  onSend: (message: string) => void;
  onStop: () => void;
}

export function ChatInput({ isLoading, onSend, onStop }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input);
    setInput("");
    // Reset height
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative flex items-end gap-2 bg-gray-50 p-2 rounded-3xl border border-gray-200 focus-within:ring-2 focus-within:ring-blue-100 transition-all shadow-sm">
      <Textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a follow-up..."
        //  text-gray-900: Forces typing text to be dark/black
        // placeholder:text-gray-400: Keeps placeholder subtle but readable
        //  bg-transparent: Blends with the container
        className="min-h-[24px] max-h-[120px] py-3 px-4 resize-none bg-transparent border-0 focus-visible:ring-0 shadow-none text-base sm:text-sm text-gray-900 placeholder:text-gray-400"
        rows={1}
      />
      
      {isLoading ? (
        <Button
          onClick={onStop}
          variant="destructive"
          size="icon"
          className="h-10 w-10 rounded-full shrink-0 mb-1"
        >
          <Square className="w-4 h-4 fill-current" />
        </Button>
      ) : (
        <Button
          onClick={handleSend}
          disabled={!input.trim()}
          size="icon"
          className={
             // Dynamic styling: Disabled looks gray, Active looks Black
             input.trim() 
               ? "h-10 w-10 rounded-full shrink-0 mb-1 bg-black hover:bg-gray-800 text-white transition-colors"
               : "h-10 w-10 rounded-full shrink-0 mb-1 bg-gray-200 text-gray-400 cursor-not-allowed"
          }
        >
          <Send className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}