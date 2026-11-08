import { createChatState, selectConversation, sendMessage } from "./chat-state.mjs";

let state = createChatState();
const list = document.querySelector("#conversation-list");
const title = document.querySelector("#active-conversation");
const messages = document.querySelector("#message-list");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const status = document.querySelector("#chat-status");

function activeConversation() {
  return state.conversations.find((conversation) => conversation.id === state.activeId);
}

function render() {
  list.replaceChildren();
  for (const conversation of state.conversations) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.conversation = conversation.id;
    button.textContent = conversation.title;
    button.setAttribute("aria-current", conversation.id === state.activeId ? "page" : "false");
    button.addEventListener("click", () => {
      state = selectConversation(state, conversation.id);
      status.textContent = "Conversation opened: " + conversation.title;
      render();
    });
    list.append(button);
  }
  const conversation = activeConversation();
  title.textContent = conversation.title;
  messages.replaceChildren();
  for (const message of conversation.messages) {
    const item = document.createElement("li");
    item.textContent = message;
    messages.append(item);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) {
    status.textContent = "Write a message first";
    return;
  }
  state = sendMessage(state, message);
  input.value = "";
  status.textContent = "Message sent";
  render();
  input.focus();
});

render();
