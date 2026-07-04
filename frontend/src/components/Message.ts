export class Message {
  constructor(private container: HTMLElement) {}

  render(role: string, content: string) {
    this.container.innerHTML += `<div class="message message--${role}">${content}</div>`;
  }
}
