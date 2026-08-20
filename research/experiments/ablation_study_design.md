# Component Ablation Study

**Hypothesis:** Each component (proactive, approval, NLM) contributes uniquely to overall performance

## Variables
- Independent: system_configuration (full, minus_proactive, minus_approval, minus_NLM, reactive_only)
- Dependent: overall_performance_score, user_satisfaction, task_success_rate
- Control: user_sample, task_set

## Experimental Protocol
1. Test 5 system configurations with same user base
2. Use Latin square design to control for order effects
3. Measure composite performance metric
4. Conduct user interviews about missing components
