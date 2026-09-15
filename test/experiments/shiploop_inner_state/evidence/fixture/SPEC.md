# Required behavior

Implement clean_lines(text) in lines.py. Accept str only; otherwise raise
TypeError. Split using Python splitlines(), strip each resulting line, discard
empty strings, and preserve order and duplicates. Empty or whitespace-only text
returns []. For example ' a \n \n b\n a ' returns ['a', 'b', 'a'].
Keep the function small and stdlib-only. This specification is immutable.
