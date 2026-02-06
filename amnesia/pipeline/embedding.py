"""Event embedding stage with deterministic local fallback."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass

from amnesia.models import Event, EventEmbedding

TOKEN_RE = re.compile(r"[A-Za-z0-9_@.+-]{2,}")


@dataclass(slots=True)
class EmbeddingResult:
    embeddings: list[EventEmbedding]
    model: str


class HashEmbeddingProvider:
    """Cheap, deterministic embedding provider for local-first pipelines."""

    def __init__(self, *, dimensions: int = 128, model_name: str = "hash-embed-v1") -> None:
        self.dimensions = dimensions
        self.model_name = model_name

    def embed_text(self, text: str) -> list[float]:
        counts: Counter[int] = Counter()
        for token in TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], byteorder="big") % self.dimensions
            counts[idx] += 1

        vector = [0.0] * self.dimensions
        for idx, count in counts.items():
            vector[idx] = float(count)
        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        return vector


def embed_events(
    events: list[Event],
    *,
    provider: HashEmbeddingProvider | None = None,
) -> EmbeddingResult:
    embedder = provider or HashEmbeddingProvider()
    out: list[EventEmbedding] = []
    for event in events:
        text_hash = hashlib.sha256(event.content.encode("utf-8")).hexdigest()
        emb_id = hashlib.sha256(
            f"{event.event_id}|{embedder.model_name}|{text_hash}".encode()
        ).hexdigest()
        out.append(
            EventEmbedding(
                embedding_id=emb_id,
                event_id=event.event_id,
                ts=event.ts,
                source=event.source,
                model=embedder.model_name,
                vector_json=embedder.embed_text(event.content),
                text_hash=text_hash,
                meta_json={"token_count": len(TOKEN_RE.findall(event.content))},
            )
        )
    return EmbeddingResult(embeddings=out, model=embedder.model_name)
