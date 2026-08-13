import re
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    document_id: str
    chunk_id: str
    chunk_type: str  # sentence | paragraph | semantic
    language: str = "en"
    position: int
    parent_document: str
    text: str
    sentence_count: Optional[int] = 1
    word_count: Optional[int] = 0

class VASTChunker:
    """
    Variable Adaptive Semantic Text Chunking (VAST)
    Supports Sentence, Paragraph, and Semantic Sliding window representations
    preserving document provenance.
    """
    def __init__(self, target_semantic_words: int = 150, overlap_words: int = 30):
        self.target_words = target_semantic_words
        self.overlap_words = overlap_words

    def _split_into_sentences(self, text: str) -> List[str]:
        # Clean up whitespace
        clean_text = re.sub(r'\s+', ' ', text).strip()
        if not clean_text:
            return []
        # Split on sentence boundaries (. ! ?) while keeping context
        sentences = re.split(r'(?<=[.!?])\s+', clean_text)
        return [s.strip() for s in sentences if s.strip()]

    def _split_into_paragraphs(self, text: str) -> List[str]:
        # Split on double newlines or paragraph breaks
        raw_paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [re.sub(r'\s+', ' ', p).strip() for p in raw_paragraphs]
        return [p for p in paragraphs if p]

    def create_sentence_chunks(self, document_id: str, text: str, language: str = "en") -> List[ChunkMetadata]:
        sentences = self._split_into_sentences(text)
        chunks = []
        for idx, sentence in enumerate(sentences):
            c_id = f"{document_id}_sent_{idx}"
            chunks.append(ChunkMetadata(
                document_id=document_id,
                chunk_id=c_id,
                chunk_type="sentence",
                language=language,
                position=idx,
                parent_document=text,
                text=sentence,
                sentence_count=1,
                word_count=len(sentence.split())
            ))
        return chunks

    def create_paragraph_chunks(self, document_id: str, text: str, language: str = "en") -> List[ChunkMetadata]:
        paragraphs = self._split_into_paragraphs(text)
        if not paragraphs:
            paragraphs = [text.strip()]
            
        chunks = []
        for idx, para in enumerate(paragraphs):
            c_id = f"{document_id}_para_{idx}"
            sents = self._split_into_sentences(para)
            chunks.append(ChunkMetadata(
                document_id=document_id,
                chunk_id=c_id,
                chunk_type="paragraph",
                language=language,
                position=idx,
                parent_document=text,
                text=para,
                sentence_count=len(sents),
                word_count=len(para.split())
            ))
        return chunks

    def create_semantic_chunks(self, document_id: str, text: str, language: str = "en") -> List[ChunkMetadata]:
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_chunk_sents = []
        current_word_count = 0
        chunk_idx = 0

        for sent in sentences:
            words = sent.split()
            sent_word_count = len(words)

            current_chunk_sents.append(sent)
            current_word_count += sent_word_count

            if current_word_count >= self.target_words:
                chunk_text = " ".join(current_chunk_sents)
                c_id = f"{document_id}_sem_{chunk_idx}"
                chunks.append(ChunkMetadata(
                    document_id=document_id,
                    chunk_id=c_id,
                    chunk_type="semantic",
                    language=language,
                    position=chunk_idx,
                    parent_document=text,
                    text=chunk_text,
                    sentence_count=len(current_chunk_sents),
                    word_count=current_word_count
                ))
                chunk_idx += 1

                # Sliding overlap calculation
                overlap_sents = []
                overlap_count = 0
                for s in reversed(current_chunk_sents):
                    w_cnt = len(s.split())
                    if overlap_count + w_cnt <= self.overlap_words:
                        overlap_sents.insert(0, s)
                        overlap_count += w_cnt
                    else:
                        break

                current_chunk_sents = overlap_sents
                current_word_count = overlap_count

        # Append remaining sentence group
        if current_chunk_sents and (not chunks or current_word_count > 10):
            chunk_text = " ".join(current_chunk_sents)
            c_id = f"{document_id}_sem_{chunk_idx}"
            chunks.append(ChunkMetadata(
                document_id=document_id,
                chunk_id=c_id,
                chunk_type="semantic",
                language=language,
                position=chunk_idx,
                parent_document=text,
                text=chunk_text,
                sentence_count=len(current_chunk_sents),
                word_count=current_word_count
            ))

        return chunks

    def process_document(self, document_id: str, text: str, language: str = "en") -> Dict[str, List[ChunkMetadata]]:
        """
        Generates all 3 chunk representations (sentence, paragraph, semantic) for a document.
        """
        sentence_chunks = self.create_sentence_chunks(document_id, text, language)
        paragraph_chunks = self.create_paragraph_chunks(document_id, text, language)
        semantic_chunks = self.create_semantic_chunks(document_id, text, language)

        return {
            "sentence": sentence_chunks,
            "paragraph": paragraph_chunks,
            "semantic": semantic_chunks,
            "all": sentence_chunks + paragraph_chunks + semantic_chunks
        }
