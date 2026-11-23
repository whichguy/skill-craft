"""Offline consistency checks for the Codybot brief's JSON examples."""

import json
from pathlib import Path
import re
import unittest


BRIEF = Path(__file__).with_name("Codybot-design-prompt.md")
JSON_FENCE = re.compile(r"^```json[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
MEDIA_TYPES = {"image", "pdf", "audio"}
REST_FIELDS = {"deliveryState", "contentHref"}


class CodybotBriefTest(unittest.TestCase):
    def test_json_examples_describe_the_same_exchange_and_media(self):
        markdown = BRIEF.read_text(encoding="utf-8")
        examples = []
        for match in JSON_FENCE.finditer(markdown):
            line_number = markdown.count("\n", 0, match.start()) + 1
            try:
                example = json.loads(match[1])
            except json.JSONDecodeError as error:
                self.fail(f"Invalid JSON example at {BRIEF.name}:{line_number}: {error}")
            if isinstance(example, dict):
                examples.append(example)

        (transcript,) = [example for example in examples if "messages" in example]
        (assistant,) = [message for message in transcript["messages"] if message["role"] == "assistant"]
        (user,) = [
            message for message in transcript["messages"]
            if message["role"] == "user" and message["turnId"] == assistant["turnId"]
        ]
        (rest,) = [
            example for example in examples
            if example.get("role") == "assistant" and example.get("id") == assistant["id"]
        ]

        for field in ("id", "turnId", "runId", "role", "presentationRef"):
            self.assertEqual(rest[field], assistant[field], field)
        projected_parts = [
            {key: value for key, value in part.items() if key not in REST_FIELDS}
            for part in rest["parts"]
        ]
        self.assertEqual(projected_parts, assistant["parts"])

        # In this worked exchange, the photo, PDF and audio all contribute
        # to every generated media part. Other conversations can differ.
        inputs = [part for part in user["parts"] if part["type"] in MEDIA_TYPES]
        self.assertCountEqual([part["type"] for part in inputs], MEDIA_TYPES)
        source_ids = {part["assetId"] for part in inputs}
        self.assertEqual(len(source_ids), len(MEDIA_TYPES))

        outputs = [part for part in rest["parts"] if part["type"] in MEDIA_TYPES]
        self.assertCountEqual([part["type"] for part in outputs], MEDIA_TYPES)
        for part in outputs:
            with self.subTest(part=part["partId"]):
                self.assertCountEqual(part["derivedFrom"], source_ids)
                self.assertEqual(part["deliveryState"], "available")
                self.assertEqual(
                    part["contentHref"],
                    f"/services/apexrest/codybot/v1/conversations/{transcript['conversationId']}"
                    f"/messages/{assistant['id']}/parts/{part['partId']}/content",
                )


if __name__ == "__main__":
    unittest.main()
