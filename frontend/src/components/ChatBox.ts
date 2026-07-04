export class ChatBox {
  constructor(private container: HTMLElement) {}

  render() {
    this.container.innerHTML = `<div class="chat-box"></div>`;
  }
}
