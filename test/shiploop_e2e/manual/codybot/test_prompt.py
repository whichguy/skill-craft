"""Offline consistency checks for the Codybot brief's JSON examples."""

import json
from pathlib import Path
import re
import unittest


BRIEF = Path(__file__).with_name("Codybot-design-prompt.md")
JSON_FENCE = re.compile(r"^```json[ \t]*\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
MEDIA_TYPES = {"image", "pdf", "audio"}
REST_FIELDS = {"deliveryState", "contentHref"}
REST_ROOT = "/services/apexrest/codybot/v1"


class CodybotBriefTest(unittest.TestCase):
    def read_json_examples(self):
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
        return examples

    def test_json_examples_describe_the_same_exchange_and_media(self):
        examples = self.read_json_examples()
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

    def test_tool_turn_examples_follow_the_same_run(self):
        fixtures = [
            example for example in self.read_json_examples()
            if example.get("fixture") == "codybot-tool-turn-v1"
        ]
        self.assertEqual(len(fixtures), 1, "Expected one codybot-tool-turn-v1 JSON example")
        (fixture,) = fixtures
        lightning = fixture["lightning"]["request"]
        rest = fixture["rest"]
        receipt = fixture["receipt"]
        snapshot = fixture["snapshot"]
        assistant = fixture["assistantMessage"]

        with self.subTest(boundary="Lightning and REST"):
            conversation_id = lightning["conversationId"]
            self.assertEqual(rest["path"], f"{REST_ROOT}/conversations/{conversation_id}/turns")
            self.assertEqual(set(lightning), {"conversationId", "sessionHandle", "requestKey", "parts"})
            self.assertEqual(
                rest["body"],
                {field: value for field, value in lightning.items() if field != "conversationId"},
                "Lightning and REST must submit identical content and retry identity",
            )
            self.assertEqual(receipt["conversationId"], conversation_id)
            self.assertEqual(receipt["state"], "queued")
            self.assertEqual(receipt["statusUrl"], f"{REST_ROOT}/runs/{receipt['runId']}")
            for field in (
                "instanceId", "bindingId", "sessionId", "epoch", "expiresAt",
                "conversationId", "turnId", "runId",
            ):
                self.assertEqual(snapshot[field], receipt[field], f"Snapshot changed receipt {field}")
            self.assertGreater(snapshot["revision"], receipt["revision"])
            self.assertEqual(snapshot["state"], "completed")
            self.assertEqual(assistant["id"], snapshot["finalMessageId"])
            self.assertEqual(assistant["role"], "assistant")

        manifest = fixture["manifest"]
        tool_receipt = fixture["toolReceipt"]
        openai = fixture["openai"]
        claude = fixture["claude"]
        with self.subTest(boundary="Tool declaration and receipt"):
            self.assertEqual(len(manifest["tools"]), 1)
            (definition,) = manifest["tools"]
            self.assertEqual(tool_receipt["runId"], receipt["runId"])
            self.assertEqual(tool_receipt["manifestRevision"], manifest["revision"])
            for field in ("toolId", "version"):
                self.assertEqual(tool_receipt[field], definition[field], f"Tool receipt changed {field}")
            for field in ("invocationId", "stepId", "attemptId"):
                self.assertTrue(tool_receipt[field], f"Missing {field} in tool receipt")
            self.assertEqual(definition["alias"], "timer_read")
            schema = definition["inputSchema"]
            self.assertEqual(schema["type"], "object")
            self.assertEqual(set(schema["properties"]), {"timerId"}, "Only timerId is model-supplied")
            self.assertEqual(schema["properties"]["timerId"]["type"], "string")
            self.assertEqual(schema["required"], ["timerId"])
            self.assertIs(schema["additionalProperties"], False)

            for request, schema_field, extra in (
                (openai["request"], "parameters", {"type", "strict"}),
                (claude["request"], "input_schema", {"strict"}),
            ):
                self.assertEqual(len(request["tools"]), 1)
                (tool,) = request["tools"]
                self.assertLessEqual(
                    set(tool), {"name", "description", schema_field} | extra,
                    f"Private tool metadata crossed the {schema_field} boundary",
                )
                self.assertEqual(tool["name"], definition["alias"])
                self.assertEqual(tool["description"], definition["description"])
                self.assertEqual(tool[schema_field], schema)

        with self.subTest(boundary="User input projection"):
            self.assertTrue(lightning["parts"])
            for request, messages_field, text_type in (
                (openai["request"], "input", "input_text"),
                (claude["request"], "messages", "text"),
            ):
                self.assertTrue(request["model"])
                self.assertEqual(
                    request[messages_field],
                    [{"role": "user", "content": [
                        {"type": text_type, "text": part["text"]} for part in lightning["parts"]
                    ]}],
                    f"{messages_field} changed the submitted user parts",
                )
            self.assertEqual(openai["request"]["instructions"], claude["request"]["system"])
            self.assertGreater(claude["request"]["max_tokens"], 0)

        with self.subTest(boundary="Provider tool calls and continuation"):
            arguments = tool_receipt["arguments"]
            self.assertEqual(set(arguments), {"timerId"}, "Unexpected model input field")
            result = tool_receipt["result"]
            self.assertEqual(set(result), {"ok", "data"})
            self.assertIs(result["ok"], True)
            self.assertEqual(set(result["data"]), {"timerId", "state", "nextFireAt"})
            self.assertEqual(result["data"]["timerId"], arguments["timerId"])

            self.assertIs(openai["request"]["store"], False)
            self.assertEqual(openai["request"]["tool_choice"], "auto")
            self.assertEqual(openai["request"]["tools"][0]["type"], "function")
            calls = [item for item in openai["output"] if item["type"] == "function_call"]
            self.assertEqual(len(calls), 1, "Expected one OpenAI function_call")
            (call,) = calls
            self.assertEqual(call["name"], "timer_read")
            self.assertNotEqual(call["id"], call["call_id"], "Item ID and call ID must differ")
            openai_call_id = call["call_id"]
            self.assertEqual(json.loads(call["arguments"]), arguments)
            continuation = openai["result"]
            self.assertEqual(continuation["type"], "function_call_output")
            self.assertEqual(
                continuation["call_id"], call["call_id"],
                "OpenAI function_call_output must reference the function call ID",
            )
            self.assertEqual(json.loads(continuation["output"]), result)

            self.assertEqual(claude["request"]["tool_choice"], {"type": "auto"})
            response = claude["response"]
            self.assertEqual(response["stop_reason"], "tool_use")
            calls = [block for block in response["content"] if block["type"] == "tool_use"]
            self.assertEqual(len(calls), 1, "Expected one Claude tool_use block")
            (call,) = calls
            self.assertEqual(call["name"], "timer_read")
            self.assertEqual(call["input"], arguments)
            continuation = claude["result"]
            self.assertEqual(continuation["role"], "user")
            self.assertEqual(len(continuation["content"]), 1)
            (block,) = continuation["content"]
            self.assertEqual(block["type"], "tool_result")
            self.assertEqual(
                block["tool_use_id"], call["id"],
                "Claude tool_result must reference the tool_use ID",
            )
            self.assertEqual(json.loads(block["content"]), result)

            for provider, native_call_id in ((openai, openai_call_id), (claude, call["id"])):
                correlation = provider["correlation"]
                self.assertEqual(
                    correlation["providerCallId"], native_call_id,
                    "Correlation must reference the native tool call ID",
                )
                self.assertEqual(correlation["invocationId"], tool_receipt["invocationId"])
                for document in ("request", "result"):
                    payload = json.dumps(provider[document])
                    for field in ("correlation", *correlation):
                        self.assertNotIn(
                            f'"{field}":', payload, f"Private {field} crossed into {document}",
                        )

        with self.subTest(boundary="Final message"):
            self.assertEqual(claude["final"]["stop_reason"], "end_turn")
            self.assertEqual(openai["final"]["status"], "completed")
            messages = [item for item in openai["final"]["output"] if item["type"] == "message"]
            self.assertEqual(len(messages), 1, "Expected one final OpenAI message")
            (message,) = messages
            self.assertEqual(message["role"], "assistant")
            self.assertTrue(assistant["parts"], "Expected final text to render")
            self.assertTrue(all(part["type"] == "text" for part in assistant["parts"]))
            expected = [part["text"] for part in assistant["parts"]]
            for provider, content, text_type in (
                ("OpenAI", message["content"], "output_text"),
                ("Claude", claude["final"]["content"], "text"),
            ):
                self.assertEqual(
                    [block["text"] for block in content if block["type"] == text_type],
                    expected,
                    f"{provider} final text changed when rendered",
                )


if __name__ == "__main__":
    unittest.main()
