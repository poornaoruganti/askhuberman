import { ExternalLink } from "lucide-react";
import { CitationMap } from "@/types/chat";

interface ChatCitationProps {
  citations: CitationMap;
}

export function ChatCitation({ citations }: ChatCitationProps) {
  const items = Object.values(citations || {});
  if (items.length === 0) return null;

  return (
    <div className="mt-4 pt-3 border-t border-gray-100 animate-in fade-in duration-500 w-full">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Sources
        </h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {items.map((meta, index) => (
          <a
            key={index}
            href={meta.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex flex-col p-2.5 rounded-lg border border-gray-100 bg-gray-50/50 hover:bg-white hover:border-blue-200 hover:shadow-sm transition-all text-left decoration-transparent"
          >
            <div className="flex items-start gap-2">
              {/* The Number [1] */}
              <span className="flex-shrink-0 flex items-center justify-center w-5 h-5 rounded-full bg-gray-200 text-[10px] font-bold text-gray-600 group-hover:bg-blue-100 group-hover:text-blue-600 transition-colors">
                {index + 1}
              </span>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1">
                   <h4 className="text-xs font-medium text-gray-700 truncate group-hover:text-blue-700 transition-colors">
                     {meta.title}
                   </h4>
                   <ExternalLink className="w-3 h-3 text-gray-300 group-hover:text-blue-400 shrink-0" />
                </div>
                <p className="text-[10px] text-gray-400 truncate mt-0.5">
                  {meta.topic || new URL(meta.url).hostname}
                </p>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}