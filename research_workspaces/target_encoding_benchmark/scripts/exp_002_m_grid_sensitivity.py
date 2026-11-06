import numpy as np
import pandas as pd
import os
import pickle
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

def generate_synthetic_data(n_samples=10000, n_categories=500, seed=42):
    np.random.seed(seed)
    # 1. Category distribution following a power law (Zipf-like)
    probs = np.random.pareto(2, n_categories)
    probs /= probs.sum()
    categories = np.random.choice(np.arange(n_categories), size=n_samples, p=probs)
    
    # 2. Target relationship: p(target=1 | category)
    cat_probs = np.random.beta(2, 5, n_categories)
    targets = np.array([np.random.binomial(1, cat_probs[c]) for c in categories])
    return pd.DataFrame({'feature': categories, 'target': targets})

class MEstimateOOFEncoder:
    def __init__(self, m=10.0):
        self.m = float(m)
        self.global_mean = None

    def fit_transform(self, X, y, cv_folds):
        self.global_mean = float(np.mean(y))
        X = np.array(X)
        y = np.array(y)
        oof_encoded = np.zeros(len(X))
        train_encoded = np.zeros(len(X))

        for train_idx, val_idx in cv_folds:
            X_train, y_train = X[train_idx], y[train_idx]
            X_val = X[val_idx]

            train_df = pd.DataFrame({'feat': X_train, 'targ': y_train})
            agg = train_df.groupby('feat')['targ'].agg(['mean', 'count'])

            # M-Estimate smoothing: (n * mean + m * global_mean) / (n + m)
            if self.m == 0.0:
                fold_map = agg['mean'].to_dict()
            else:
                fold_map = {
                    cat: (agg.loc[cat, 'count'] * agg.loc[cat, 'mean'] + self.m * self.global_mean) / (agg.loc[cat, 'count'] + self.m)
                    for cat in agg.index
                }

            # Map to validation slice (strictly leak-free)
            for i in val_idx:
                cat = X[i]
                oof_encoded[i] = fold_map.get(cat, self.global_mean)

            # Map to train slice for generalization gap calculation
            for i in train_idx:
                cat = X[i]
                train_encoded[i] = fold_map.get(cat, self.global_mean)

        return oof_encoded, train_encoded

def run_m_grid_experiment():
    df = generate_synthetic_data()
    X = df['feature'].values
    y = df['target'].values

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    folds = list(skf.split(X, y))

    m_grid = [0.0, 0.1, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 500.0, 1000.0]
    results = {}
    oof_predictions_all = {}

    print(f"Executing EXP_002: Evaluating M-Estimate Grid across {len(m_grid)} points...")

    for m in m_grid:
        encoder = MEstimateOOFEncoder(m=m)
        oof_preds, train_preds = encoder.fit_transform(X, y, cv_folds=folds)

        fold_val_aucs = []
        fold_train_aucs = []

        for train_idx, val_idx in folds:
            fold_val_aucs.append(roc_auc_score(y[val_idx], oof_preds[val_idx]))
            fold_train_aucs.append(roc_auc_score(y[train_idx], train_preds[train_idx]))

        mean_val_auc = float(np.mean(fold_val_aucs))
        mean_train_auc = float(np.mean(fold_train_aucs))
        std_val_auc = float(np.std(fold_val_aucs))
        gen_gap = float(mean_train_auc - mean_val_auc)

        results[f"m_{m}"] = {
            'm': m,
            'mean_val_auc': round(mean_val_auc, 5),
            'std_val_auc': round(std_val_auc, 5),
            'mean_train_auc': round(mean_train_auc, 5),
            'generalization_gap': round(gen_gap, 5),
            'fold_aucs': [round(a, 5) for a in fold_val_aucs]
        }
        oof_predictions_all[f"m_{m}"] = oof_preds

    return results, oof_predictions_all

if __name__ == "__main__":
    results, oof_predictions = run_m_grid_experiment()

    artifact_dir = "/home/kizamladjanijebac/.gemini/antigravity/worktrees/discord-openclaw/analyze_discord_openclaw_setup/research_workspaces/target_encoding_benchmark/experiments/artifacts/EXP_002"
    os.makedirs(artifact_dir, exist_ok=True)

    results_file = os.path.join(artifact_dir, "m_grid_results.pkl")
    preds_file = os.path.join(artifact_dir, "oof_predictions_exp002.pkl")

    with open(results_file, "wb") as f:
        pickle.dump(results, f)
    with open(preds_file, "wb") as f:
        pickle.dump(oof_predictions, f)

    print("\n=== EXP_002 RESULTS TABLE ===")
    print(f"{'m':<8} | {'Val AUC (Mean)':<15} | {'Std Dev':<10} | {'Train AUC':<12} | {'Gen Gap':<10}")
    print("-" * 65)
    for k, v in results.items():
        print(f"{v['m']:<8} | {v['mean_val_auc']:<15.5f} | {v['std_val_auc']:<10.5f} | {v['mean_train_auc']:<12.5f} | {v['generalization_gap']:<10.5f}")
