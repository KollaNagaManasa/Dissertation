from ragiac.embeddings.local_tfidf import LocalTfidfEmbedder


def test_similar_texts_score_higher_than_dissimilar():
    embedder = LocalTfidfEmbedder(max_features=64)
    embedder.fit(["gcs bucket storage class versioning", "gke cluster node pool workload identity"])

    [query_vec, similar_vec, dissimilar_vec] = embedder.embed(
        ["storage bucket versioning", "gcs bucket storage class versioning", "gke cluster node pool"]
    )

    def cosine(a, b):
        import numpy as np

        a, b = np.array(a), np.array(b)
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

    assert cosine(query_vec, similar_vec) > cosine(query_vec, dissimilar_vec)


def test_embed_before_fit_raises():
    embedder = LocalTfidfEmbedder()
    try:
        embedder.embed(["hello"])
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
