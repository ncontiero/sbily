export function applyYearlyDiscount(amount: number) {
  return amount * 0.8; // 20% discount
}

export const prices = {
  monthly: {
    premium: 10,
    business: 20,
    advanced: 40,
  },
  yearly: {
    premium: applyYearlyDiscount(10 * 12) / 12,
    business: applyYearlyDiscount(20 * 12) / 12,
    advanced: applyYearlyDiscount(40 * 12) / 12,
  },
};

export type Cycle = keyof typeof prices;
export type Plan = keyof typeof prices.monthly;
