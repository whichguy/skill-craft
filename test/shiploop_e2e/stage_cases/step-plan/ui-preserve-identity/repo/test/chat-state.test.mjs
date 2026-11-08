import test from "node:test";
import assert from "node:assert/strict";
import {
  activeConversation,
  appendLocalMessage,
  createChatState,
  selectConversation
} from "../src/chat-ui.mjs";

test("the seeded local conversations open with their own messages", () => {
  const state = createChatState();
  assert.equal(state.activeConversationId, "mira");
  assert.equal(activeConversation(state).name, "Mira Chen");
  assert.match(activeConversation(state).messages[0].text, /navigation notes/);
});

test("selecting a seeded conversation changes the active local message thread", () => {
  const state = selectConversation(createChatState(), "sam");
  assert.equal(activeConversation(state).name, "Sam Ortiz");
  assert.match(activeConversation(state).messages[0].text, /interview themes/);
});

test("sending adds a message to that conversation locally", () => {
  const state = createChatState();
  const originalState = {
    activeConversationId: state.activeConversationId,
    conversations: state.conversations.map((conversation) => ({
      ...conversation,
      messages: conversation.messages.map((message) => ({ ...message }))
    }))
  };
  const next = appendLocalMessage(state, "mira", "  Review note  ");
  assert.equal(activeConversation(next).messages.at(-1).text, "Review note");
  assert.deepEqual(state, originalState);
});

test("blank messages do not change local conversation state", () => {
  const state = createChatState();
  assert.equal(appendLocalMessage(state, "mira", "   "), state);
});
