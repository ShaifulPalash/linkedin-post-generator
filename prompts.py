"""
STEP 2: Prompt design.

TOKEN-EFFICIENCY NOTE
-----------------------
This prompt is written to be CONCISE, not padded with restated context or
long-winded instructions. Every extra sentence in a system prompt costs
tokens on every single call — with Groq's free tier capped at 12,000 tokens
per minute (see README), a bloated system prompt eats into that budget for
no quality benefit. We keep the instructions tight but complete.

WHY WE ASK FOR A DELIMITER INSTEAD OF JSON
---------------------------------------------
We need to split the generated post from its hashtags. Two common ways to
do this: (a) ask the model for structured JSON output, or (b) ask for plain
text with a simple delimiter line between the two parts. We use (b) here —
a delimiter line costs a few tokens; a JSON schema wrapper costs more
tokens for the same information and adds a parsing failure mode (malformed
JSON) for no real benefit in a single-field-pair case like this. For a
more complex output shape, JSON/structured output would be the better
choice — see the "Testing philosophy" note in README for when to reach for
that instead.

WHY WE GENERATE NATIVELY IN {language} RATHER THAN TRANSLATING AFTER
------------------------------------------------------------------------
Asking the model to write in English and then translate produces stiff,
literally-translated phrasing — idioms and hooks that work in English often
don't translate naturally. Asking it to write natively in the target
language from the start lets it choose phrasing that's actually idiomatic
there, and also costs fewer total tokens than a two-step generate-then-
translate pipeline would.
"""

from langchain_core.prompts import ChatPromptTemplate

HASHTAG_DELIMITER = "---HASHTAGS---"

SYSTEM_INSTRUCTIONS = f"""You are a professional LinkedIn content writer.

Rules:
- Write ENTIRELY in {{language}} (not English translated afterward).
- Start with a short, attention-grabbing hook line (bold claim, surprising
  fact, or direct question) — not a generic intro.
- 2 to 4 short paragraphs (2-4 sentences each). LinkedIn readers skim.
- Professional but approachable tone, not academic or stiff.
- No meta-commentary ("Here is your post:"), no quotation marks around it.

After the post, output exactly this line: {HASHTAG_DELIMITER}
Then 3 to 5 relevant hashtags in {{language}} where that makes sense
(proper nouns/acronyms can stay as-is), space-separated, each starting
with #."""

HUMAN_INSTRUCTIONS = "Topic: {topic}"

linkedin_post_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_INSTRUCTIONS),
        ("human", HUMAN_INSTRUCTIONS),
    ]
)


if __name__ == "__main__":
    # Preview how the template renders — pure string substitution, no LLM
    # call, no API key needed, no tokens spent. Run: python prompts.py
    examples = [
        {"topic": "AI in Healthcare", "language": "English"},
        {"topic": "Remote Work Productivity", "language": "Spanish"},
        {"topic": "The Future of Renewable Energy", "language": "Bengali"},
    ]

    for ex in examples:
        print("=" * 70)
        print(f"topic={ex['topic']!r}  language={ex['language']!r}")
        print("=" * 70)
        rendered = linkedin_post_prompt.format_messages(**ex)
        for msg in rendered:
            print(f"[{msg.type}]\n{msg.content}\n")
