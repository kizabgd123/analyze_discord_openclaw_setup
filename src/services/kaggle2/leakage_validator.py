"""
leakage_validator.py — Deterministic Data Leakage & Schema Validation Layer
============================================================================
Enforces strict competition integrity for Kaggle S6E11:
  1. Schema enforcement: exactly 24 verified features from train.csv (no hallucinated columns).
  2. Target exclusion: 'is_fraud' cannot be used in model features or feature transformations.
  3. Key isolation: 'id' must be excluded from feature matrices.
  4. AST-based leakage detection:
     - Catches naive global target encoding (y.groupby(X[col]).mean() mapped to whole dataset).
     - Catches fitting transformers/scalers on validation or test sets.
     - Catches direct leakage of target into features.
  5. Cross-fitting verification: mathematically checks that a row's label does not influence its own target encoding.
"""

import ast
import re
from typing import List, Dict, Any, Optional, Set
import numpy as np
import pandas as pd

# The authoritative 24 features present in S6E11 train.csv / test.csv
VERIFIED_S6E11_FEATURES = [
    "amount_usd",
    "hours_since_last_txn",
    "txn_count_last_24h",
    "distance_from_home_km",
    "card_age_months",
    "customer_age",
    "account_balance_usd",
    "cvv_retry_count",
    "velocity_score",
    "time_of_day_hour",
    "day_of_week",
    "merchant_risk_score",
    "prior_disputes",
    "merchant_category",
    "card_type",
    "auth_method",
    "channel",
    "device_type",
    "is_foreign_transaction",
    "is_new_merchant",
    "used_vpn",
    "ip_country_mismatch",
    "billing_shipping_mismatch",
    "is_ai_generated_scam_attempt"
]

FORBIDDEN_COLUMNS = {"id", "is_fraud"}


class LeakageValidator:
    """Deterministic leakage and schema validation service."""

    @classmethod
    def get_verified_features(cls) -> List[str]:
        return list(VERIFIED_S6E11_FEATURES)

    @classmethod
    def validate_features(cls, proposed_features: List[str]) -> List[str]:
        """
        Validates that all proposed features exist in the verified schema and do not
        include target or ID columns.
        """
        errors = []
        verified_set = set(VERIFIED_S6E11_FEATURES)

        for feat in proposed_features:
            if feat in FORBIDDEN_COLUMNS:
                errors.append(f"ForbiddenColumnError: '{feat}' is a protected key/target and cannot be a feature.")
            elif feat not in verified_set:
                errors.append(f"NonexistentFeatureError: '{feat}' does not exist in the 24 verified S6E11 features.")

        return errors

    @classmethod
    def check_ast_leakage(cls, code_str: str) -> List[str]:
        """
        Performs static AST and syntactic analysis of Python model code to detect
        data leakage patterns.
        """
        issues = []
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return [f"SyntaxError in model code: {e}"]

        class LeakageVisitor(ast.NodeVisitor):
            def __init__(self):
                self.val_in_fit = False
                self.target_in_features = False
                self.naive_target_encode = False
                self.id_as_feature = False

            def visit_Call(self, node: ast.Call):
                # Check for .fit(X_val) or .fit_transform(X_val)
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("fit", "fit_transform"):
                    for arg in node.args:
                        arg_repr = ast.unparse(arg).lower() if hasattr(ast, "unparse") else ""
                        if "val" in arg_repr or "test" in arg_repr:
                            # If it's eval_set=[(X_val, y_val)], that is valid early stopping.
                            # But if the first arg (training data) contains val/test, flag it!
                            if node.args and node.args[0] == arg:
                                self.val_in_fit = True

                # Check for y.groupby(X[col]).mean() or df.groupby(col)['is_fraud'].mean()
                if hasattr(ast, "unparse"):
                    call_code = ast.unparse(node)
                    if "groupby" in call_code and ("mean" in call_code or "agg" in call_code):
                        if "is_fraud" in call_code or "y_train" in call_code or "y[" in call_code or "y." in call_code:
                            # Check if inner KFold is used or if it's directly assigned to whole dataset
                            if "oof_target_encode" not in call_code and "kfold" not in code_str.lower():
                                self.naive_target_encode = True

                self.generic_visit(node)

            def visit_Assign(self, node: ast.Assign):
                for target in node.targets:
                    if hasattr(ast, "unparse"):
                        target_code = ast.unparse(target)
                        if "'is_fraud'" in target_code or '"is_fraud"' in target_code:
                            if any(k in target_code.lower() for k in ("x_train", "x_val", "features", "df")):
                                self.target_in_features = True
                self.generic_visit(node)

            def visit_Subscript(self, node: ast.Subscript):
                if hasattr(ast, "unparse"):
                    sub_code = ast.unparse(node)
                    if any(k in sub_code.lower() for k in ("x_train", "x_val")):
                        if "'id'" in sub_code or '"id"' in sub_code:
                            self.id_as_feature = True
                self.generic_visit(node)

        visitor = LeakageVisitor()
        visitor.visit(tree)

        if visitor.val_in_fit:
            issues.append("ValidationContaminationError: Preprocessing or model fitting appears to use validation/test data directly.")

        if visitor.target_in_features:
            issues.append("TargetLeakageError: Target column 'is_fraud' is explicitly added to training features.")

        if visitor.naive_target_encode:
            issues.append("UnsafeTargetEncodingError: Target encoding detected without inner cross-validation folds.")

        if visitor.id_as_feature or re.search(r"\bX_(?:train|val|te|test)\s*\[.*['\"]id['\"].*\]", code_str):
            issues.append("IdentifierLeakageError: Column 'id' is explicitly referenced as a model feature.")

        if re.search(r"\b(X_test|test_df)\[\s*['\"]is_fraud['\"]\s*\]\s*=", code_str):
            issues.append("TestLabelContaminationError: Writing target 'is_fraud' to test set.")

        return issues

    @classmethod
    def verify_target_encoding_isolation(
        cls,
        encoder_fn,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        cat_col: str,
        target_series: pd.Series
    ) -> bool:
        """
        Mathematically verifies that flipping a sample's label produces 0 delta on
        its own training-time encoded feature value.
        """
        orig_tr, _, _ = encoder_fn(
            train_df=train_df.copy(),
            val_df=val_df.copy(),
            cat_cols=[cat_col],
            y_train=target_series.copy()
        )
        col_encoded_name = f"{cat_col}_te"
        if col_encoded_name not in orig_tr.columns:
            return False

        orig_val = orig_tr[col_encoded_name].iloc[0]

        # Flip the label of row 0
        y_perturbed = target_series.copy()
        y_perturbed.iloc[0] = 1 - y_perturbed.iloc[0]

        perturbed_tr, _, _ = encoder_fn(
            train_df=train_df.copy(),
            val_df=val_df.copy(),
            cat_cols=[cat_col],
            y_train=y_perturbed
        )
        perturbed_val = perturbed_tr[col_encoded_name].iloc[0]

        # Delta must be exactly 0 (machine epsilon)
        delta = abs(float(orig_val) - float(perturbed_val))
        return delta < 1e-12
