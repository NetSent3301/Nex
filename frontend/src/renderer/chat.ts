class ChatHandler {
  private messages: { role: string; content: string }[] = [];

  add(role: string, content: string) {
    this.messages.push({ role, content });
  }

  all() {
    return this.messages;
  }
}

export const chatHandler = new ChatHandler();
