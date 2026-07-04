export class Sidebar {
  constructor(private container: HTMLElement) {}

  render() {
    this.container.innerHTML = `<aside class="sidebar"></aside>`;
  }
}
