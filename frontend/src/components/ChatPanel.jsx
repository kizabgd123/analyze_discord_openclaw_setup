import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Bot, User, Sparkles, ChevronDown, ChevronUp, Loader2, Cpu, Globe } from 'lucide-react';

export default function ChatPanel({ isDark, modelInfo }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Zdravo! Ja sam AI Data Asistent za Antigravity sistem. Mogu analizirati multi-agent debate, pretraživati RAG bazu znanja, tumačiti rezultate naučnih studija i proveravati stanje lokalnog LiteRT modela. Šta te zanima?',
      thoughts: [],
      suggestions: [
        'Koji je trenutni status konsenzusa u debati?',
        'Objasni rezultate Ablation studije',
        'Pretraži RAG indeks za JudgeGuard pravila',
      ],
    },
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [provider, setProvider] = useState('auto'); // 'auto', 'litert', 'gemini'
  const [expandedThoughts, setExpandedThoughts] = useState({});

  const textareaRef = useRef(null);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Dynamic textarea height resizing
  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  };

  const toggleThought = (idx) => {
    setExpandedThoughts((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const sendMessage = async (textToSend) => {
    const text = textToSend || input;
    if (!text.trim() || isStreaming) return;

    const userMessage = { role: 'user', content: text };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // Prepare assistant placeholder message
    const assistantIndex = newMessages.length;
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', thoughts: [], suggestions: [] },
    ]);
    setIsStreaming(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: newMessages.slice(-6).map((m) => ({ role: m.role, content: m.content })),
          provider: provider,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP greška: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.replace('data: ', '').trim());
              setMessages((prev) => {
                const updated = [...prev];
                const targetMsg = { ...updated[assistantIndex] };

                if (data.type === 'THOUGHT') {
                  targetMsg.thoughts = [...(targetMsg.thoughts || []), data.content];
                } else if (data.type === 'CONTENT') {
                  targetMsg.content = (targetMsg.content || '') + data.content;
                } else if (data.type === 'SUGGESTION') {
                  targetMsg.suggestions = [...(targetMsg.suggestions || []), data.content];
                } else if (data.type === 'ERROR') {
                  targetMsg.content += `\n\n❌ ${data.content}`;
                }
                updated[assistantIndex] = targetMsg;
                return updated;
              });
            } catch (err) {
              console.error('SSE JSON parsiranje greška:', err, line);
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[assistantIndex] = {
          ...updated[assistantIndex],
          content: `Greška pri komunikaciji: ${err.message}`,
        };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-[700px] bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
      {/* Chat Header */}
      <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between bg-zinc-50 dark:bg-zinc-900/50">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-500" />
          <h3 className="font-bold text-xs uppercase tracking-wider text-zinc-950 dark:text-zinc-50">
            Natural Language Data Analytics Chat
          </h3>
        </div>

        {/* Provider Switcher */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-zinc-400 text-[11px]">Model:</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md px-2 py-1 text-xs text-zinc-700 dark:text-zinc-300 font-medium"
          >
            <option value="auto">Auto (Dual Mode)</option>
            <option value="litert">Lokalni Gemma 2 (Offline)</option>
            <option value="gemini">Gemini Cloud API</option>
          </select>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-5 overflow-y-auto space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          const hasThoughts = msg.thoughts && msg.thoughts.length > 0;
          const isThoughtExpanded = !!expandedThoughts[idx];

          return (
            <div
              key={idx}
              className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-full`}
            >
              {/* Message Header */}
              <div className="flex items-center gap-1.5 mb-1 text-[11px] text-zinc-400">
                {isUser ? (
                  <>
                    <span>Ti</span>
                    <User className="w-3.5 h-3.5" />
                  </>
                ) : (
                  <>
                    <Bot className="w-3.5 h-3.5 text-blue-500" />
                    <span>Antigravity Data Intelligence</span>
                  </>
                )}
              </div>

              {/* Thought Accordion (Segregated Thoughts) */}
              {!isUser && hasThoughts && (
                <div className="mb-2 max-w-2xl w-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 rounded-lg text-xs overflow-hidden">
                  <button
                    onClick={() => toggleThought(idx)}
                    className="w-full px-3 py-1.5 flex items-center justify-between text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
                  >
                    <span className="flex items-center gap-1.5 font-medium text-[11px]">
                      <Sparkles className="w-3 h-3 text-amber-500" />
                      Proces razmišljanja ({msg.thoughts.length} koraka)
                    </span>
                    {isThoughtExpanded ? (
                      <ChevronUp className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                  </button>
                  {isThoughtExpanded && (
                    <div className="p-3 border-t border-zinc-200 dark:border-zinc-800 space-y-1.5 bg-zinc-100/50 dark:bg-zinc-950/50">
                      {msg.thoughts.map((t, tIdx) => (
                        <div key={tIdx} className="text-[11px] text-zinc-600 dark:text-zinc-400 font-mono">
                          • {t}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Message Bubble */}
              <div
                className={`p-4 rounded-xl text-xs leading-relaxed max-w-3xl shadow-sm ${
                  isUser
                    ? 'bg-blue-600 text-white rounded-br-none'
                    : 'bg-zinc-100 dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800 rounded-bl-none'
                }`}
              >
                {isUser ? (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none [&>p]:mb-2 [&>h3]:text-sm [&>h3]:font-bold [&>ul]:list-disc [&>ul]:ml-4">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content || (isStreaming ? 'Analiziram podatke...' : '')}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Interactive Follow-up Suggestions */}
              {!isUser && msg.suggestions && msg.suggestions.length > 0 && !isStreaming && (
                <div className="mt-2.5 flex flex-wrap gap-1.5 max-w-2xl">
                  {msg.suggestions.map((sug, sIdx) => (
                    <button
                      key={sIdx}
                      onClick={() => sendMessage(sug)}
                      className="px-2.5 py-1 rounded-full text-[11px] bg-zinc-100 hover:bg-blue-50 dark:bg-zinc-900 dark:hover:bg-blue-950/40 text-zinc-700 hover:text-blue-600 dark:text-zinc-300 dark:hover:text-blue-400 border border-zinc-200 dark:border-zinc-800 transition-colors"
                    >
                      💡 {sug}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        <div ref={chatBottomRef} />
      </div>

      {/* Multiline Input Toolbar */}
      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/40">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage();
          }}
          className="flex items-end gap-2"
        >
          <div className="flex-1 relative bg-white dark:bg-[#09090b] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-blue-500 shadow-sm">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              onChange={handleInputChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Postavite pitanje o debatama, RAG indeksu ili studijama (Shift+Enter za novi red)..."
              className="w-full p-3 text-xs bg-transparent text-zinc-900 dark:text-zinc-100 focus:outline-none resize-none max-h-[140px]"
            />
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="p-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white transition-colors shadow-sm shrink-0"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
