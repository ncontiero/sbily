export function initSwitch(): void {
  const switchButtons =
    document.querySelectorAll<HTMLElement>("[data-jswc-switch]");

  switchButtons.forEach((button) => {
    const { state } = button.dataset;

    button.setAttribute("role", "switch");
    button.setAttribute("aria-checked", "false");
    button.dataset.state = state ?? "unchecked";
    button.classList.add("switch-button");

    const switchThumb =
      button.querySelector<HTMLElement>(".switch-thumb") ||
      document.createElement("span");
    switchThumb.classList.add("switch-thumb");
    switchThumb.dataset.state = state ?? "unchecked";
    button.append(switchThumb);

    const switchName = button.dataset.name;
    if (switchName != null) {
      const switchInput = document.createElement("input");
      switchInput.classList.add("hidden");
      switchInput.type = "checkbox";
      switchInput.hidden = true;
      switchInput.name = switchName;
      switchInput.checked = !!(state === "checked");
      button.append(switchInput);
    }

    button.addEventListener("click", () => Switch(button));
  });
}

export function Switch(targetElement: HTMLElement) {
  const switchThumb = targetElement.querySelector<HTMLElement>(".switch-thumb");
  const switchInput = targetElement.querySelector<HTMLInputElement>("input");
  if (!switchThumb) return;

  if (targetElement.dataset.state === "unchecked") {
    targetElement.dataset.state = "checked";
    targetElement.setAttribute("aria-checked", "true");
    switchThumb.dataset.state = "checked";
    switchThumb.setAttribute("aria-checked", "true");
    if (switchInput) switchInput.checked = true;
  } else {
    targetElement.dataset.state = "unchecked";
    targetElement.setAttribute("aria-checked", "false");
    switchThumb.dataset.state = "unchecked";
    switchThumb.setAttribute("aria-checked", "false");
    if (switchInput) switchInput.checked = false;
  }
}
