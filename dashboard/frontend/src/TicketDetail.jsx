import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowUp, ArrowDown, Terminal, FileCode, ChevronRight, Paperclip, ArrowLeft } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function TicketDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [input, setInput] = useState('');
    const [error, setError] = useState(null);
    const messagesEndRef = useRef(null);
    const [expandedTools, setExpandedTools] = useState({});

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const scrollToTop = () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    useEffect(() => {
        fetchConversation();
        // Poll for updates
        const interval = setInterval(fetchConversation, 3000);
        return () => clearInterval(interval);
    }, [id]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const fetchConversation = async () => {
        try {
            const response = await fetch(`${API_BASE}/api/tickets/${id}/conversation`);
            const data = await response.json();

            if (!response.ok || data.error) {
                const errorMsg = data.error || 'Unknown error';
                console.warn('API Error:', errorMsg);
                setError(errorMsg);
                setLoading(false);
                return;
            }

            if (Array.isArray(data)) {
                setError(null); // Clear error if successful
                // Only update if data changed (simple check)
                if (JSON.stringify(data) !== JSON.stringify(messages)) {
                    setMessages(data);
                    setLoading(false);
                }
            } else {
                console.warn('Received non-array data:', data);
                setLoading(false);
            }
        } catch (error) {
            console.error('Error fetching conversation:', error);
            setError(error.message);
            setLoading(false);
        }
    };

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        // Optimistic update
        const newMessage = {
            role: 'user_response',
            content: input,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        setMessages(prev => [...prev, newMessage]);
        setInput('');

        // TODO: Send to backend API when ready
        // await fetch(`${API_BASE}/api/tickets/${id}/message`, { method: 'POST', body: JSON.stringify({ content: input }) });
    };

    const toggleTool = (index) => {
        setExpandedTools(prev => ({
            ...prev,
            [index]: !prev[index]
        }));
    };

    if (loading && messages.length === 0) {
        return (
            <div className="min-h-screen bg-[#050505] flex items-center justify-center text-emerald-500 font-mono">
                <div className="animate-pulse">Initializing Terminal Link...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-[#050505] flex items-center justify-center text-red-500 font-mono p-4 text-center">
                <div>
                    <h2 className="text-xl font-bold mb-2">Connection Error</h2>
                    <p className="text-red-400/80">{error}</p>
                    <button
                        onClick={() => navigate('/')}
                        className="mt-6 px-4 py-2 bg-red-900/20 border border-red-900/50 rounded hover:bg-red-900/40 transition"
                    >
                        Return to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#050505] text-[#e4e4e7] font-mono selection:bg-emerald-900 selection:text-white flex flex-col">

            {/* Navigation Shortcuts */}
            <div className="fixed top-6 right-6 flex flex-col gap-3 z-50">
                <button onClick={() => navigate('/')}
                    className="p-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-full shadow-xl text-emerald-500 hover:text-emerald-400 transition duration-200 group mb-4"
                    title="Back to Dashboard">
                    <ArrowLeft className="group-hover:-translate-x-0.5 transition-transform" />
                </button>
                <button onClick={scrollToTop}
                    className="p-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-full shadow-xl text-emerald-500 hover:text-emerald-400 transition duration-200 group">
                    <ArrowUp className="group-hover:-translate-y-0.5 transition-transform" />
                </button>
                <button onClick={scrollToBottom}
                    className="p-3 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-full shadow-xl text-emerald-500 hover:text-emerald-400 transition duration-200 group">
                    <ArrowDown className="group-hover:translate-y-0.5 transition-transform" />
                </button>
            </div>

            {/* Main Feed */}
            <main className="flex-1 overflow-y-auto px-4 py-12 pb-64 w-full max-w-4xl mx-auto scroll-smooth">
                {messages.map((block, index) => (
                    <div key={index} className="w-full mb-6 animate-fade-in flex flex-col" style={{ animationDelay: `${index * 0.05}s` }}>

                        {/* Agent Question */}
                        {block.role === 'agent_question' && (
                            <div className="self-start max-w-2xl group">
                                <div className="bg-[#0c0c0c] border border-emerald-900/50 rounded-lg p-6 shadow-sm relative">
                                    <div className="absolute -top-3 -left-0 bg-[#050505] border border-emerald-800 text-emerald-500 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                                        Agent Question
                                    </div>
                                    <p className="text-emerald-100/90 text-base leading-7 font-sans whitespace-pre-wrap">{block.content}</p>
                                </div>
                            </div>
                        )}

                        {/* User Response */}
                        {block.role === 'user_response' && (
                            <div className="self-end max-w-xl mt-2">
                                <div className="bg-emerald-950/30 border border-emerald-500/30 text-emerald-50 rounded-lg p-5 relative shadow-md">
                                    <div className="absolute -top-3 -right-0 bg-[#050505] border border-emerald-500/30 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
                                        YOU
                                    </div>
                                    <div className="flex gap-3">
                                        <span className="text-emerald-600 select-none">$</span>
                                        <p className="font-mono text-base leading-relaxed text-emerald-100 whitespace-pre-wrap">{block.content}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Tool Call */}
                        {(block.role === 'tool_call' || block.role === 'agent_action') && (
                            <div className="self-start w-full max-w-3xl mt-3">
                                <div className="bg-[#0a0a0a] border border-zinc-800 rounded overflow-hidden">
                                    <button
                                        onClick={() => toggleTool(index)}
                                        className="w-full flex items-center justify-between p-3 hover:bg-zinc-900 transition cursor-pointer text-left group border-l-2 border-emerald-600/50"
                                    >
                                        <div className="flex items-center gap-3">
                                            {block.output_type === 'terminal' ?
                                                <Terminal className="text-emerald-600 w-4 h-4" /> :
                                                <FileCode className="text-emerald-600 w-4 h-4" />
                                            }
                                            <span className="font-mono text-sm text-zinc-400 font-medium group-hover:text-emerald-100 transition">
                                                {block.title || `Running ${block.tool_name}`}
                                            </span>
                                        </div>
                                        <ChevronRight
                                            className={`text-zinc-600 w-4 h-4 transition-transform duration-200 ${expandedTools[index] ? 'rotate-90' : ''}`}
                                        />
                                    </button>

                                    {expandedTools[index] && (
                                        <div className="border-t border-zinc-800 bg-black">
                                            <div className="p-4 overflow-x-auto custom-scrollbar">
                                                <pre className="text-xs font-mono text-zinc-400 leading-relaxed"><code>{block.content}</code></pre>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </main>

            {/* Floating Input */}
            <div className="fixed bottom-0 left-0 w-full px-4 pb-8 pt-12 bg-gradient-to-t from-[#050505] via-[#050505] to-transparent z-40 flex justify-center pointer-events-none">
                <div className="w-full max-w-3xl pointer-events-auto">
                    <div className="bg-[#0a0a0a]/95 backdrop-blur-xl border border-zinc-800 shadow-2xl rounded-lg overflow-hidden input-glow transition-all duration-300 focus-within:border-emerald-500 focus-within:shadow-[0_0_0_1px_rgba(16,185,129,0.4)]">
                        <form onSubmit={handleSend} className="flex flex-col">

                            {/* Meta Bar */}
                            <div className="px-4 py-2 bg-black/40 border-b border-white/5 flex justify-between items-center">
                                <div className="flex items-center gap-2 text-xs font-bold text-emerald-600 uppercase tracking-widest">
                                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                                    <span>System Active</span>
                                </div>
                                <span className="text-xs font-mono text-zinc-600">v2.4.0</span>
                            </div>

                            {/* Input */}
                            <textarea
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSend(e);
                                    }
                                }}
                                className="w-full p-4 h-20 bg-[#0a0a0a] text-emerald-100 placeholder:text-zinc-700 border-none outline-none resize-none text-base font-mono"
                                placeholder="Input command or prompt..."
                            />

                            {/* Actions */}
                            <div className="flex justify-between items-center px-3 pb-3 pt-1 bg-[#0a0a0a]">
                                <div className="flex gap-1">
                                    <button type="button" className="p-2 hover:bg-zinc-900 rounded text-zinc-600 hover:text-emerald-500 transition">
                                        <Paperclip width={18} />
                                    </button>
                                </div>

                                <button type="submit" className="bg-emerald-700 hover:bg-emerald-600 text-white px-6 py-2 rounded text-sm font-bold tracking-wide shadow-lg shadow-emerald-900/20 transition-all flex items-center gap-2 uppercase">
                                    <span>Execute</span>
                                    <Terminal width={14} className="fill-current" />
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default TicketDetail;
