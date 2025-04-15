import { CircleAlert, CircleCheck, CircleX, createElement, Info } from "lucide";

function verifyToastOl() {
  let toastOl = document.getElementById("toast-ol");
  if (!toastOl) {
    toastOl = document.createElement("ol");
    toastOl.setAttribute("id", "toast-ol");
    toastOl.setAttribute("tabindex", "-1");
    toastOl.classList.add("toast-list");
    document.body.append(toastOl);
  }
  return toastOl;
}

function getToastIcon(tag: string) {
  switch (tag) {
    case "toast-success":
      return createElement(CircleCheck);
    case "toast-warning":
      return createElement(CircleAlert);
    case "toast-error":
      return createElement(CircleX);
    default:
      return createElement(Info);
  }
}

export function closeToast(id: string, time = 3000) {
  const toast = document.getElementById(id);
  if (!toast) return;

  const timeout = setTimeout(() => {
    toast.classList.replace("toast-open", "toast-close");
    setTimeout(() => toast.remove(), 600);
  }, time);

  const handleMouseEnter = () => clearTimeout(timeout);
  const handleMouseLeave = () => closeToast(id, time);

  toast.addEventListener("mouseenter", handleMouseEnter);
  toast.addEventListener("mouseleave", handleMouseLeave);

  setTimeout(() => {
    toast.removeEventListener("mouseenter", handleMouseEnter);
    toast.removeEventListener("mouseleave", handleMouseLeave);
  }, time + 600);
}

export function toast(msg: string, className: string, time = 3000, delay = 0) {
  const toastOl = verifyToastOl();
  const id = `toast-${Date.now()}`;

  if (toastOl.children.length >= 3) {
    closeToast(toastOl.children[0].id, 0);
  }
  const toastIcon = getToastIcon(className);
  toastIcon.classList.add("toast-icon");

  setTimeout(() => {
    toastOl.insertAdjacentHTML(
      "beforeend",
      `<li class="toast-open ${className}" id="${id}" role="alert" aria-live="assertive" aria-atomic="true" tabindex="0">
        <button
          type="button"
          onclick="closeToast('${id}', 0)"
          class="toast-close-btn"
          aria-label="Close toast"
          data-dismiss="toast"
        >
          <span aria-hidden="true">&times;</span>
        </button>
        <div class="flex items-center">
          <div>
            ${toastIcon.outerHTML}
          </div>
          <p
            class="toast-msg"
            role="alert"
            aria-live="assertive"
            aria-atomic="true"
          >
            ${msg}
          </p>
        </div>
      </li>`,
    );

    closeToast(id, time);
  }, delay);
}
