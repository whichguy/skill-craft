import test from "node:test";
import assert from "node:assert/strict";
import { createChatState, selectConversation, sendMessage } from "../src/chat-state.mjs";

test("selecting a seeded conversation changes the active conversation", () => {
  const state = createChatState();
  const next = selectConversation(state, "team");
  assert.equal(next.activeId, "team");
  assert.equal(next.conversations[1].messages[0], "The board is ready for a quick look.");
  assert.equal(state.activeId, "maya");
});

test("unknown conversations leave the state alone", () => {
  const state = createChatState();
  assert.equal(selectConversation(state, "missing"), state);
});

test("sending non-empty text appends to the active local conversation", () => {
  const state = selectConversation(createChatState(), "team");
  const next = sendMessage(state, "  Looks good  ");
  assert.deepEqual(next.conversations[1].messages, ["The board is ready for a quick look.", "Looks good"]);
  assert.deepEqual(next.conversations[0].messages, state.conversations[0].messages);
});

test("empty messages are not appended", () => {
  const state = createChatState();
  assert.equal(sendMessage(state, "  "), state);
});
