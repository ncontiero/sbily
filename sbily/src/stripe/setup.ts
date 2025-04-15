import { initStripe } from "./stripe";

declare const clientSecret: string;
declare const redirectUrl: string;

export async function initSetupCardForm() {
  const stripe = await initStripe();
  const elements = stripe.elements();

  const cardHTMLElement = document.getElementById("card-element");
  if (!cardHTMLElement) return;

  const cardElement = elements.create("card", {
    style: {
      base: {
        fontSize: "16px",
        color: "#aab7c4",
        fontFamily:
          'var(--font-inter), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        "::placeholder": {
          color: "#aab7c4",
        },
      },
      invalid: {
        color: "#fa755a",
        iconColor: "#fa755a",
      },
    },
  });

  cardElement.mount(cardHTMLElement);

  // Handle validation errors
  cardElement.on("change", (event) => {
    const displayError = document.getElementById("card-errors");
    if (!displayError) return;

    if (event.error) {
      displayError.textContent = event.error.message;
    } else {
      displayError.textContent = "";
    }
  });

  // Handle form submission
  const form = document.getElementById("payment-form") as HTMLFormElement;
  const submitButton = document.getElementById(
    "submit-button",
  ) as HTMLButtonElement;
  const spinner = document.getElementById("spinner") as HTMLDivElement;
  const buttonText = document.getElementById("button-text") as HTMLSpanElement;

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      // Disable the submit button to prevent repeated clicks
      setLoading(true);

      try {
        const result = await stripe.confirmCardSetup(clientSecret, {
          payment_method: {
            card: cardElement,
          },
        });

        if (result.error) {
          const errorElement = document.getElementById("card-errors");
          if (errorElement) {
            errorElement.textContent =
              result.error.message || "An error occurred.";
          }
          setLoading(false);
        } else {
          const paymentMethodId = result.setupIntent.payment_method;
          const setupIntentId = result.setupIntent.id;

          window.location.href = `${redirectUrl}?payment_method=${paymentMethodId}&setup_intent=${setupIntentId}`;
        }
      } catch (error) {
        console.error("Error:", error);
        const errorElement = document.getElementById("card-errors");
        if (errorElement) {
          errorElement.textContent = "An unexpected error occurred.";
        }
        setLoading(false);
      }
    });
  }

  function setLoading(isLoading: boolean): void {
    if (isLoading) {
      submitButton.disabled = true;
      spinner.classList.remove("hidden");
      buttonText.classList.add("hidden");
    } else {
      submitButton.disabled = false;
      spinner.classList.add("hidden");
      buttonText.classList.remove("hidden");
    }
  }
}
