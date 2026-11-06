import numpy as np
import pandas as pd
import os
import pickle
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score

def generate_synthetic_data(n_samples=10000, n_categories=500, seed=42):
    np.random.seed(seed)
    
    # 1. Create category distribution following a power law (Zipf-like)
    probs = np.random.pareto(2, n_categories) 
    probs /= probs.sum()
    
    categories = np.random.choice(np.arange(n_categories), size=n_samples, p=probs)
    
    # 2. Create target relationship: p(target=1 | category)
    cat_probs = np.random.beta(2, 5, n_categories) # Most categories have low prob
    
    targets = np.array([np.random.binomial(1, cat_probs[c]) for c in categories])
    
    return pd.DataFrame({'feature': categories, 'target': targets})

class OOFEncoder:
    def __init__(self, method='naive', m=10, k=10, f=1):
        self.method = method
        self.m = m
        self.k = k
        self.f = f
        self.global_mean = None
        self.mapping = {}

    def _compute_smoothed_mean(self, n, mean, global_mean):
        if self.method == 'm_estimate':
            return (n * mean + self.m * global_mean) / (n + self.m)
        elif self.method == 'mb_smoothing':
            # Micci-Barreca: lambda = 1 / (1 + exp(-(n-k)/f))
            lambda_val = 1 / (1 + np.exp(-(n - self.k) / self.f))
            return lambda_val * mean + (1 - lambda_val) * global_mean
        else: # naive or basic oof
            return mean

    def fit_transform(self, X, y, cv_folds=None):
        self.global_mean = np.mean(y)
        X = np.array(X)
        y = np.array(y)
        
        if self.method == 'naive':
            means = pd.Series(y).groupby(X).mean()
            counts = pd.Series(y).groupby(X).count()
            
            full_mapping = {}
            for cat in means.index:
                full_mapping[cat] = self._compute_smoothed_mean(counts[cat], means[cat], self.global_mean)
            
            self.mapping = full_mapping
            return np.array([self.mapping.get(c, self.global_mean) for c in X])

        elif cv_folds is not None:
            oof_encoded = np.zeros(len(X))
            
            for train_idx, val_idx in cv_folds:
                X_train, y_train = X[train_idx], y[train_idx]
                X_val = X[val_idx]
                
                train_df = pd.DataFrame({'feat': X_train, 'targ': y_train})
                agg = train_df.groupby('feat')['targ'].agg(['mean', 'count'])
                
                fold_map = {cat: self._compute_smoothed_mean(agg.loc[cat, 'count'], agg.loc[cat, 'mean'], self.global_mean) 
                            for cat in agg.index}
                
                for i in val_idx:
                    cat = X[i]
                    oof_encoded[i] = fold_map.get(cat, self.global_mean)
                    
            return oof_encoded
        else:
            means = pd.Series(y).groupby(X).mean()
            counts = pd.Series(y).groupby(X).count()
            full_mapping = {cat: self._compute_smoothed_mean(counts[cat], means[cat], self.global_mean) for cat in means.index}
            self.mapping = full_mapping
            return np.array([self.mapping.get(c, self.global_mean) for c in X])

def run_benchmark():
    df = generate_synthetic_data()
    X = df['feature'].values
    y = df['target'].values
    
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    folds = list(skf.split(X, y))
    
    variants = [
        ('V1_Naive', 'naive', None, None),
        ('V2_OOF', 'oof', None, None),
        ('V3_M_OOF', 'm_estimate', 10, None),
        ('V4_MB_OOF', 'mb_smoothing', 10, 1),
    ]
    
    results = {}
    all_oof_preds = {}

    for name, method, m, f in variants:
        print(f"Running {name}...")
        encoder = OOFEncoder(method=method, m=m if m else 10, k=10, f=f if f else 1)
        
        if method == 'naive':
            preds = encoder.fit_transform(X, y)
        else:
            preds = encoder.fit_transform(X, y, cv_folds=folds)
        
        fold_aucs = []
        for train_idx, val_idx in folds:
            val_preds = preds[val_idx]
            val_targets = y[val_idx]
            fold_aucs.append(roc_auc_score(val_targets, val_preds))
        
        mean_auc = np.mean(fold_aucs)
        results[name] = {'mean_auc': mean_auc, 'fold_aucs': fold_aucs}
        all_oof_preds[name] = preds
        
    return results, all_oof_preds

if __name__ == "__main__":
    res, preds = run_benchmark()
    
    artifact_dir = "/home/kizamladjanijebac/.gemini/antigravity/worktrees/discord-openclaw/analyze_discord_openclaw_setup/research_workspaces/target_encoding_benchmark/experiments/artifacts/EXP_001"
    os.makedirs(artifact_dir, exist_ok=True)
    with open(os.path.join(artifact_dir, "oof_predictions.pkl"), "wb") as f:
        pickle.dump(preds, f)
        
    print("\n--- BENCHMARK RESULTS ---")
    for var, data in res.items():
        print(f"{var}: AUC={data['mean_auc']:.4f} Folds={data['fold_aucs']}")
