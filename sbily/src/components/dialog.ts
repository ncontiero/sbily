import type { EventHandler } from "@/types";

interface DialogOptions {
  animation?: boolean;
  closeOnEscape?: boolean;
  closeOnOverlayClick?: boolean;
}

const DEFAULT_OPTIONS: DialogOptions = {
  animation: false,
  closeOnEscape: true,
  closeOnOverlayClick: true,
};

export function initDialog(): void {
  const dialogButtons =
    document.querySelectorAll<HTMLElement>("[data-jswc-dialog]");

  dialogButtons.forEach((button) => {
    const target = button.dataset.jswcTarget;
    if (!target) return;

    const targetElement = document.getElementById(target);
    if (!targetElement) return;

    targetElement.setAttribute("aria-hidden", "true");
    targetElement.setAttribute("tabindex", "-1");
    targetElement.setAttribute("role", "dialog");

    const options: DialogOptions = {
      ...DEFAULT_OPTIONS,
      animation: targetElement.dataset.jswcDialogAnimation === "true",
    };

    button.addEventListener("click", () => dialog(targetElement, options));
  });
}

function createOverlay(
  targetElement: HTMLElement,
  options: DialogOptions,
): HTMLElement {
  const overlayId = `dialog-overlay-${targetElement.id}`;

  const existingOverlay = document.getElementById(overlayId);
  if (existingOverlay) return existingOverlay;

  const overlay = document.createElement("div");
  overlay.id = overlayId;
  overlay.classList.add("dialog-overlay");
  overlay.setAttribute("aria-hidden", "false");

  if (options.closeOnOverlayClick) {
    overlay.addEventListener("click", () => dialog(targetElement, options));
  }

  return overlay;
}

export function dialog(
  targetElement: HTMLElement,
  options: DialogOptions = DEFAULT_OPTIONS,
): void {
  const handleKeydown: EventHandler<KeyboardEvent> = (event) => {
    if (event.key === "Escape" && options.closeOnEscape) {
      dialog(targetElement, options);
    }
  };

  const handleFocus: EventHandler<FocusEvent> = (event) => {
    if (!targetElement.contains(event.target as Node)) {
      event.stopPropagation();
      targetElement.focus();
    }
  };

  const cleanup = () => {
    document.removeEventListener("keydown", handleKeydown);
    document.removeEventListener("focus", handleFocus, true);
  };

  let overlay = createOverlay(targetElement, options);
  const isOpen = targetElement.getAttribute("aria-hidden") !== "true";
  const closeButtons = targetElement.querySelectorAll(
    "[data-jswc-dialog-close]",
  );

  closeButtons.forEach((button) => {
    button.addEventListener("click", () => dialog(targetElement, options));
  });

  document.addEventListener("keydown", handleKeydown);
  document.addEventListener("focus", handleFocus, true);

  if (!isOpen) {
    if (document.body.scrollHeight > window.innerHeight) {
      document.body.dataset.scrollLocked = "true";
    }
    document.body.append(overlay);

    targetElement.setAttribute("aria-hidden", "false");
    targetElement.setAttribute("aria-modal", "true");
    targetElement.classList.replace("hidden", "block");
  } else {
    targetElement.setAttribute("aria-hidden", "true");
    targetElement.removeAttribute("aria-modal");

    overlay = createOverlay(targetElement, options);
    overlay.setAttribute("aria-hidden", "true");

    const closeDialog = () => {
      delete document.body.dataset.scrollLocked;
      overlay.remove();
      targetElement.classList.replace("block", "hidden");
      cleanup();
    };

    if (options.animation) {
      setTimeout(requestAnimationFrame, 200, closeDialog);
    } else {
      closeDialog();
    }
  }
}
