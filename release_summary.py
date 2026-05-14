from openai import OpenAI

from utils.config_loader import load_properties

config = load_properties("config/config.properties")
api_key = config["openAI"]
client = OpenAI(api_key=api_key)
enableAI = config["enableAI"]


def generate_release_summary(issues):
    """
    issues: list of dicts with keys:
    - id, title, description, acceptance_criteria, type, status
    """

    formatted_issues = []
    for issue in issues:
        formatted_issues.append(f"""
ID: {issue.get('id')}
Type: {issue.get('type')}
Title: {issue.get('title')}
Description: {issue.get('description')}
Acceptance Criteria: {issue.get('acceptance_criteria')}
Status: {issue.get('status')}
""")

    issues_text = "\n\n".join(formatted_issues)

    prompt = f"""
You are a senior product manager preparing a concise release summary for engineering leadership.

Analyse the Jira issues below and return ONLY the following — no extra commentary:

---

## 🏷️ Release Type: <Major | Minor>
**Major** = contains new customer-facing features or breaking changes.
**Minor** = bug fixes, small enhancements, internal improvements only.
One line justification for your classification.

---

## ⭐ Top 3 Highlights
The 3 most impactful customer-facing changes. One sentence each. Bold the feature name.

---

## 📋 Key Deliverables
- Max 5 bullets. Customer-facing only. Skip bugs, refactoring, infra unless critical.
- Format: **Feature Name** — one sentence on what it does and why it matters.

---

## 💼 Business Value
2-3 sentences max. What does this release mean for the end user or the business?

---

Rules:
- Be concise. No padding.
- If something is not clearly important, leave it out.
- No section should exceed 5 lines.

Jira Issues:
{issues_text}
"""

    def to_bool(val):
        return str(val).strip().lower() in ("true", "1", "yes")

    enableAI_flag = to_bool(enableAI)

    print(enableAI_flag)
    if enableAI_flag:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You create crisp, executive-level release summaries. Be brief. No filler."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content