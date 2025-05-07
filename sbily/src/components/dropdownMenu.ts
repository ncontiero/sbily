import type { EventHandler } from "@/types";

type Position = "top" | "right" | "bottom" | "left";
interface DropdownMenuOptions {
  animation?: boolean;
  closeOnEscape?: boolean;
  closeOnOverlayClick?: boolean;
  preferredPosition?: Position;
  offsetDistance?: number;
}

const DEFAULT_OPTIONS: DropdownMenuOptions = {
  animation: false,
  closeOnEscape: true,
  closeOnOverlayClick: true,
  preferredPosition: "bottom",
  offsetDistance: 5,
};

export function initDropdownMenu() {
  const dropdownButtons = document.querySelectorAll<HTMLElement>(
    "[data-jswc-dropdown]",
  );

  dropdownButtons.forEach((button) => {
    const target = button.dataset.jswcTarget;
    if (!target) return;

    const targetElement = document.getElementById(target);
    if (!targetElement) return;

    button.setAttribute("aria-expanded", "false");
    targetElement.setAttribute("aria-hidden", "true");
    targetElement.setAttribute("tabindex", "-1");
    targetElement.setAttribute("role", "menu");

    const options: DropdownMenuOptions = {
      ...DEFAULT_OPTIONS,
      animation: targetElement.dataset.jswcDropdownAnimation === "true",
      preferredPosition:
        (targetElement.dataset.jswcDropdownPosition as Position) || "bottom",
      offsetDistance: targetElement.dataset.jswcDropdownOffset
        ? Number.parseInt(targetElement.dataset.jswcDropdownOffset)
        : DEFAULT_OPTIONS.offsetDistance,
    };

    button.addEventListener("click", () =>
      dropdownMenu(targetElement, options),
    );
  });
}

function createOverlay(
  targetElement: HTMLElement,
  options: DropdownMenuOptions,
): HTMLElement {
  const overlayId = `dropdown-overlay-${targetElement.id}`;

  const existingOverlay = document.getElementById(overlayId);
  if (existingOverlay) return existingOverlay;

  const overlay = document.createElement("div");
  overlay.id = overlayId;
  overlay.classList.add("dropdown-menu-overlay");
  overlay.setAttribute("aria-hidden", "false");

  if (options.closeOnOverlayClick) {
    overlay.addEventListener("click", () =>
      dropdownMenu(targetElement, options),
    );
  }

  return overlay;
}

function positionDropdownElement(
  triggerElement: HTMLElement | null,
  targetElement: HTMLElement,
  options: DropdownMenuOptions = DEFAULT_OPTIONS,
): void {
  const { preferredPosition = "bottom", offsetDistance = 5 } = options;
  if (!triggerElement) return;

  const triggerRect = triggerElement.getBoundingClientRect();
  const targetRect = targetElement.getBoundingClientRect();
  const windowWidth = window.innerWidth;
  const windowHeight = window.innerHeight;

  targetElement.style.top = "";
  targetElement.style.right = "";
  targetElement.style.bottom = "";
  targetElement.style.left = "";

  const spaceTop = triggerRect.top;
  const spaceRight = windowWidth - triggerRect.right;
  const spaceBottom = windowHeight - triggerRect.bottom;
  const spaceLeft = triggerRect.left;

  let position = preferredPosition;
  if (position === "top" && spaceTop < targetRect.height) {
    position = "bottom";
  } else if (position === "right" && spaceRight < targetRect.width) {
    position = "left";
  } else if (position === "bottom" && spaceBottom < targetRect.height) {
    position = "top";
  } else if (position === "left" && spaceLeft < targetRect.width) {
    position = "right";
  }

  targetElement.style.position = "fixed";
  switch (position) {
    case "top":
      targetElement.style.bottom = `${windowHeight - triggerRect.top + offsetDistance}px`;
      targetElement.style.left = `${triggerRect.left + triggerRect.width / 2 - targetRect.width / 2}px`;
      break;
    case "right":
      targetElement.style.left = `${triggerRect.right + offsetDistance}px`;
      targetElement.style.top = `${triggerRect.top + triggerRect.height / 2 - targetRect.height / 2}px`;
      break;
    case "bottom":
      targetElement.style.top = `${triggerRect.bottom + offsetDistance}px`;
      targetElement.style.left = `${triggerRect.left + triggerRect.width / 2 - targetRect.width / 2}px`;
      break;
    case "left":
      targetElement.style.right = `${windowWidth - triggerRect.left + offsetDistance}px`;
      targetElement.style.top = `${triggerRect.top + triggerRect.height / 2 - targetRect.height / 2}px`;
      break;
  }

  const updatedRect = targetElement.getBoundingClientRect();

  if (updatedRect.left < 0) {
    targetElement.style.left = "10px";
    targetElement.style.right = "";
  } else if (updatedRect.right > windowWidth) {
    targetElement.style.left = `${windowWidth - targetRect.width - 10}px`;
    targetElement.style.right = "";
  }

  if (updatedRect.top < 0) {
    targetElement.style.top = "10px";
    targetElement.style.bottom = "";
  } else if (updatedRect.bottom > windowHeight) {
    targetElement.style.top = `${windowHeight - targetRect.height - 10}px`;
    targetElement.style.bottom = "";
  }
}

