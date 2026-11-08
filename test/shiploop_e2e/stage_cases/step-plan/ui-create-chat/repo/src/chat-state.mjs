export function createChatState() {
  return {
    activeId: "maya",
    conversations: [
      { id: "maya", title: "Maya Chen", messages: ["Can you review the launch notes?", "Yes, I will send a short summary."] },
      { id: "team", title: "Product team", messages: ["The board is ready for a quick look."] },
    ],
  };
}

export function selectConversation(state, id) {
  if (!state.conversations.some((conversation) => conversation.id === id)) return state;
  return { ...state, activeId: id };
}

export function sendMessage(state, text) {
  const message = String(text).trim();
  if (!message) return state;
  return {
    ...state,
    conversations: state.conversations.map((conversation) => conversation.id === state.activeId
      ? { ...conversation, messages: [...conversation.messages, message] }
      : conversation),
  };
}
