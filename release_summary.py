from openai import OpenAI

from utils.config_loader import load_properties

config = load_properties("config/config.properties")
api_key = config["openAI"]
client = OpenAI(api_key=api_key)
enableAI=config["enableAI"]


def generate_release_summary(issues):
    """
    issues: list of dicts with keys:
    - id, title, description, acceptance_criteria, type, status
    """

    # Prepare clean input for AI
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
You are a senior product manager preparing release notes.

From the Jira issues below:
- Identify ONLY important, customer-facing features
- Ignore bugs, refactoring, internal/infra work unless critical
- Group related items into themes

Return:
1. Key Features Delivered (5-7 bullets)
2. Customer Impact (business value)
3. Optional: Technical Highlights (only if important)

Keep it concise, leadership-ready.

Jira Issues:
{issues_text}
"""

    # GEN AI
    def to_bool(val):
        return str(val).strip().lower() in ("true", "1", "yes")

    enableAI_flag =  to_bool(enableAI)

    print(enableAI_flag)
    if enableAI_flag:
        response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You create crisp, executive-level release summaries."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
        )

        return response.choices[0].message.content

