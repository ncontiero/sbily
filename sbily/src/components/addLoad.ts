import { createElement, Loader } from "lucide";

export function setLoading(
  element: HTMLElement,
  loader: SVGElement,
  isLoading = true,
  elementContent?: string,
) {
  if (isLoading) {
    element.setAttribute("disabled", "true");
    element.classList.add("cursor-not-allowed");
    element.innerHTML = "";
    element.append(loader);
  } else {
    element.removeAttribute("disabled");
    element.classList.remove("cursor-not-allowed");
    element.innerHTML = elementContent || element.innerHTML;
    element.querySelector("svg")?.remove();
  }
}

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
      setLoading(submitButton, loader);
    });
  });

  anchorsToAddLoad.forEach((a) => {
    a.addEventListener("click", () => {
      setLoading(a, loader);
    });
  });
}
