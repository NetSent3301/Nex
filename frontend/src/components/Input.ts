export class Input {
  constructor(private container: HTMLElement) {}

  render() {
    this.container.innerHTML = `<textarea class="chat-input" rows="3"></textarea>`;
  }
}
