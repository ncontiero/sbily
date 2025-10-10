import type { Cycle, Plan } from "./prices";
import { createElement, Loader } from "lucide";
import { setLoading } from "@/components/addLoad";
import { initSetupCard, prices } from ".";

declare const clientSecret: string;
declare const redirectUrl: string;
declare const plan: Plan;
declare const discountAmount: string;
declare const invoiceCredit: string;
declare const defaultPaymentMethod: string;

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
    !monthsCycle ||
    !monthlyAmount ||
    billingCycleElements.length === 0 ||
    totalAmount.length === 0
  )
    return;

  const cycles = selectedCycle === "monthly" ? 1 : 12;

  billingCycleElements.forEach((element) => {
    element.textContent = selectedCycle;
  });

  monthlyAmount.textContent = prices[selectedCycle][plan].toFixed(2);
  totalAmount.forEach((element) => {
    const monthlyPrice = prices[selectedCycle][plan];
    const discount =
      discountAmount !== "False" ? Number.parseFloat(discountAmount) : 0;
    const invoiceCreditAmount =
      invoiceCredit !== "0" ? Number.parseFloat(invoiceCredit) : 0;
    const total = monthlyPrice * cycles - discount - invoiceCreditAmount;

    element.textContent = total > 0 ? total.toFixed(2) : "0";
  });

  if (selectedCycle === "monthly") {
    discountElement.classList.add("hidden");
  } else {
    discountElement.classList.remove("hidden");
  }

  monthsCycle.textContent = cycles === 1 ? "month" : "12 months";
  if (nextBilling) {
    nextBilling.textContent = new Date(
      new Date().setMonth(new Date().getMonth() + cycles),
    ).toLocaleDateString("en-US", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }
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

  const fixedMonthlyAmounts = document.querySelectorAll(
    "[data-jswc-upgrade='fixed-monthly-amount']",
  );
  const fixedYearlyMonthAmount = document.querySelector(
    "[data-jswc-upgrade='fixed-yearly-month-amount']",
  );
  const fixedYearlyTotalAmount = document.querySelector(
    "[data-jswc-upgrade='fixed-yearly-total-amount']",
  );
  const fixedYearlyDiscount = document.querySelector(
    "[data-jswc-upgrade='fixed-yearly-discount']",
  );
  if (
    !fixedYearlyMonthAmount ||
    !fixedYearlyTotalAmount ||
    !fixedYearlyDiscount
  )
    return;

  const yearlyPrice = prices.yearly[plan];
  const discount = prices.monthly[plan] * 12 - yearlyPrice * 12;

  fixedYearlyMonthAmount.textContent = yearlyPrice.toFixed(2);
  fixedYearlyTotalAmount.textContent = (yearlyPrice * 12).toFixed(2);
  fixedYearlyDiscount.textContent = discount.toFixed(2);
  fixedMonthlyAmounts.forEach((element) => {
    element.textContent = prices.monthly[plan].toFixed(2);
  });

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

      if (result.error && defaultPaymentMethod === "None") {
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
      url.searchParams.append("plan", plan);
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
