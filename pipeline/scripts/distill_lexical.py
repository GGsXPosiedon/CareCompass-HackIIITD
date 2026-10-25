"""Can the e5 head be distilled into a runtime-free lexical model (sparse word + char n-gram weights in JSON)?

Teacher = frozen e5 + LR head (offline only). Student = TF-IDF + logistic regression, no model weights at serve time.
LOFO over the 20 CareCompass families. Student is trained on (a) the true labels of the training families and
(b) teacher soft labels (hard argmax of teacher probs, weight --w) on an unlabeled pool: the multilingual complaints, SYNAPSE phrases.
The teacher never sees the held-out family (it is re-fit per fold), so there is no leakage.
Usage: python scripts/distill_lexical.py --model-dir <models>/multilingual-e5-base [--pool 3000]
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import hstack

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "src")); sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, str(Path(__file__).parent))
from ccpipe.triage.data import CLASSES, load_unique  # noqa: E402
from app.services.onnx_embed import OnnxEmbedder  # noqa: E402
from train_router_embed import metrics  # noqa: E402


def feats(fit_texts, texts_list):
    w = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"[^\s,.;:!?|।()]+", min_df=1)
    c = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)
    w.fit(fit_texts); c.fit(fit_texts)
    return [hstack([w.transform(t), c.transform(t)]).tocsr() for t in texts_list]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--pool", type=int, default=3000)
    a = ap.parse_args()
    df = load_unique()
    texts = df["text"].tolist()
    y, fam = df["label"].to_numpy(), df["family"].to_numpy()
    pool = [json.loads(l)["text"] for l in (ROOT / "pipeline/data/processed/mlt_complaints.jsonl").read_text(encoding="utf-8").splitlines()]
    rng = np.random.RandomState(0); pool = list(rng.choice(pool, size=min(a.pool, len(pool)), replace=False))
    emb = OnnxEmbedder(a.model_dir)
    E, Ep = emb.encode(texts), emb.encode(pool)
    out = {}
    for w_pool in (0.0, 0.1, 0.3):
        P = np.zeros((len(df), len(CLASSES)))
        for g in sorted(set(fam)):
            te, tr = np.where(fam == g)[0], np.where(fam != g)[0]
            teacher = LogisticRegression(C=0.3, class_weight="balanced", max_iter=2000).fit(E[tr], y[tr])
            ypool = teacher.predict(Ep)
            X_all = [texts[i] for i in tr] + pool
            Xtr, Xp, Xte = feats(X_all, [[texts[i] for i in tr], pool, [texts[i] for i in te]])
            from scipy.sparse import vstack
            Xs = vstack([Xtr, Xp]) if w_pool > 0 else Xtr
            ys = np.concatenate([y[tr], ypool]) if w_pool > 0 else y[tr]
            sw = np.concatenate([np.ones(len(tr)), np.full(len(pool), w_pool)]) if w_pool > 0 else None
            st = LogisticRegression(C=10, class_weight="balanced", max_iter=3000).fit(Xs, ys, sample_weight=sw)
            pr = st.predict_proba(Xte)
            for j, c in enumerate(st.classes_):
                P[te, CLASSES.index(c)] = pr[:, j]
        m = metrics(df, P); out[w_pool] = m
        print(f"pool weight {w_pool}: F1={m['macro_f1']:.3f} acc={m['accuracy']:.3f} emRecall={m['emergency_recall']:.3f} overTriage={m['over_triage']} emAUROC={m['emergency_auroc']:.3f}")
    print("reference: e5 head F1=0.680, char n-gram baseline F1=0.416")


if __name__ == "__main__":
    main()
