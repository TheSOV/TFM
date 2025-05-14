from pathlib import Path
from typing import List, Tuple, Optional
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import torch
import torch.nn.functional as F
from typing import List, Tuple
import logging
from sentence_transformers import SentenceTransformer
import ast

class LateChunkingHelper:
    """
    Helper that:
      1. Splits Markdown into late-chunkable blocks
      2. Rebuilds a canonical document & token-level spans
      3. Exposes three encoders with Jina-v3 task-LoRAs
    """

    def __init__(
        self,
        model_name: str = "jinaai/jina-embeddings-v3",
        headers_to_split_on: Optional[List[Tuple[str, str]]] = None,
        max_chunk_chars: int = 2048,
        device: str = "cpu",
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized LateChunkingHelper: device=%s, max_chunk_chars=%d", device, max_chunk_chars)

        # header levels
        if isinstance(headers_to_split_on, str):
            headers_to_split_on = ast.literal_eval(headers_to_split_on)
        elif headers_to_split_on is None:
            headers_to_split_on = [("#", "h1"), ("##", "h2")] # default to h1 & h2

        self.headers_to_split_on = headers_to_split_on
        self.max_chunk_chars = max_chunk_chars
        self.device = device

        # ------------- LoRA-mounted encoders -------------
        self.model = SentenceTransformer(
            model_name,
            trust_remote_code=True,
            device=self.device
        )

        # ------------- tokenizer (CPU) -------------
        self.tokenizer = self.model.tokenizer

    def _md_chunking(
        self,
        path: str,
    ) -> Tuple[List[dict], str]:
        """
        Returns (documents, canonical_doc).

        • documents …… List[dict] whose .metadata contains:
            - filename
            - chunk (k / K)
            - subchunk (j / J in that header chunk)
            - char_span (c0, c1)
            - token_span (t0, t1)

        • token_spans … Parallel list for convenience.
        • canonical_doc … The exact text the spans were computed on.
        """
        raw_md = Path(path).read_text(encoding="utf-8")
        
        # header-aware primary split
        hdr_split = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False,                          # keep header lines
        )
        header_docs = hdr_split.split_text(raw_md)

        # size guard
        char_split = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chunk_chars,
            chunk_overlap=0,                 # 0 → no overlap here
        )

        chunk_texts, hdr_index = [], []                  # keep header id for subchunk count
        for h_id, h_doc in enumerate(header_docs, 1):
            sub_docs = (
                char_split.split_documents([h_doc])
                if len(h_doc.page_content) > self.max_chunk_chars
                else [h_doc]
            )
            chunk_texts.extend(x.page_content for x in sub_docs)
            hdr_index.extend([(h_id, j + 1, len(sub_docs)) for j in range(len(sub_docs))])

        # canonical doc
        SEP = "\u2043\n"                                 # rare separator
        canonical_doc = SEP.join(chunk_texts)

        # global tokenisation with offsets
        enc = self.tokenizer(
            canonical_doc,
            add_special_tokens=False,
            return_offsets_mapping=True,
        )
        offsets = enc["offset_mapping"]
        n_tokens = len(offsets)

        # compute spans & build LangChain documents
        docs: List[dict] = []
        c_cursor = 0
        t_cursor = 0
        K = len(chunk_texts)

        for k, txt in enumerate(chunk_texts, 1):
            c0 = canonical_doc.find(txt, c_cursor)
            c1 = c0 + len(txt)
            c_cursor = c1

            while t_cursor < n_tokens and offsets[t_cursor][1] <= c0:
                t_cursor += 1
            t0 = t_cursor
            while t_cursor < n_tokens and offsets[t_cursor][0] < c1:
                t_cursor += 1
            t1 = t_cursor

            header_id, j, J = hdr_index[k - 1]
            late_chunking_metadata = {
                "char_span": (c0, c1),
                "token_span": (t0, t1),
            }
            docs.append({
                "content": txt,
                "filename": path,
                "chunk": f"{k}/{K}",
                "subchunk": f"{j}/{J}",
                "late_chunking_metadata": late_chunking_metadata,
            })

        return docs, canonical_doc

    def _generic_chunking(
        self,
        path: str,
    ) -> Tuple[List[dict], str]:
        """
        Splits a generic text file using RecursiveCharacterTextSplitter only.
        Returns (documents, canonical_doc).
        """
        raw_txt = Path(path).read_text(encoding="utf-8")

        # Split using only the recursive splitter
        char_split = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chunk_chars,
            chunk_overlap=0,
        )
        sub_docs = char_split.split_text(raw_txt)
        chunk_texts = [d for d in sub_docs]
        K = len(chunk_texts)

        SEP = "\u2043\n"
        canonical_doc = SEP.join(chunk_texts)
        enc = self.tokenizer(
            canonical_doc,
            add_special_tokens=False,
            return_offsets_mapping=True,
        )
        offsets = enc["offset_mapping"]
        n_tokens = len(offsets)

        docs: List[dict] = []
        c_cursor = 0
        t_cursor = 0

        for k, txt in enumerate(chunk_texts, 1):
            c0 = canonical_doc.find(txt, c_cursor)
            c1 = c0 + len(txt)
            c_cursor = c1
            while t_cursor < n_tokens and offsets[t_cursor][1] <= c0:
                t_cursor += 1
            t0 = t_cursor
            while t_cursor < n_tokens and offsets[t_cursor][0] < c1:
                t_cursor += 1
            t1 = t_cursor
            late_chunking_metadata = {
                "char_span": (c0, c1),
                "token_span": (t0, t1),
            }
            docs.append({
                "content": txt,
                "filename": path,
                "chunk": f"{k}/{K}",
                "subchunk": "1/1",
                "late_chunking_metadata": late_chunking_metadata,
            })
        return docs, canonical_doc

    def _yaml_chunking(
        self,
        path: str,
        summary: str = "",
    ) -> Tuple[List[dict], str]:
        """
        For YAML files: prepends a summary as a comment, does NOT split, returns one chunk.
        Returns (documents, canonical_doc).
        """
        raw_txt = Path(path).read_text(encoding="utf-8")
        summary_comment = f"# {summary.strip()}\n" if summary.strip() else ""
        canonical_doc = summary_comment + raw_txt
        enc = self.tokenizer(
            canonical_doc,
            add_special_tokens=False,
            return_offsets_mapping=True,
        )
        offsets = enc["offset_mapping"]
        n_tokens = len(offsets)
        c0 = 0
        c1 = len(canonical_doc)
        t0 = 0
        t1 = n_tokens
        late_chunking_metadata = {
            "char_span": (c0, c1),
            "token_span": (t0, t1),
        }
        docs = [{
            "content": canonical_doc,
            "filename": path,
            "chunk": "1/1",
            "subchunk": "1/1",
            "summary": summary,
            "late_chunking_metadata": late_chunking_metadata,
        }]
        return docs, canonical_doc

    def chunk_file(self, path: str, summary: str = "") -> Tuple[List[dict], List[Tuple[int, int]], str]:
        """
        Selects the appropriate chunking method based on file extension.
        - .md: uses _md_chunking
        - .yaml/.yml: uses _yaml_chunking (summary used)
        - otherwise: uses _generic_chunking
        """
        self.logger.info("chunk_file: processing path=%s", path)
        try:
            ext = Path(path).suffix.lower()
            if ext == ".md":
                return self._md_chunking(path)
            elif ext in {".yaml", ".yml"}:
                return self._yaml_chunking(path, summary=summary)
            else:
                return self._generic_chunking(path)

        except Exception as e:
            self.logger.error("chunk_file error: %s", e)
            raise

    def generate_late_chunking_embeddings(self, docs: List[dict], canonical_doc: str):
        """
        Generate embeddings for a list of documents.
        """
        self.logger.info("generate_late_chunking_embeddings: docs=%d", len(docs))
        try:
            # get per-token embeddings with the *passage* adapter
            tok_emb = self.model.encode(
                    canonical_doc,
                    output_value="token_embeddings",
                    convert_to_tensor=True,          # tensor on the same device
                    task="retrieval.passage",        # <-- LoRA head
                    prompt_name="retrieval.passage")

            output = []
            for doc in docs:
                start, end = doc["late_chunking_metadata"]["token_span"]
                if end > start:
                    pooled = tok_emb[start:end].mean(dim=0)          # mean-pool
                    # detach from GPU and move to CPU
                    doc["late_chunking_metadata"]["embedding"] = pooled.detach().cpu().float()
                else:
                    raise ValueError("Invalid token span")

                sep_emb = self.model.encode(
                    doc["content"],
                    output_value="sentence_embedding",
                    convert_to_tensor=True,          # tensor on the same device
                    task="separation",        # <-- LoRA head
                    prompt_name="separation")

                # detach from GPU and move to CPU
                doc["late_chunking_metadata"]["sep_embedding"] = sep_emb.detach().cpu().float()

                output.append(doc)
            self.logger.info("generate_late_chunking_embeddings: completed embeddings for %d docs", len(output))
            return output
        except Exception as e:
            self.logger.error("generate_late_chunking_embeddings error: %s", e)
            raise

    def generate_query_embedding(self, query) -> torch.Tensor:
        """
        Generate an embedding for a query.
        """
        self.logger.info("generate_query_embedding: query='%s'", query)
        try:
            # get per-token embeddings
            tok_emb = self.model.encode(
                    query,
                    output_value="token_embeddings",
                    convert_to_tensor=True,
                    task="retrieval.query",
                    prompt_name="retrieval.query")
            # pool tokens to 1D vector (mean-pool)
            pooled = tok_emb.mean(dim=0)
            # detach and move to CPU
            return pooled.detach().cpu().float()
        except Exception as e:
            self.logger.error("generate_query_embedding error: %s", e)
            raise

    def re_rank(
        self,
        query: str,
        docs: List[dict],
        top_k: int | None = None,
        normalize: bool = True,
    ) -> List[dict]:
        """
        Rerank candidate chunks with the `separation` LoRA head.

        Returns a list of dicts with keys 'doc' (the document) and 'score' (the score), sorted by descending score.
        """
        self.logger.info("re_rank: %d docs, top_k=%s", len(docs), top_k)
        try:
            # --- 1. embed query with separation head ---
            q_vec = self.model.encode(
                query,
                convert_to_tensor=True,
                output_value="sentence_embedding",
                task="separation",
                prompt_name="separation",
            ).to(self.device)

            if normalize:
                q_vec = F.normalize(q_vec, p=2, dim=-1)

            # --- 2. embed all documents ---
            embeddings = []
            for d in docs:
                emb = self.model.encode(
                    d["content"],
                    convert_to_tensor=True,
                    output_value="sentence_embedding",
                    task="separation",
                    prompt_name="separation",
                )
                if normalize:
                    emb = F.normalize(emb, p=2, dim=-1)
                embeddings.append(emb)
            if not embeddings:
                return []

            # --- 3. batched similarity & sorting ---
            doc_matrix = torch.stack(embeddings)  # [N, dim]
            scores = (doc_matrix @ q_vec).squeeze(-1).cpu()
            order = torch.argsort(scores, descending=True)
            ranked = [{"doc": docs[i], "score": float(scores[i])} for i in order]

            self.logger.info("re_rank: returning %d ranked docs", len(ranked[:top_k] if top_k else ranked))
            return ranked[:top_k] if top_k else ranked
        except Exception as e:
            self.logger.error("re_rank error: %s", e)
            raise
