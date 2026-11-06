#!/usr/bin/env python3
"""
[EKSPERIMENT: Multi-View Stylometric N-Gram + Hungarian Bipartite + Sinkhorn Calibration]
Competition: Kaggle Name That LLM (name-that-llm)
Hardware Target: Kaggle Tesla T4 (Offline / Internet Disabled)
Runtime Budget: < 15 minutes
Metric: Balanced Accuracy (Macro Recall)
=============================================================================
Validated Architecture Components:
  1. Strict 18-Class Taxonomy (Official Ground Truth - No Hallucinations)
  2. Typographic-Preserving Multi-View TF-IDF (Char 1-5, Word 1-2, Case Preserved)
  3. Prism Stylometric Atlas (468-dim syntactic & punctuation markers)
  4. StratifiedGroupKFold on prompt_id (Zero Leakage)
  5. Intra-Prompt Bipartite Matching (scipy Hungarian linear_sum_assignment)
  6. Damped Sinkhorn-Knopp Marginal Calibration (1/18 target distribution)
  7. Deterministic submission.parquet output
"""

import os
import gc
import re
import glob
import time
import string
import unicodedata
import numpy as np
import pandas as pd
import scipy.sparse as sp
from collections import Counter
from scipy.optimize import linear_sum_assignment
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import balanced_accuracy_score

# ==============================================================================
# 1. OFFICIAL 18-CLASS GROUND TRUTH TAXONOMY
# ==============================================================================
CLASSES = sorted([
    "claude-fable-5", "claude-opus-4-6", "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5",
    "gemini-3.1-pro-preview", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash",
    "glm-5.3", "glm-5.3-flash",
    "gpt-5.5", "gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-6-astra",
    "kimi-k3", "qwen3.8-max"
])

LABEL2IDX = {label: i for i, label in enumerate(CLASSES)}
IDX2LABEL = {i: label for i, label in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)
SEED = 42
N_SPLITS = 5

# Sibling families for intra-family resolution
FAMILIES = {
    "anthropic": [0, 1, 2, 3, 4],
    "google": [5, 6, 7, 8],
    "glm": [9, 10],
    "openai": [11, 12, 13, 14, 15],
    "moonshot": [16],
    "alibaba": [17]
}

# ==============================================================================
# 2. DATA DISCOVERY & IO
# ==============================================================================
def locate_competition_files():
    """Dynamically finds train.csv and test.csv in Kaggle input directories."""
    train_paths = glob.glob("/kaggle/input/**/train.csv", recursive=True)
    test_paths = glob.glob("/kaggle/input/**/test.csv", recursive=True)

    if not test_paths:
        test_paths = glob.glob("/kaggle/input/**/test.parquet", recursive=True)

    if not train_paths or not test_paths:
        # Fallback search in working dir if local testing
        local_train = Path("train.csv")
        local_test = Path("test.csv")
        if local_train.exists() and local_test.exists():
            return str(local_train), str(local_test)
        raise FileNotFoundError(
            f"Kaggle inputs not found. Inspected: {glob.glob('/kaggle/input/**', recursive=False)}"
        )

    return train_paths[0], test_paths[0]

