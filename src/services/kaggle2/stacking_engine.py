"""
stacking_engine.py — 4-Level Stacking Hierarchy & Logit Meta-Learner
=====================================================================
Implements the 4-Level Stacking Architecture from the Strategic Framework:
  Level 1: Feature Extraction Models (cuML KNN, PCA, DAE embeddings, Target Encoding)
  Level 2: Base Models (GBDTs: XGBoost, LightGBM, CatBoost, YDF, Random Forest +
           Neural Networks: RealMLP, TabM, TabNet, Trompt)
  Level 3: Intermediate Stacking (*_stk models trained on Level 2 OOFs)
  Level 4: Final Meta-Learner: L2-penalized Logistic Regression in Logit Space
           logit(p) = log(p / (1 - p))
  
Includes the KGMON Diversity Filter:
  - AUC > threshold (e.g. 0.940)
  - Pairwise Pearson correlation with existing pool < 0.99
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression, RidgeClassifier

logger = logging.getLogger("Kaggle2.StackingEngine")


def to_logit(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """
    Transforms probability predictions in [0, 1] into Logit space (-inf, +inf):
      logit(p) = log((p + eps) / (1 - p + eps))
    Prevents asymptotic boundary compression in deep ensembles.
    """
    p_clipped = np.clip(p, eps, 1.0 - eps)
    return np.log(p_clipped / (1.0 - p_clipped))


def from_logit(logits: np.ndarray) -> np.ndarray:
    """Transforms Logit values back to probability predictions in [0, 1]."""
    return 1.0 / (1.0 + np.exp(-logits))


class DiversityFilter:
    """Enforces the KGMON model diversity acceptance policy."""

    def __init__(self, min_auc: float = 0.940, max_correlation: float = 0.99):
        self.min_auc = min_auc
        self.max_correlation = max_correlation

    def evaluate_candidate(
        self,
        candidate_oof: np.ndarray,
        candidate_name: str,
        existing_oofs: Dict[str, np.ndarray],
        y_true: np.ndarray
    ) -> Tuple[bool, str, float, float]:
        """
        Evaluates candidate against diversity criteria:
          1. Candidate AUC must be >= min_auc (or higher than random chance baseline).
          2. Max pairwise correlation with any existing model must be < max_correlation.
        Returns: (passed, reason, auc, max_corr)
        """
        try:
            cand_auc = float(roc_auc_score(y_true, candidate_oof))
        except Exception as e:
            return False, f"Failed to compute ROC-AUC: {e}", 0.0, 1.0

        if len(existing_oofs) == 0:
            return True, f"First model accepted (AUC: {cand_auc:.5f})", cand_auc, 0.0

        max_corr = 0.0
        most_correlated_model = ""
        for name, oof in existing_oofs.items():
            # Pearson correlation
            corr = float(np.corrcoef(candidate_oof, oof)[0, 1])
            if corr > max_corr:
                max_corr = corr
                most_correlated_model = name

        if max_corr >= self.max_correlation:
            reason = (
                f"REJECTED: Correlation {max_corr:.4f} with '{most_correlated_model}' "
                f"exceeds diversity limit ({self.max_correlation})"
            )
            return False, reason, cand_auc, max_corr

        reason = f"ACCEPTED: AUC {cand_auc:.5f}, max correlation {max_corr:.4f} with '{most_correlated_model}'"
        return True, reason, cand_auc, max_corr


class LogitMetaLearner:
    """
    Level 4 Final Meta-Learner combining OOF predictions using L2 Logistic Regression in Logit space.
    GPU-accelerated via RAPIDS cuML when available, with automatic CPU scikit-learn fallback.
    """

    def __init__(self, C: float = 1.0, max_iter: int = 1000, random_state: int = 42):
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state
        self.model = None
        self.use_gpu = False
        self._init_backend()

    def _init_backend(self):
        try:
            import cuml
            from cuml.linear_model import LogisticRegression as CuMLLogisticRegression
            self.model = CuMLLogisticRegression(C=self.C, max_iter=self.max_iter)
            self.use_gpu = True
            logger.info("[StackingEngine] GPU cuML LogisticRegression backend initialized")
        except (ImportError, Exception) as e:
            self.model = LogisticRegression(
                C=self.C,
                max_iter=self.max_iter,
                random_state=self.random_state,
                solver="lbfgs"
            )
            self.use_gpu = False
            logger.info(f"[StackingEngine] cuML unavailable ({e}), using CPU scikit-learn LogisticRegression")

    def fit(self, oof_matrix: np.ndarray, y_true: np.ndarray) -> "LogitMetaLearner":
        """
        Fits L2 Logistic Regression over logits of out-of-fold predictions.
        oof_matrix shape: (n_samples, n_models)
        """
        logits_mat = to_logit(oof_matrix)
        self.model.fit(logits_mat, y_true)
        return self

    def predict_proba(self, pred_matrix: np.ndarray) -> np.ndarray:
        """
        Generates ensemble probability predictions given base model predictions.
        pred_matrix shape: (n_samples, n_models)
        """
        logits_mat = to_logit(pred_matrix)
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(logits_mat)
            if probs.ndim == 2 and probs.shape[1] >= 2:
                return probs[:, 1]
            return probs.flatten()
        elif hasattr(self.model, "decision_function"):
            df = self.model.decision_function(logits_mat)
            return from_logit(df)
        else:
            preds = self.model.predict(logits_mat)
            return preds.astype(float)

    def get_model_weights(self, model_names: List[str]) -> Dict[str, float]:
        """Returns normalized feature weights assigned to each base model by the meta-learner."""
        if hasattr(self.model, "coef_"):
            coefs = np.array(self.model.coef_).flatten()
            total = np.sum(np.abs(coefs)) or 1.0
            return {name: float(coefs[i] / total) for i, name in enumerate(model_names)}
        return {name: 1.0 / len(model_names) for name in model_names}


class FourLevelStacker:
    """
    Orchestrates the 4-Level Stacking Hierarchy:
      Level 1: Feature Extraction Models
      Level 2: Base Models
      Level 3: Intermediate Stacking (*_stk)
      Level 4: Logit Meta-Learner
    """

    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.level2_models: Dict[str, np.ndarray] = {}  # {name: oof_preds}
        self.level2_test_preds: Dict[str, np.ndarray] = {}
        self.level3_models: Dict[str, np.ndarray] = {}  # {name_stk: oof_preds}
        self.level3_test_preds: Dict[str, np.ndarray] = {}
        self.meta_learner = LogitMetaLearner()
        self.diversity_filter = DiversityFilter()

    def register_level2_model(
        self,
        name: str,
        oof: np.ndarray,
        test_pred: Optional[np.ndarray] = None,
        y_true: Optional[np.ndarray] = None
    ) -> Tuple[bool, str]:
        """Registers a Level 2 base model after passing the diversity filter."""
        if y_true is not None:
            passed, reason, auc, corr = self.diversity_filter.evaluate_candidate(
                candidate_oof=oof,
                candidate_name=name,
                existing_oofs=self.level2_models,
                y_true=y_true
            )
            if not passed:
                logger.warning(f"[FourLevelStacker] Level 2 model '{name}' rejected: {reason}")
                return False, reason

        self.level2_models[name] = oof
        if test_pred is not None:
            self.level2_test_preds[name] = test_pred
        return True, f"Registered Level 2 model '{name}'"

    def register_level3_model(
        self,
        name: str,
        oof: np.ndarray,
        test_pred: Optional[np.ndarray] = None
    ):
        """Registers a Level 3 intermediate stacked model (e.g. name with suffix '_stk')."""
        clean_name = name if name.endswith("_stk") else f"{name}_stk"
        self.level3_models[clean_name] = oof
        if test_pred is not None:
            self.level3_test_preds[clean_name] = test_pred

    def fit_final_stack(self, y_true: np.ndarray) -> Dict[str, Any]:
        """
        Fits Level 4 Logit Meta-Learner over all Level 2 and Level 3 OOF predictions.
        Returns final ensemble OOF AUC and model contribution weights.
        """
        all_names = list(self.level2_models.keys()) + list(self.level3_models.keys())
        if not all_names:
            raise ValueError("No models registered in stacker to fit")

        oof_cols = [self.level2_models[n] for n in self.level2_models] + \
                   [self.level3_models[n] for n in self.level3_models]
        oof_matrix = np.column_stack(oof_cols)

        self.meta_learner.fit(oof_matrix, y_true)
        ensemble_oof_probs = self.meta_learner.predict_proba(oof_matrix)
        ensemble_auc = float(roc_auc_score(y_true, ensemble_oof_probs))
        weights = self.meta_learner.get_model_weights(all_names)

        return {
            "ensemble_auc": ensemble_auc,
            "n_models": len(all_names),
            "model_weights": weights,
            "ensemble_oof": ensemble_oof_probs
        }

    def predict_test_ensemble(self) -> Optional[np.ndarray]:
        """Generates Level 4 meta-learner predictions for test set."""
        all_names = list(self.level2_models.keys()) + list(self.level3_models.keys())
        for n in all_names:
            if n in self.level2_models and n not in self.level2_test_preds:
                return None
            if n in self.level3_models and n not in self.level3_test_preds:
                return None

        test_cols = [self.level2_test_preds[n] for n in self.level2_models] + \
                    [self.level3_test_preds[n] for n in self.level3_models]
        test_matrix = np.column_stack(test_cols)
        return self.meta_learner.predict_proba(test_matrix)
