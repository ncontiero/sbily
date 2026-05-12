import { loadStripe } from "@stripe/stripe-js";

export const initStripe = async () => {
  if (!process.env.STRIPE_PUBLIC_KEY) {
    throw new Error("Missing env variable: STRIPE_PUBLIC_KEY");
  }

  const stripe = await loadStripe(process.env.STRIPE_PUBLIC_KEY);
  if (!stripe) {
    throw new Error("Stripe failed to load");
  }

  return stripe;
};
