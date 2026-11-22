"""Sentence embeddings for comparing emails with the Congress texts.

Each text is split into chunks of about 180 words of equal size (the length of
the Congress passages): a 210-word text stays one chunk, a 460-word text becomes
three chunks of about 153 words, so there are no short leftover chunks. Each chunk
is embedded with a sentence-transformers model (Reimers and Gurevych 2019), and a
text's similarity to a theme is the AVERAGE cosine similarity of its chunks. With
the average, a long document scores high only if it is on the theme throughout,
not because a long text shares some words with anything.

Embeddings are saved in results/email_themes/embeddings/ (one file per model,
chunk size and set of texts), so only the first run has to compute them.
"""

import hashlib
import re
from pathlib import Path

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-mpnet-base-v2"   # reads up to 384 word pieces (~280 words)
CHUNK_WORDS = 180


def chunk_text(text: str, size: int = CHUNK_WORDS) -> list[str]:
    """The text in chunks of about `size` words, all of (nearly) equal length."""
    words = str(text).split()
    if not words:
        return [""]
    n = max(1, round(len(words) / size))
    bounds = np.linspace(0, len(words), n + 1).round().astype(int)
    return [" ".join(words[a:b]) for a, b in zip(bounds[:-1], bounds[1:])]


def load_model(name: str = DEFAULT_MODEL):
    """The sentence-transformers model (downloaded on first use, then cached)."""
    from sentence_transformers import SentenceTransformer   # heavy import: only when needed
    return SentenceTransformer(name)


class LazyModel:
    """Loads the model at the first `encode` call, so a run whose embeddings are all
    cached never loads it (and several calls share one loaded model)."""

    def __init__(self, name: str = DEFAULT_MODEL):
        self.name, self._model = name, None

    def encode(self, *args, **kwargs):
        if self._model is None:
            self._model = load_model(self.name)
        return self._model.encode(*args, **kwargs)


def _cache_path(cache_dir: Path, label: str, model_name: str, size: int, chunks: list[str]) -> Path:
    digest = hashlib.sha1("\x00".join([model_name, str(size)] + chunks).encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^A-Za-z0-9]+", "-", model_name.split("/")[-1])
    return cache_dir / f"{label}_{slug}_{size}w_{digest}.npy"


def embed_chunks(texts, cache_dir: Path, label: str, model_name: str = DEFAULT_MODEL,
                 size: int = CHUNK_WORDS, model=None) -> tuple[np.ndarray, np.ndarray]:
    """Unit-length embeddings of every chunk of every text, and for each chunk the
    position of its text. `model` (anything with a sentence-transformers `encode`)
    is loaded only when the embeddings are not cached yet."""
    chunks, owner = [], []
    for i, text in enumerate(texts):
        for chunk in chunk_text(text, size):
            chunks.append(chunk)
            owner.append(i)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, label, model_name, size, chunks)
    if path.exists():
        vectors = np.load(path)
    else:
        model = model or load_model(model_name)
        print(f"  embedding {len(chunks):,} chunks of the {label} with {model_name} ...", flush=True)
        vectors = model.encode(chunks, batch_size=32, show_progress_bar=True,
                               convert_to_numpy=True, normalize_embeddings=True)
        np.save(path, vectors.astype(np.float32))
    return np.asarray(vectors, dtype=np.float32), np.asarray(owner)


def text_vectors(vectors: np.ndarray, owner: np.ndarray, n_texts: int) -> np.ndarray:
    """One unit vector per text: the mean of its chunk vectors."""
    sums = np.zeros((n_texts, vectors.shape[1]), dtype=np.float64)
    np.add.at(sums, owner, vectors)
    norms = np.linalg.norm(sums, axis=1, keepdims=True)
    return sums / np.where(norms == 0, 1, norms)


def mean_similarity(vectors: np.ndarray, owner: np.ndarray, n_texts: int,
                    profiles: np.ndarray) -> np.ndarray:
    """Average cosine similarity of each text's chunks to each profile
    (rows: texts, columns: profiles). Profiles must be unit vectors."""
    per_chunk = vectors @ profiles.T
    sums = np.zeros((n_texts, profiles.shape[0]))
    np.add.at(sums, owner, per_chunk)
    counts = np.bincount(owner, minlength=n_texts)[:, None]
    return sums / np.maximum(counts, 1)
