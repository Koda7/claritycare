"""
LLM Structuring Pipeline: uses OpenAI gpt-4o to convert extracted text into JSON decision trees.
"""
import json
import hashlib
import os
import sys
import time

from openai import OpenAI
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection, init_db
from pipeline.extract import extract_for_policy
from pipeline.schemas import StructuredPolicy

OSCAR_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "oscar.json"
)
PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfs")
MODEL = "gpt-4o"
MAX_LLM_RETRIES = 1


def load_few_shot_example() -> str:
    with open(OSCAR_JSON_PATH) as f:
        return f.read()


SYSTEM_PROMPT = """You are a medical policy document analyst. Your job is to extract medical necessity criteria from insurance policy documents and structure them into JSON decision trees.

You must output valid JSON matching this exact schema:
{
  "title": "string - the policy/guideline title",
  "insurance_name": "Oscar Health",
  "rules": {
    "rule_id": "string - hierarchical ID like 1, 1.1, 1.1.1",
    "rule_text": "string - the criteria text",
    "operator": "AND or OR (only for non-leaf nodes)",
    "rules": [array of child rule nodes (only for non-leaf nodes)]
  }
}

Rules for structuring:
- Leaf nodes have only rule_id and rule_text (no operator, no rules array)
- Non-leaf nodes MUST have operator ("AND" or "OR") and a rules array
- Use "AND" when ALL criteria must be met
- Use "OR" when ANY ONE of the criteria suffices
- rule_id should be hierarchical (1, 1.1, 1.2, 1.2.1, etc.)
- Extract ONLY the initial/first-time authorization criteria, not continuation/renewal criteria
- Preserve the medical terminology exactly as written in the source"""


def build_user_prompt(policy_title: str, extracted_text: str, few_shot: str) -> str:
    return f"""Here is an example of the expected output format:

{few_shot}

---

Now extract the initial medical necessity criteria from the following policy document into the same JSON structure.

Policy: {policy_title}

Document text:
{extracted_text[:12000]}

Output ONLY the JSON object, no other text."""


def build_retry_prompt(policy_title: str, extracted_text: str, few_shot: str, error: str) -> str:
    return f"""Here is an example of the expected output format:

{few_shot}

---

Your previous attempt to structure this policy had a validation error: {error}

Please fix the output. Extract the initial medical necessity criteria from the following policy document into the correct JSON structure.

Policy: {policy_title}

Document text:
{extracted_text[:12000]}

Output ONLY the JSON object, no other text."""


def call_llm(system: str, user: str) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=4096,
    )
    return response.choices[0].message.content


def structure_policy(policy_id: int, title: str, pdf_path: str) -> bool:
    """Structure a single policy. Returns True on success."""
    print(f"  Extracting text from PDF...")
    try:
        full_text, initial_text = extract_for_policy(pdf_path)
    except FileNotFoundError as e:
        print(f"  SKIP: {e}")
        return False
    except Exception as e:
        print(f"  ERROR extracting text: {e}")
        return False

    if len(initial_text.strip()) < 100:
        print(f"  SKIP: Extracted text too short ({len(initial_text)} chars)")
        return False

    few_shot = load_few_shot_example()
    prompt_hash = hashlib.md5((SYSTEM_PROMPT + initial_text[:1000]).encode()).hexdigest()[:8]

    # First attempt
    print(f"  Calling {MODEL}...")
    user_prompt = build_user_prompt(title, initial_text, few_shot)
    raw_json = call_llm(SYSTEM_PROMPT, user_prompt)

    # Validate
    validation_error = None
    structured_json = None
    try:
        parsed = StructuredPolicy.model_validate_json(raw_json)
        structured_json = parsed.model_dump_json()
    except (ValidationError, json.JSONDecodeError) as e:
        validation_error = str(e)
        print(f"  Validation failed, retrying: {validation_error[:100]}")

        # Retry once with error feedback
        retry_prompt = build_retry_prompt(title, initial_text, few_shot, validation_error)
        raw_json = call_llm(SYSTEM_PROMPT, retry_prompt)
        try:
            parsed = StructuredPolicy.model_validate_json(raw_json)
            structured_json = parsed.model_dump_json()
            validation_error = None
        except (ValidationError, json.JSONDecodeError) as e2:
            validation_error = str(e2)
            print(f"  Retry also failed: {validation_error[:100]}")

    # Store result
    conn = get_connection()
    conn.execute(
        """INSERT OR REPLACE INTO structured_policies
           (policy_id, extracted_text, structured_json, llm_model, llm_prompt_hash, validation_error)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            policy_id,
            initial_text[:50000],  # Cap stored text
            structured_json,
            MODEL,
            prompt_hash,
            validation_error,
        ),
    )
    conn.commit()
    conn.close()

    if structured_json:
        print(f"  SUCCESS")
        return True
    else:
        print(f"  STORED WITH ERROR: {validation_error[:80]}")
        return False


def run(limit: int = 15):
    """Structure at least 10 policies (attempt up to `limit`)."""
    init_db()

    conn = get_connection()
    # Get policies with successful downloads that haven't been structured yet
    policies = conn.execute("""
        SELECT p.id, p.title, d.stored_location
        FROM policies p
        JOIN downloads d ON d.policy_id = p.id AND d.http_status = 200
        LEFT JOIN structured_policies sp ON sp.policy_id = p.id
        WHERE sp.id IS NULL AND d.stored_location IS NOT NULL
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    print("=" * 60)
    print("LLM STRUCTURING PIPELINE")
    print("=" * 60)
    print(f"Policies to structure: {len(policies)}")
    print("-" * 60)

    success_count = 0
    for i, policy in enumerate(policies, 1):
        print(f"\n[{i}/{len(policies)}] {policy['title']}")
        try:
            if structure_policy(policy["id"], policy["title"], policy["stored_location"]):
                success_count += 1
        except Exception as e:
            print(f"  FATAL ERROR: {e}")

        # Brief pause between LLM calls
        if i < len(policies):
            time.sleep(0.5)

    print("-" * 60)
    print(f"Successfully structured: {success_count}/{len(policies)}")
    print("=" * 60)
    return success_count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15, help="Max policies to attempt")
    args = parser.parse_args()
    run(limit=args.limit)
