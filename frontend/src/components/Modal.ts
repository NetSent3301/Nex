export class Modal {
  constructor(private container: HTMLElement) {}

  show(content: string) {
    this.container.innerHTML = `<div class="modal-overlay"><div class="modal">${content}</div></div>`;
  }

  hide() {
    this.container.innerHTML = "";
  }
}