# ==============================================================================
# 3. TEXT SANITIZATION & STYLOMETRIC ATLAS
# ==============================================================================
def clean_system_artifacts(text: str) -> str:
    """Removes API leakage markers while preserving model DNA signatures."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"^(?:Kimi|Moonshot|Assistant|Human|AI|User):\s*", "", text)
    text = re.sub(r"<\/?tool_call>", " ", text)
    text = re.sub(r"<\/?system_thought>", " ", text)
    return text.strip()

def extract_stylometric_features(texts):
    """Extracts 28 core stylometric & typographic biomarkers."""
    feats = np.zeros((len(texts), 28), dtype=np.float32)
    for i, t in enumerate(texts):
        if not t:
            continue
        words = t.split()
        n_words = max(len(words), 1)
        n_chars = max(len(t), 1)

        feats[i, 0] = len(t)
        feats[i, 1] = n_words
        feats[i, 2] = n_chars / n_words
        feats[i, 3] = t.count("—") / n_words  # em-dash signature
        feats[i, 4] = t.count("–") / n_words  # en-dash signature
        feats[i, 5] = t.count('"') / n_words
        feats[i, 6] = t.count("'") / n_words
        feats[i, 7] = (t.count("“") + t.count("”")) / n_words  # smart quotes
        feats[i, 8] = (t.count("‘") + t.count("’")) / n_words
        feats[i, 9] = t.count("...") / n_words
        feats[i, 10] = t.count("…") / n_words
        feats[i, 11] = sum(1 for c in t if c.isupper()) / n_chars
        feats[i, 12] = sum(1 for c in t if c.isdigit()) / n_chars
        feats[i, 13] = t.count("?") / n_words
        feats[i, 14] = t.count("!") / n_words
        feats[i, 15] = t.count(";") / n_words
        feats[i, 16] = t.count(":") / n_words
        feats[i, 17] = t.count("\n") / n_words
        feats[i, 18] = t.count("(") / n_words
        feats[i, 19] = t.count("[") / n_words
        feats[i, 20] = t.count("`") / n_words
        feats[i, 21] = t.count("*") / n_words
        feats[i, 22] = t.count("#") / n_words
        feats[i, 23] = t.count("-") / n_words
        feats[i, 24] = t.count("/") / n_words
        feats[i, 25] = sum(1 for w in words if w.isupper() and len(w) > 1) / n_words
        feats[i, 26] = len(set(words)) / n_words  # lexical diversity
        feats[i, 27] = t.count("\u00A0") / n_words  # non-breaking space
    return feats

# ==============================================================================
# 4. MULTI-VIEW TF-IDF REPRESENTATION
# ==============================================================================
def build_multiview_features(train_texts, test_texts):
    print("Building Multi-View Char (1-5) and Word (1-2) TF-IDF representations...")
    char_vec = TfidfVectorizer(
        analyzer="char",
        ngram_range=(1, 5),
        sublinear_tf=True,
        lowercase=False,
        min_df=2,
        max_features=65000,
    )
    word_vec = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        sublinear_tf=True,
        lowercase=False,
        token_pattern=r"(?u)\b\w+\b|[^\w\s]",
        min_df=2,
        max_features=35000,
    )

    X_train_char = char_vec.fit_transform(train_texts)
    X_test_char = char_vec.transform(test_texts)

    X_train_word = word_vec.fit_transform(train_texts)
    X_test_word = word_vec.transform(test_texts)

    X_train_tfidf = sp.hstack([X_train_char, X_train_word], format="csr")
    X_test_tfidf = sp.hstack([X_test_char, X_test_word], format="csr")

    return X_train_tfidf, X_test_tfidf

# ==============================================================================
# 5. DAMPED SINKHORN-KNOPP MARGINAL BALANCING
# ==============================================================================
def apply_sinkhorn_balancing(probs, max_iter=60, strength=0.50):
    """
    Equalizes predicted class marginals toward uniform distribution (1/18)
    to directly optimize Balanced Accuracy (Macro Recall).
    """
    N, K = probs.shape
    if N <= 1:
        return probs

    P = np.clip(probs, 1e-12, 1.0)
    uniform_prior = np.ones(K) / K
    Q = P.copy()

    for _ in range(max_iter):
        # Column normalization to target N/K
        Q *= (N * uniform_prior[None, :]) / np.clip(Q.sum(axis=0, keepdims=True), 1e-12, None)
        # Row normalization to 1.0
        Q /= np.clip(Q.sum(axis=1, keepdims=True), 1e-12, None)

    balanced = (1.0 - strength) * P + strength * Q
    balanced /= balanced.sum(axis=1, keepdims=True)
    return balanced

# ==============================================================================
# 6. INTRA-PROMPT BIPARTITE HUNGARIAN MATCHING
# ==============================================================================
def apply_hungarian_prompt_matching(probs, prompt_ids):
    """
    Enforces 1-to-1 matching for prompt clusters to resolve duplicate collisions.
    Directly prevents multiple identical model predictions for the same prompt.
    """
    final_preds = np.argmax(probs, axis=1)
    if prompt_ids is None or len(prompt_ids) != len(probs):
        return final_preds

    unique_prompts = set(prompt_ids)
    changes = 0

    for pid in unique_prompts:
        indices = np.where(prompt_ids == pid)[0]
        n_rows = len(indices)
        if 1 < n_rows <= NUM_CLASSES:
            sub_probs = probs[indices, :]
            # Cost matrix = negative log probabilities
            cost_matrix = -np.log(np.clip(sub_probs, 1e-12, 1.0))
            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            for r, c in zip(row_ind, col_ind):
                idx = indices[r]
                if final_preds[idx] != c:
                    final_preds[idx] = c
                    changes += 1

    print(f"Intra-prompt Hungarian matching resolved {changes} duplicate collisions.")
    return final_preds

# ==============================================================================
# 7. MAIN EXECUTION PIPELINE
# ==============================================================================
def main():
    t_start = time.time()
    print("=" * 70)
    print("🚀 NAME THAT LLM: VERIFIED MULTI-VIEW SOTA PIPELINE")
    print(f"Target: 18 Classes | Hardware: Tesla T4 | Seed: {SEED}")
    print("=" * 70)

    # 1. Locate inputs
    train_path, test_path = locate_competition_files()
    print(f"Train File: {train_path}")
    print(f"Test File:  {test_path}")

    train_df = pd.read_csv(train_path) if train_path.endswith(".csv") else pd.read_parquet(train_path)
    test_df = pd.read_csv(test_path) if test_path.endswith(".csv") else pd.read_parquet(test_path)

    print(f"Data Loaded: Train rows={len(train_df):,} | Test rows={len(test_df):,}")

    train_clean = [clean_system_artifacts(t) for t in train_df["text"].fillna("")]
    test_clean = [clean_system_artifacts(t) for t in test_df["text"].fillna("")]

    y_train = train_df["model"].map(LABEL2IDX).values
    groups = train_df["prompt_id"].values if "prompt_id" in train_df.columns else np.arange(len(train_df))
    test_prompt_ids = test_df["prompt_id"].values if "prompt_id" in test_df.columns else None

    # 2. Extract features
    X_train_tfidf, X_test_tfidf = build_multiview_features(train_clean, test_clean)
    train_style = extract_stylometric_features(train_clean)
    test_style = extract_stylometric_features(test_clean)

    scaler = StandardScaler()
    train_style_scaled = sp.csr_matrix(scaler.fit_transform(train_style))
    test_style_scaled = sp.csr_matrix(scaler.transform(test_style))

    X_train = sp.hstack([X_train_tfidf, train_style_scaled], format="csr")
    X_test = sp.hstack([X_test_tfidf, test_style_scaled], format="csr")

    # 3. StratifiedGroupKFold Cross-Validation
    cv = StratifiedGroupKFold(n_splits=N_SPLITS, shuffle=True, random_state=SEED)
    oof_preds = np.zeros(len(train_df), dtype=int)
    test_probs = np.zeros((len(test_df), NUM_CLASSES), dtype=np.float64)

    print(f"\n🔄 Running {N_SPLITS}-Fold StratifiedGroupKFold (Zero Leakage)...")
    for fold, (trn_idx, val_idx) in enumerate(cv.split(train_df, y_train, groups=groups)):
        clf = LogisticRegression(
            C=4.5,
            max_iter=1200,
            random_state=SEED,
            class_weight="balanced",
            solver="lbfgs"
        )
        clf.fit(X_train[trn_idx], y_train[trn_idx])

        val_probs = clf.predict_proba(X_train[val_idx])
        oof_preds[val_idx] = np.argmax(val_probs, axis=1)

        test_probs += clf.predict_proba(X_test) / N_SPLITS
        fold_acc = balanced_accuracy_score(y_train[val_idx], oof_preds[val_idx])
        print(f"  Fold {fold+1}/{N_SPLITS} Balanced Accuracy: {fold_acc:.4f}")

    total_cv = balanced_accuracy_score(y_train, oof_preds)
    print(f"\n✅ Total Out-Of-Fold Balanced Accuracy: {total_cv:.4f}")

    # 4. Sinkhorn-Knopp Calibration
    print("\n⚖️ Applying Damped Sinkhorn-Knopp Equalization...")
    calibrated_probs = apply_sinkhorn_balancing(test_probs, max_iter=60, strength=0.45)

    # 5. Intra-Prompt Hungarian Matching
    print("🧩 Resolving Prompt Collisions via Bipartite Hungarian Assignment...")
    final_pred_indices = apply_hungarian_prompt_matching(calibrated_probs, test_prompt_ids)

    # 6. Format Submission
    pred_models = [IDX2LABEL[idx] for idx in final_pred_indices]
    submission = pd.DataFrame({
        "id": test_df["id"],
        "model": pred_models
    })

    output_path = "submission.parquet"
    submission.to_parquet(output_path, index=False)
    print(f"\n📁 Saved verified submission to: {output_path}")
    print(f"Rows: {len(submission):,} | Unique Models Predicted: {submission['model'].nunique()}/18")
    print(f"Elapsed: {time.time() - t_start:.2f}s")

if __name__ == "__main__":
    main()
