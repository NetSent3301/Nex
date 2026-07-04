document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "k") {
    e.preventDefault();
    document.querySelector<HTMLInputElement>("#search")?.focus();
  }
});
