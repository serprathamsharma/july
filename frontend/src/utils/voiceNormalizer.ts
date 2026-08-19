/**
 * Voice Query Normalizer
 * Collapses spelled-out letters (e.g. 'm s m a r c o' -> 'MSMARCO'),
 * normalizes domain acronyms, Roman numerals, and common STT misspellings.
 */
export function normalizeVoiceQuery(text: string): string {
  if (!text) return '';

  let normalized = text.trim();

  // 1. Collapse spelled-out sequences of single letters: "m s m a r c o" -> "msmarco", "f a i s s" -> "faiss"
  normalized = normalized.replace(/\b([a-zA-Z]\s+){2,}[a-zA-Z]\b/gi, (match) => {
    return match.replace(/\s+/g, '');
  });

  // 2. Handle dot-separated letters: "m.s.m.a.r.c.o" -> "msmarco"
  normalized = normalized.replace(/\b([a-zA-Z]\.\s*){2,}[a-zA-Z]\.?/gi, (match) => {
    return match.replace(/[\.\s]+/g, '');
  });

  // 3. Domain-specific acronym and phrase normalization
  normalized = normalized
    .replace(/\bm\s*s\s*marco\b/gi, 'MSMARCO')
    .replace(/\bmsmarco\s*(11|eleven|xi)\b/gi, 'MSMARCO-XI')
    .replace(/\bmsmarco\s*(1|one|i)\b/gi, 'MSMARCO-XI')
    .replace(/\bf\s*a\s*i\s*s\s*s\b/gi, 'FAISS')
    .replace(/\bb\s*m\s*25\b/gi, 'BM25')
    .replace(/\bb\s*m\s*twenty\s*five\b/gi, 'BM25')
    .replace(/\br\s*r\s*f\b/gi, 'RRF')
    .replace(/\br\s*a\s*g\b/gi, 'RAG')
    .replace(/\bv\s*a\s*s\s*t\b/gi, 'VAST')
    .replace(/\bs\s*a\s*r\s*v\s*a\s*m\b/gi, 'Sarvam')
    .replace(/\bp\s*l\s*[riay]\b/gi, 'PLI')
    .replace(/\bplr\b/gi, 'PLI')
    .replace(/\bply\b/gi, 'PLI')
    .replace(/\bdatabse\b/gi, 'database')
    .replace(/\bdatbase\b/gi, 'database')
    .replace(/\bdata\s+base\b/gi, 'database');

  return normalized;
}
