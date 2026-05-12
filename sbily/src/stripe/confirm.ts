import { initStripe } from "./stripe";

declare const clientSecret: string;
declare const redirectUrl: string;

export async function initConfirmPayment() {
  const stripe = await initStripe();

  const confirmButton = document.getElementById("confirm-button") as
    | HTMLButtonElement
    | undefined;
  const spinner = document.getElementById("spinner") as HTMLDivElement;
  const buttonText = document.getElementById("button-text") as HTMLSpanElement;
  const messageContainer = document.getElementById(
    "payment-message",
  ) as HTMLDivElement;
  const messageText = document.getElementById(
    "message-text",
  ) as HTMLSpanElement;

  if (!confirmButton) return;

  function showMessage(message: string): void {
    messageText.textContent = message;
    messageContainer.classList.remove("hidden");
  }
  function setLoading(isLoading: boolean): void {
    if (confirmButton) {
      confirmButton.disabled = isLoading;
    }

    if (isLoading) {
      // Disable the button and show spinner
      spinner.classList.remove("hidden");
      buttonText.classList.add("hidden");
      return;
    }

    // Enable the button and hide spinner
    spinner.classList.add("hidden");
    buttonText.classList.remove("hidden");
  }

  const handleConfirm = async () => {
    setLoading(true);

    const url = new URL(redirectUrl);

    try {
      // Check whether this is a payment intent or setup intent
      if (clientSecret.startsWith("pi_")) {
        // Payment Intent
        const result = await stripe.confirmCardPayment(clientSecret);
        if (result.error) {
          showMessage(result.error.message ?? "Payment failed");
          setLoading(false);
          return;
        }

        url.searchParams.append("payment_intent", result.paymentIntent.id);

        window.location.href = url.href;
      } else if (clientSecret.startsWith("seti_")) {
        // Setup Intent
        const result = await stripe.confirmCardSetup(clientSecret);
        if (result.error) {
          showMessage(result.error.message ?? "Setup failed");
          setLoading(false);
          return;
        }

        const paymentMethodId = result.setupIntent.payment_method;
        if (typeof paymentMethodId === "string") {
          url.searchParams.append("payment_method", paymentMethodId);
        }
        url.searchParams.append("setup_intent", result.setupIntent.id);

        window.location.href = url.href;
      } else {
        showMessage("Invalid client secret format");
        setLoading(false);
      }
    } catch (error) {
      console.error("Error:", error);
      showMessage("An unexpected error occurred");
      setLoading(false);
    }
  };

  confirmButton.addEventListener("click", () => {
    handleConfirm().catch(console.error);
  });
}
