import { prices } from "@/stripe";

function selectCyclePlan(
  selected: HTMLElement,
  unselected: HTMLElement,
  upgradeElements: NodeListOf<HTMLElement>,
  amountElements: NodeListOf<HTMLElement>,
) {
  selected.dataset.active = "true";
  unselected.dataset.active = "false";

  selected.classList.add("bg-primary", "text-primary-foreground");
  unselected.classList.remove("bg-primary", "text-primary-foreground");

  const currentCycle =
    selected.dataset.jswcPrice === "monthly-button" ? "monthly" : "yearly";

  amountElements.forEach((element) => {
    const amount = element.textContent;
    if (!amount || amount === "0") return;

    const price = prices[currentCycle].premium;
    if (!price) return;
    element.textContent = price.toString();
  });

  upgradeElements.forEach((element) => {
    const currentHref = element.getAttribute("href");
    const url = new URL(currentHref || "", origin);

    if (currentCycle === "yearly") {
      url.searchParams.append("cycle", "yearly");
    } else {
      url.searchParams.delete("cycle");
    }

    const newHref = `${url.pathname}?${url.searchParams}`;
    element.setAttribute("href", newHref);
  });
}

export function initPriceToggle() {
  const monthlyButton = document.querySelector<HTMLElement>(
    "[data-jswc-price='monthly-button'",
  );
  const yearlyButton = document.querySelector<HTMLElement>(
    "[data-jswc-price='yearly-button'",
  );
  const upgradeElements = document.querySelectorAll<HTMLElement>(
    "[data-jswc-price='upgrade'",
  );
  const amountElements = document.querySelectorAll<HTMLHtmlElement>(
    "[data-jswc-price='amount'",
  );

  if (!monthlyButton || !yearlyButton || amountElements.length === 0) return;

  monthlyButton.addEventListener("click", () => {
    selectCyclePlan(
      monthlyButton,
      yearlyButton,
      upgradeElements,
      amountElements,
    );
  });
  yearlyButton.addEventListener("click", () => {
    selectCyclePlan(
      yearlyButton,
      monthlyButton,
      upgradeElements,
      amountElements,
    );
  });
}
