import { createElement, Loader } from "lucide";

export function initAddLoad() {
  const formsToAddLoad = document.querySelectorAll<HTMLElement>(
    "form[data-jswc-add-load]",
  );
  const anchorsToAddLoad = document.querySelectorAll<HTMLAnchorElement>(
    "a[data-jswc-add-load]",
  );

  const loader = createElement(Loader);
  loader.classList.add("animate-spin");

  formsToAddLoad.forEach((form) => {
    const submitButton = form.querySelector<HTMLElement>(
      "button[type='submit']",
    );
    if (!submitButton) return;

    form.addEventListener("submit", () => {
      load(submitButton, loader);
    });
  });

  anchorsToAddLoad.forEach((a) => {
    a.addEventListener("click", () => {
      load(a, loader);
    });
  });
}

function load(element: HTMLElement, loader: SVGElement) {
  element.setAttribute("disabled", "true");
  element.classList.add("cursor-not-allowed");
  element.textContent = "";
  element.append(loader);
}
