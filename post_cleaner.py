"""
Post Cleaning and Normalization utility for LinkedIn & Telegram publishing.
Ensures zero rogue characters, strips erroneous escape backslashes, fixes runaway /n or \\n,
and guarantees clean paragraph spacing and unbroken numbered lists.
"""

import re

UNWANTED_ESCAPES = [
    (r"\(", "("),
    (r"\)", ")"),
    (r"\[", "["),
    (r"\]", "]"),
    (r"\{", "{"),
    (r"\}", "}"),
    (r"\|", "|"),
    (r"\_", "_"),
    (r"\*", "*"),
    (r"\#", "#"),
    (r'\"', '"'),
    (r"\'", "'"),
    (r"\<", "<"),
    (r"\>", ">"),
    (r"\@", "@"),
    (r"\/", "/"),
    (r"\-", "-"),
    (r"\+", "+"),
    (r"\=", "="),
    (r"\.", "."),
    (r"\!", "!"),
    (r"\?", "?"),
    (r"\:", ":"),
    (r"\;", ";"),
    (r"\,", ","),
]


def clean_linkedin_post_text(text: str) -> str:
    """
    Cleanses and formats post text for pristine presentation on LinkedIn and Telegram:
    1. Converts literal '\\n', '\\r\\n', '/n' into real newlines.
    2. Strips erroneous backslash escaping from brackets, parentheses, pipes, etc.
    3. Cleans stray slashes and backslashes.
    4. Automatically ensures numbered lists (1-, 2-, 3-, 1️⃣, 2️⃣, •) start on fresh lines with empty line spacing.
    5. Normalizes excessive empty lines while preserving deliberate paragraph breaks.
    """
    if not text:
        return ""

    cleaned = str(text)

    # 1. Unescape literal newlines and carriage returns
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Replace literal string '\n' (escaped by json or LLM) with actual newline
    cleaned = re.sub(r'(?<!\\)\\n', '\n', cleaned)
    cleaned = cleaned.replace("\\\\n", "\n")

    # Replace rogue '/n' when used as an intended newline separator
    # e.g., "نص الخبر/n1- النقطة الأولى" or "نص الخبر /n 2- النقطة"
    cleaned = re.sub(r'[\s]*/n[\s]*', '\n\n', cleaned)

    # 2. Strip unwanted escape backslashes via straightforward string replacement
    for raw_escaped, clean_char in UNWANTED_ESCAPES:
        cleaned = cleaned.replace(raw_escaped, clean_char)

    # Clean double backslashes
    cleaned = cleaned.replace(r"\\", "")

    # Also remove any remaining lone backslash before standard alphanumeric or punctuation
    cleaned = re.sub(r'\\([a-zA-Z0-9_\-\.\:\/])', r'\1', cleaned)

    # 3. Fix numbered lists and bullet points running together without line breaks:
    # Matches patterns like: "نهاية جملة. 1- بداية نقطة" or "نص 2- النقطة التالية"
    # Supported list markers: 1- , 1. , 1) , 1️⃣ , • , - , 🔹 , 📌
    list_marker_pattern = re.compile(
        r'(?<=[^\n])\s*([0-9]{1,2}[\-\.\)]|[1-9]️⃣|🔟|[•▪️▫️🔹])\s+'
    )
    cleaned = list_marker_pattern.sub(r'\n\n\1 ', cleaned)

    # Also handle Arabic hyphen/dash in numbered lists: "1ـ " or "1 - "
    arabic_list_pattern = re.compile(
        r'(?<=[^\n])\s*([0-9]{1,2}\s*[\u0640\-\–\—]\s*)'
    )
    cleaned = arabic_list_pattern.sub(r'\n\n\1', cleaned)

    # 4. Clean up whitespace per line
    lines = [line.rstrip() for line in cleaned.split("\n")]
    cleaned = "\n".join(lines)

    # 5. Normalize multiple consecutive blank lines to at most two
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()
