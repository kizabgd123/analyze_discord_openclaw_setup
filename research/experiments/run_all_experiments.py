#!/usr/bin/env python3
"""
Master experiment runner for Discord OpenClaw research
"""

import subprocess
import os
import time
from pathlib import Path

EXPERIMENTS = [
    "engagement_study",
    "safety_study", 
    "knowledge_study",
    "ablation_study"
]

def run_all_experiments():
    """Run all experiments in sequence"""
    print("Starting experiment suite for Discord OpenClaw research")
    print("=" * 60)
    
    results = {}
    
    for exp_name in EXPERIMENTS:
        script_path = Path(f"./experiments/run_{exp_name}.py")
        if script_path.exists():
            print(f"\nRunning {{exp_name}}...")
            start_time = time.time()
            
            try:
                result = subprocess.run(
                    ["python3", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1 hour timeout per experiment
                )
                
                elapsed = time.time() - start_time
                results[exp_name] = {{
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration": elapsed,
                    "success": result.returncode == 0
                }}
                
                if result.returncode == 0:
                    print(f"✓ {{exp_name}} completed in {{elapsed:.1f}}s")
                else:
                    print(f"✗ {{exp_name}} failed after {{elapsed:.1f}}s")
                    print(f"  stderr: {{result.stderr[:200]}}...")
                    
            except subprocess.TimeoutExpired:
                results[exp_name] = {{
                    "timeout": True,
                    "duration": 3600,
                    "success": False
                }}
                print(f"✗ {{exp_name}} timed out after 1 hour")
            except Exception as e:
                results[exp_name] = {{
                    "error": str(e),
                    "duration": time.time() - start_time,
                    "success": False
                }}
                print(f"✗ {{exp_name}} failed with error: {{e}}")
        else:
            print(f"⚠ Experiment script not found: {{script_path}}")
    
    # Summary
    print("\n" + "=" * 60)
    print("EXPERIMENT SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results.values() if r.get("success", False))
    total = len([r for r in results.values() if "error" not in r or not r.get("timeout", False)])
    
    print(f"Successful experiments: {{successful}}/{{total}}")
    
    for exp_name, result in results.items():
        if result.get("success", False):
            status = "✓ PASS"
        elif result.get("timeout", False):
            status = "⏰ TIMEOUT"
        else:
            status = "✗ FAIL"
        print(f"  {{status}} {{exp_name}}")
    
    # Save summary
    import json
    from datetime import datetime
    summary_file = Path("./results/experiment_summary.json")
    with open(summary_file, 'w') as f:
        json.dump({{
            "timestamp": datetime.now().isoformat(),
            "total_experiments": len(EXPERIMENTS),
            "successful": successful,
            "results": results
        }}, f, indent=2)
    
    print(f"\nDetailed summary saved to {{summary_file}}")

if __name__ == "__main__":
    run_all_experiments()
