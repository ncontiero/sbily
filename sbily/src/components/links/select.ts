import { dialog } from "../dialog";
import { toast } from "../toast";

const tbody = document.getElementById("tbody") as HTMLTableElement | null;
const checkAllLinksCheckbox = document.getElementById(
  "check-all-links",
) as HTMLInputElement | null;

const linkActionGo = document.getElementById("link-action-go");
linkActionGo?.addEventListener("click", (e: Event) => {
  const target = e.target as HTMLElement | undefined;
  if (!target || !tbody) return;

  const action = (document.getElementById("action") as HTMLSelectElement)
    ?.value;
  if (!action || action === "------------") {
    toast("No action selected!", "toast-warning");
    return;
  }

  const checkedLinks =
    tbody.querySelectorAll<HTMLInputElement>("input:checked");
  if (checkedLinks.length === 0) {
    toast("No links selected!", "toast-warning");
    return;
  }

  const actionType = action.split("_")[0];
  const actionText = document.getElementById("action-text");
  const actionTextF = document.getElementById("action-text-f");

  if (actionText) actionText.textContent = actionType;
  if (actionTextF) actionTextF.textContent = `${actionType}d`;

  const linksSelectedUl = document.getElementById("links-selected-ul");
  if (linksSelectedUl) {
    linksSelectedUl.innerHTML = "";
    checkedLinks.forEach((checkbox) => {
      const li = document.createElement("li");
      const content = document.createElement("span");
      content.textContent = checkbox.dataset.link ?? "";
      content.classList.add("text-primary");
      li.innerHTML = `Link: ${content.outerHTML}`;
      linksSelectedUl.append(li);
    });
  }

  const dialogTarget = target.dataset.jswcTarget;
  if (!dialogTarget) return;
  const targetElement = document.getElementById(dialogTarget);
  if (targetElement) dialog(targetElement, { animation: true });
});

function updateActionCounter(): void {
  const actionCounter = document.getElementById("action-counter");
  if (!actionCounter) return;

  const actionCount = tbody?.querySelectorAll("input:checked");
  actionCounter.textContent = actionCount?.length.toString() ?? "0";
}

function checkLink(checkbox: HTMLInputElement): void {
  if (!checkbox.checked && checkAllLinksCheckbox) {
    checkAllLinksCheckbox.checked = false;
  }

  const link = checkbox.closest("tr");
  if (link) {
    link.classList.toggle("selected");
    link.classList.toggle("hover:bg-muted/50");
  }
  updateActionCounter();
}

function checkAllLinks(): void {
  if (!tbody || !checkAllLinksCheckbox) return;

  const isChecked = checkAllLinksCheckbox.checked;
  tbody.querySelectorAll("tr").forEach((link) => {
    link.querySelectorAll("input").forEach((checkbox) => {
      if (isChecked) {
        link.classList.add("selected");
        link.classList.remove("hover:bg-muted/50");
      } else {
        link.classList.remove("selected");
        link.classList.add("hover:bg-muted/50");
      }
      checkbox.checked = isChecked;
    });
  });

  updateActionCounter();
}

checkAllLinksCheckbox?.addEventListener("change", checkAllLinks);
document.addEventListener("DOMContentLoaded", () => {
  const linksCheckbox =
    document.querySelectorAll<HTMLInputElement>("input[data-link]");
  linksCheckbox.forEach((checkbox) => {
    checkbox.addEventListener("change", (e) => {
      const target = e.target as HTMLInputElement;
      checkLink(target);
    });
  });
});