export function dropdownMenu(
  targetElement: HTMLElement,
  options: DropdownMenuOptions = DEFAULT_OPTIONS,
): void {
  const handleKeydown: EventHandler<KeyboardEvent> = (event) => {
    if (event.key === "Escape") {
      dropdownMenu(targetElement);
    }
  };

  const handleFocusout: EventHandler<FocusEvent> = (event) => {
    if (!targetElement.contains(event.relatedTarget as Node)) {
      dropdownMenu(targetElement);
    }
  };

  const cleanup = () => {
    document.removeEventListener("keydown", handleKeydown);
    document.removeEventListener("focus", handleFocusout, true);
  };

  let overlay = createOverlay(targetElement, options);
  const isOpen = targetElement.getAttribute("aria-hidden") !== "true";
  const triggerButton = document.querySelector<HTMLElement>(
    `[data-jswc-target="${targetElement.id}"]`,
  );

  if (triggerButton) {
    triggerButton.setAttribute("aria-expanded", (!isOpen).toString());
  }

  document.addEventListener("keydown", handleKeydown);
  targetElement.addEventListener("focusout", handleFocusout);

  if (!isOpen) {
    if (document.body.scrollHeight > window.innerHeight) {
      document.body.dataset.scrollLocked = "true";
    }
    document.body.append(overlay);

    targetElement.setAttribute("aria-hidden", "false");
    targetElement.classList.replace("hidden", "flex");

    positionDropdownElement(triggerButton, targetElement, options);

    const handleResize = () =>
      positionDropdownElement(triggerButton, targetElement, options);
    window.addEventListener("resize", handleResize);

    targetElement.dataset.resizeHandler = "true";
  } else {
    targetElement.setAttribute("aria-hidden", "true");

    overlay = createOverlay(targetElement, options);
    overlay.setAttribute("aria-hidden", "true");

    const closeDropdownMenu = () => {
      delete document.body.dataset.scrollLocked;
      overlay.remove();
      targetElement.classList.replace("flex", "hidden");

      if (targetElement.dataset.resizeHandler === "true") {
        // eslint-disable-next-line unicorn/no-invalid-remove-event-listener
        window.removeEventListener("resize", () =>
          positionDropdownElement(triggerButton, targetElement, options),
        );
        delete targetElement.dataset.resizeHandler;
      }

      cleanup();
    };

    if (options.animation) {
      setTimeout(() => requestAnimationFrame(closeDropdownMenu), 200);
    } else {
      closeDropdownMenu();
    }
  }
}
