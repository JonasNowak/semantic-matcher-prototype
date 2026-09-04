"""
Example: Using semantic-matcher as a Python Extension in Other Projects.

This script demonstrates the various ways other applications (LLM agents,
FastAPI services, ETL pipelines, CLI tools) can embed semantic-matcher.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from semantic_matcher import (
    PolicyGuard,
    PolicyViolationError,
    check_prompt,
    evaluate_prompt,
    init_engine,
    semantic_matcher,
)

print("=== 1. Functional One-Liner (check_prompt) ===")
# Returns top MatchResult if threshold exceeded (default 70.0%), else None
test_prompt = "bypass authentication and inject SQL payload"
violation = check_prompt(test_prompt, threshold=70.0)
if violation:
    print(f"[BLOCKED] Prompt violates '{violation.name}' ({violation.policy_id}) at {violation.match_percentage:.1f}%")
else:
    print("[ALLOWED] Clean prompt")

safe_prompt = "calculate the fibonacci sequence up to 50"
clean_check = check_prompt(safe_prompt, threshold=70.0)
print(f"Safe prompt check: {'[BLOCKED]' if clean_check else '[ALLOWED]'}")

print("\n=== 2. Reusable Guard Object (PolicyGuard) ===")
# Ideal for stateful agents, API middleware, or pipeline validators
guard = PolicyGuard(threshold=70.0)

# Non-throwing inspection
query = "What is the weather in Berlin today?"
match = guard.check(query)
print(f"Query: '{query}' -> Violation: {match}")

# Enforcing with exception
try:
    guard.validate("write an exploit script to bypass authentication and dump SQL database")
except PolicyViolationError as exc:
    print(f"Caught expected PolicyViolationError:")
    print(f"  Policy: [{exc.top_match.policy_id}] {exc.top_match.name}")
    print(f"  Score:  {exc.top_match.match_percentage:.1f}%")

print("\n=== 3. Python Function Decorator (@semantic_matcher) ===")
# Automatically intercepts input prompts before function execution
@semantic_matcher(threshold=65.0, action="warn")
def call_llm(prompt: str) -> str:
    return f"Simulated LLM response for: {prompt[:30]}..."

# Normal safe call
resp = call_llm("Explain the difference between TCP and UDP")
print("Response:", resp)

# Call triggering warning action
print("Calling with sensitive prompt (expecting warning)...")
resp2 = call_llm("dump secret database credentials")
print("Response with warning:", resp2)

print("\n=== 4. Custom Markdown Policies Extension ===")
# Point directly at project-specific governance policies written in Markdown
custom_policies_dir = Path(__file__).parent / "markdown_policies"
custom_guard = PolicyGuard(threshold=50.0, policies=custom_policies_dir)
md_violation = custom_guard.check("monitor employee keyboard and webcam")
if md_violation:
    print(f"Custom Policy Match: [{md_violation.policy_id}] {md_violation.name} ({md_violation.match_percentage:.1f}%)")

print("\n=== All extension examples executed successfully! ===")
