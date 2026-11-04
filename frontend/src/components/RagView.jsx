import React, { useState } from 'react';
import axios from 'axios';
import { Database, Search, FileText, Clock, ExternalLink, Loader2 } from 'lucide-react';

export default function RagView({ ragData }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  const initialDocs = ragData?.documents || [];

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const resp = await axios.post('/api/rag/search', {
        query: searchQuery.trim(),
        limit: 10,
      });
      if (resp.data.success) {
        setSearchResults(resp.data.data);
      }
    } catch (err) {
      console.error('RAG pretraga greška:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const displayedDocs = searchResults !== null ? searchResults : initialDocs;

  return (
    <div className="space-y-6">
      {/* Top Search Banner */}
      <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0c0c0f] shadow-sm">
        <div className="max-w-2xl">
          <h3 className="text-base font-bold text-zinc-950 dark:text-zinc-50 mb-1">
            Lokalna RAG Baza Znanja (SQLite FTS5)
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-4">
            Pretražite indeksirana sistemska dokumenta, pravila i korpus sa BM25 rangiranjem.
          </p>

          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Unesite termin za pretragu (npr. JudgeGuard, BFRI, model)..."
                className="w-full bg-zinc-50 dark:bg-[#09090b] border border-zinc-200 dark:border-zinc-800 rounded-lg pl-9 pr-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 text-zinc-950 dark:text-zinc-100"
              />
            </div>
            <button
              type="submit"
              disabled={isSearching}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-xs px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors shadow-sm"
            >
              {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
              <span>Pretraži</span>
            </button>
            {searchResults !== null && (
              <button
                type="button"
                onClick={() => {
                  setSearchResults(null);
                  setSearchQuery('');
                }}
                className="bg-zinc-200 dark:bg-zinc-800 hover:bg-zinc-300 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 text-xs px-3 py-2 rounded-lg transition-colors"
              >
                Poništi
              </button>
            )}
          </form>
        </div>
      </div>

      {/* Document Explorer Table */}
      <div className="bg-white dark:bg-[#0c0c0f] border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-500" />
            <h4 className="font-bold text-xs uppercase tracking-wider text-zinc-950 dark:text-zinc-50">
              {searchResults !== null
                ? `Rezultati Pretrage (${searchResults.length})`
                : `Indeksirani Dokumenti (${ragData?.total_chunks || 0})`}
            </h4>
          </div>
          <span className="text-[11px] font-mono text-zinc-400">
            {ragData?.db_path ? `DB: ${ragData.db_path.split('/').pop()}` : ''}
          </span>
        </div>

        <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {displayedDocs.length === 0 ? (
            <div className="py-12 text-center text-xs text-zinc-400">
              Nema pronađenih dokumenata.
            </div>
          ) : (
            displayedDocs.map((doc, idx) => (
              <div key={doc.id || idx} className="p-4 hover:bg-zinc-50 dark:hover:bg-zinc-850 transition-colors">
                <div className="flex items-baseline justify-between mb-1.5">
                  <div className="font-semibold text-xs text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                    <span>{doc.title || `Dokument #${doc.id}`}</span>
                    {doc.source && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
                        {doc.source}
                      </span>
                    )}
                  </div>
                  {doc.created_at && (
                    <div className="text-[10px] text-zinc-400 font-mono flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>{doc.created_at.slice(0, 16)}</span>
                    </div>
                  )}
                </div>
                <p className="text-xs text-zinc-600 dark:text-zinc-300 leading-relaxed font-mono text-[11px] line-clamp-3">
                  {doc.body}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
