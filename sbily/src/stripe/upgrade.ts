import { createElement, Loader } from "lucide";
import { setLoading } from "@/components/addLoad";
import { initSetupCard, prices } from ".";

declare const clientSecret: string;
declare const redirectUrl: string;
declare const defaultPaymentMethod: string;

type Cycle = "monthly" | "yearly";

function handlePlanCycle(selectedCycle: Cycle) {
  const discountElement = document.querySelector(
    "[data-jswc-upgrade='discount']",
  );
  const billingCycleElements = document.querySelectorAll(
    "[data-jswc-upgrade='billing-cycle']",
  );
  const monthlyAmount = document.querySelector(
    "[data-jswc-upgrade='monthly-amount']",
  );
  const totalAmount = document.querySelectorAll(
    "[data-jswc-upgrade='total-amount']",
  );
  const monthsCycle = document.querySelector(
    "[data-jswc-upgrade='months-cycle']",
  );
  const nextBilling = document.querySelector(
    "[data-jswc-upgrade='next-billing']",
  );

  if (
    !discountElement ||
    !monthlyAmount ||
    !monthsCycle ||
    !nextBilling ||
    billingCycleElements.length === 0 ||
    totalAmount.length === 0
  )
    return;

  const cycles = selectedCycle === "monthly" ? 1 : 12;

  billingCycleElements.forEach((element) => {
    element.textContent = selectedCycle;
  });

  monthlyAmount.textContent = prices[selectedCycle].premium.toFixed(2);
  totalAmount.forEach((element) => {
    const amount = prices[selectedCycle].premium;
    element.textContent = (amount * cycles).toFixed(2);
  });

  if (selectedCycle === "monthly") {
    discountElement.classList.add("hidden");
  } else {
    discountElement.classList.remove("hidden");
  }

  monthsCycle.textContent = cycles === 1 ? "month" : "12 months";
  nextBilling.textContent = new Date(
    new Date().setMonth(new Date().getMonth() + cycles),
  ).toLocaleDateString("en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export async function initUpgradeCheckout() {
  if (!document.getElementById("checkout-page")) return;
  const cardSetupElement = await initSetupCard();
  if (!cardSetupElement) return;

  const { stripe, cardElement } = cardSetupElement;

  const upgradeCheckoutForm = document.getElementById("upgrade-checkout-form");
  if (!upgradeCheckoutForm) return;

  const currentCycleElement = upgradeCheckoutForm.querySelector(
    "input[name='plan_cycle']:checked",
  );
  if (!currentCycleElement) return;
  let currentCycle = currentCycleElement.id as Cycle;

  handlePlanCycle(currentCycle);

  upgradeCheckoutForm.addEventListener("change", (e) => {
    if (
      !(e.target instanceof HTMLInputElement) ||
      e.target.name !== "plan_cycle"
    )
      return;

    currentCycle = e.target.id as Cycle;
    handlePlanCycle(currentCycle);
  });

  const submitButton = upgradeCheckoutForm.querySelector<HTMLElement>(
    "button[type='submit']",
  );
  if (!submitButton) return;
  const submitButtonContent = submitButton.textContent || "";
  const loader = createElement(Loader);
  loader.classList.add("animate-spin");

  upgradeCheckoutForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    setLoading(submitButton, loader, true);

    try {
      const result = await stripe.confirmCardSetup(clientSecret, {
        payment_method: {
          card: cardElement,
        },
      });

      if (result.error && result.error.code !== "incomplete_number") {
        const errorElement = document.getElementById("card-errors");
        if (errorElement) {
          errorElement.textContent =
            result.error.message || "An error occurred.";
        }
        setLoading(submitButton, loader, false, submitButtonContent);
        return;
      }

      const paymentMethodId =
        result.setupIntent?.payment_method || defaultPaymentMethod;

      const url = new URL(redirectUrl);
      if (typeof paymentMethodId === "string") {
        url.searchParams.append("payment_method", paymentMethodId);
      }
      url.searchParams.append("plan_cycle", currentCycle);

      window.location.href = url.href;
    } catch (error) {
      console.error("Error:", error);
      const errorElement = document.getElementById("card-errors");
      if (errorElement) {
        errorElement.textContent = "An unexpected error occurred.";
      }
      setLoading(submitButton, loader, false, submitButtonContent);
    }
  });
}
