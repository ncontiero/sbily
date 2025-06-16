import type { Cycle, Plan } from "@/stripe/prices";
import { prices } from "@/stripe";

function getElement(key: string) {
  return document.querySelector<HTMLElement>(`[data-jswc-price='${key}']`);
}
function getPlanElement(plan: Plan) {
  return getElement(plan);
}

function getAmountElements() {
  const premiumBox = getPlanElement("premium");

  const amountData = "[data-jswc-price='amount']";
  const getElements = (box: HTMLElement) =>
    box.querySelectorAll<HTMLElement>(amountData);

  const premiumAmounts = premiumBox ? getElements(premiumBox) : [];

  return { premiumAmounts };
}

function setAmount(element: HTMLElement, currentCycle: Cycle, plan: Plan) {
  const amount = element.textContent;
  if (!amount || amount === "0") return;

  const price = prices[currentCycle][plan];
  if (!price) return;
  element.textContent = price.toString();
}

function selectCyclePlan(
  selected: HTMLElement,
  unselected: HTMLElement,
  upgradeElements: NodeListOf<HTMLElement>,
) {
  const { premiumAmounts } = getAmountElements();

  selected.dataset.active = "true";
  unselected.dataset.active = "false";

  selected.classList.add("bg-primary", "text-primary-foreground");
  unselected.classList.remove("bg-primary", "text-primary-foreground");

  const currentCycle =
    selected.dataset.jswcPrice === "monthly-button" ? "monthly" : "yearly";

  premiumAmounts.forEach((element) => {
    setAmount(element, currentCycle, "premium");
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
  const monthlyButton = getElement("monthly-button");
  const yearlyButton = getElement("yearly-button");
  const upgradeElements = document.querySelectorAll<HTMLElement>(
    "[data-jswc-price='upgrade'",
  );

  if (!monthlyButton || !yearlyButton) return;

  monthlyButton.addEventListener("click", () => {
    selectCyclePlan(monthlyButton, yearlyButton, upgradeElements);
  });
  yearlyButton.addEventListener("click", () => {
    selectCyclePlan(yearlyButton, monthlyButton, upgradeElements);
  });
}
