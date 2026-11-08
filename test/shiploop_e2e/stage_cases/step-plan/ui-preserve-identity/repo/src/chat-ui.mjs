export const SEEDED_CONVERSATIONS = [
  {
    id: "mira",
    name: "Mira Chen",
    initials: "MC",
    detail: "Product design",
    messages: [
      { author: "Mira Chen", text: "I added the first pass of the navigation notes." },
      { author: "You", text: "Thanks. I will review them this afternoon." }
    ]
  },
  {
    id: "sam",
    name: "Sam Ortiz",
    initials: "SO",
    detail: "Research",
    messages: [
      { author: "Sam Ortiz", text: "The interview themes are ready to compare." },
      { author: "You", text: "Great. I will add the summary to our notes." }
    ]
  },
  {
    id: "studio",
    name: "Studio Team",
    initials: "ST",
    detail: "Project room",
    messages: [
      { author: "Ari Bell", text: "The prototype review is set for Thursday." },
      { author: "You", text: "I will bring the revised screens." }
    ]
  }
];

export function createChatState() {
  return {
    activeConversationId: SEEDED_CONVERSATIONS[0].id,
    conversations: SEEDED_CONVERSATIONS.map((conversation) => ({
      ...conversation,
      messages: conversation.messages.map((message) => ({ ...message }))
    }))
  };
}

export function selectConversation(state, conversationId) {
  if (!state.conversations.some((conversation) => conversation.id === conversationId)) {
    throw new RangeError("unknown conversation");
  }
  return { ...state, activeConversationId: conversationId };
}

export function appendLocalMessage(state, conversationId, text) {
  const body = String(text).trim();
  if (!body) return state;
  if (!state.conversations.some((conversation) => conversation.id === conversationId)) {
    throw new RangeError("unknown conversation");
  }
  return {
    ...state,
    conversations: state.conversations.map((conversation) => conversation.id === conversationId
      ? { ...conversation, messages: [...conversation.messages, { author: "You", text: body }] }
      : conversation)
  };
}

export function activeConversation(state) {
  return state.conversations.find((conversation) => conversation.id === state.activeConversationId);
}

if (typeof document !== "undefined") {
  const list = document.querySelector("#conversation-list");
  const title = document.querySelector("#conversation-title");
  const preview = document.querySelector("#conversation-preview");
  const thread = document.querySelector("#message-thread");
  const composer = document.querySelector("#composer");
  const input = document.querySelector("#message-input");
  const status = document.querySelector("#chat-status");
  let state = createChatState();

  function renderConversations() {
    list.replaceChildren();
    for (const conversation of state.conversations) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.className = "conversation-item";
      button.type = "button";
      button.setAttribute("aria-current", String(conversation.id === state.activeConversationId));
      const avatar = document.createElement("span");
      avatar.className = "avatar";
      avatar.setAttribute("aria-hidden", "true");
      avatar.textContent = conversation.initials;
      const copy = document.createElement("span");
      copy.className = "conversation-copy";
      const name = document.createElement("span");
      name.className = "conversation-name";
      name.textContent = conversation.name;
      const snippet = document.createElement("span");
      snippet.className = "conversation-snippet";
      snippet.textContent = conversation.messages[conversation.messages.length - 1]?.text ?? "No messages yet";
      copy.append(name, snippet);
      button.append(avatar, copy);
      button.addEventListener("click", () => {
        state = selectConversation(state, conversation.id);
        render();
        status.textContent = `Opened ${conversation.name}`;
      });
      item.append(button);
      list.append(item);
    }
  }

  function renderThread() {
    const conversation = activeConversation(state);
    title.textContent = conversation.name;
    preview.textContent = conversation.detail;
    thread.replaceChildren();
    for (const message of conversation.messages) {
      const bubble = document.createElement("article");
      bubble.className = "message" + (message.author === "You" ? " message--outgoing" : "");
      const author = document.createElement("span");
      author.className = "message-author";
      author.textContent = message.author;
      const body = document.createElement("p");
      body.className = "message-body";
      body.textContent = message.text;
      bubble.append(author, body);
      thread.append(bubble);
    }
  }

  function render() {
    renderConversations();
    renderThread();
  }

  composer.addEventListener("submit", (event) => {
    event.preventDefault();
    const conversationId = state.activeConversationId;
    const text = input.value;
    if (!text.trim()) return;
    state = appendLocalMessage(state, conversationId, text);
    input.value = "";
    render();
    status.textContent = "Message added locally";
    input.focus();
  });

  render();
}
