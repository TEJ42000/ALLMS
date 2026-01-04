# RAG Architecture Design Document

## Overview

This document compares approaches for implementing document-based AI features (study guides, quizzes, article explanations) in the LLS Study Portal. The goal is to enable **powerful semantic search** while maintaining **LLM provider flexibility**.

## Current State: Anthropic Files API

### How It Works
```
PDFs → Upload to Anthropic → file_ids.json → Reference in API calls → Claude processes
```

### Pros
| Advantage | Description |
|-----------|-------------|
| Simple implementation | Already built, just needs file upload |
| Automatic caching | 90% cost reduction via prompt caching |
| Built-in citations | Source references included |
| No infrastructure | No vector DB to manage |
| Full document context | No chunking issues |

### Cons
| Limitation | Impact |
|------------|--------|
| **Vendor lock-in** | Cannot use Gemini, GPT-4, or other LLMs |
| **No semantic search** | Entire documents sent to context window |
| **Beta API** | `files-api-2025-04-14` may change |
| **Context limits** | Large documents may exceed limits |
| **Storage costs** | Files stored in Anthropic's infrastructure |

---

## Alternative 1: RAG with Vector Database (Recommended)

### How It Works
```
PDFs → Chunk → Embed → Vector DB → Query → Retrieve relevant chunks → Any LLM
```

### Architecture
```
┌────────────────────────────────────────────────────────────────┐
│                     Document Processing                         │
├────────────────────────────────────────────────────────────────┤
│  PDF → Text Extract → Chunk (512 tokens, 50 overlap) → Embed   │
│                              ↓                                  │
│                    Vector Store (ChromaDB)                      │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                     Query Processing                            │
├────────────────────────────────────────────────────────────────┤
│  User Query → Embed → Similarity Search → Top-K Chunks          │
│                              ↓                                  │
│              Context + Query → LLM (Any Provider)               │
└────────────────────────────────────────────────────────────────┘
```

### Pros
| Advantage | Description |
|-----------|-------------|
| **LLM-agnostic** | Use Claude, Gemini, GPT-4, or open-source |
| **Semantic search** | Find relevant content, not just keywords |
| **Scalable** | Handle thousands of documents |
| **Cost efficient** | Only relevant chunks sent to LLM |
| **Industry standard** | Well-documented patterns and libraries |

### Cons
| Limitation | Mitigation |
|------------|------------|
| More complex | Use established libraries (LangChain, ChromaDB) |
| Chunking can lose context | Use overlapping chunks + parent retrieval |
| Requires embedding costs | Vertex AI has free tier; cache embeddings |
| Infrastructure needed | ChromaDB can be embedded (no separate DB) |

### Technology Choices

| Component | Recommended | Alternatives |
|-----------|-------------|--------------|
| Vector DB | **ChromaDB** (embedded, simple) | Vertex AI Vector Search (managed) |
| Embeddings | **Vertex AI text-embedding-004** | OpenAI, Cohere, local models |
| PDF Processing | **pypdf + pdfplumber** | unstructured, PyMuPDF |
| Framework | **Direct implementation** | LangChain (more overhead) |

---

## Alternative 2: Vertex AI RAG Engine

### How It Works
- Fully managed RAG service from Google Cloud
- Handles chunking, embedding, retrieval automatically
- Native Gemini integration

### Pros
| Advantage | Description |
|-----------|-------------|
| Fully managed | No vector DB infrastructure |
| Google Cloud native | Already on GCP (Cloud Run) |
| Multi-source support | GCS, BigQuery, Google Drive |
| Built-in security | IAM integration |

### Cons
| Limitation | Impact |
|------------|--------|
| Google lock-in | May not work well with Claude |
| New service | Less community knowledge |
| Pricing | May be more expensive at scale |

---

## Alternative 3: Gemini Long Context (1M tokens)

### How It Works
- Upload entire documents to Gemini context
- Use context caching for cost reduction
- Similar to Anthropic Files API but for Gemini

### Pros
| Advantage | Description |
|-----------|-------------|
| Massive context | Up to 1M tokens |
| Simple | No chunking or vector DB |
| Context caching | Cost savings for repeated queries |

### Cons
| Limitation | Impact |
|------------|--------|
| Gemini only | No Claude, GPT-4 |
| Latency | Large context = slower |
| Cost | Charged per token in context |

---

## Comparison Matrix

| Criteria | Anthropic Files | RAG + Vector DB | Vertex RAG Engine | Gemini Long Context |
|----------|-----------------|-----------------|-------------------|---------------------|
| **LLM Flexibility** | ❌ Claude only | ✅ Any LLM | ⚠️ Gemini preferred | ❌ Gemini only |
| **Semantic Search** | ❌ None | ✅ Excellent | ✅ Built-in | ⚠️ In-context |
| **Setup Complexity** | ✅ Simple | ⚠️ Medium | ✅ Managed | ✅ Simple |
| **GCP Integration** | ⚠️ Separate | ✅ Good | ✅ Native | ✅ Native |
| **Cost at Scale** | ⚠️ Context-based | ✅ Efficient | ⚠️ Varies | ⚠️ Context-based |
| **Maintenance** | ✅ Low | ⚠️ Medium | ✅ Low | ✅ Low |

---

## Recommendation

### For This Project: RAG with Vector Database

**Rationale:**
1. **LLM flexibility** is a core requirement (support Claude + Gemini per issue #17)
2. **Semantic search** provides better study guide quality
3. **ChromaDB** is lightweight and can be embedded (no separate infra)
4. **Vertex AI embeddings** integrate well with existing GCP setup
5. **Future-proof** for adding more LLMs or switching providers

### Implementation Priority

1. **Phase 1 (Now)**: Fix Files API to unblock (#19, #7) - ~1 day
2. **Phase 2 (Next)**: Build LLM abstraction layer - ~2-3 days  
3. **Phase 3**: Add ChromaDB + retrieval - ~3-4 days
4. **Phase 4**: Migrate features to RAG - ~2-3 days
5. **Phase 5**: Add Gemini support (#17) - ~1-2 days

### Related Issues
- #7 - Upload course materials (short-term fix)
- #17 - Vertex AI / Gemini integration
- #19 - Study Guide Generator not working
- #24 - RAG Architecture implementation plan

---

*Document created: 2026-01-04*
*Last updated: 2026-01-04*

