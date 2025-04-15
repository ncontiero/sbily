// Price configuration
interface PriceConfig {
  permanent: {
    [key: string]: {
      unitPrice: number;
      discount?: number;
    };
  };
  temporary: {
    [key: string]: {
      unitPrice: number;
      discount?: number;
    };
  };
}

const priceConfig: PriceConfig = {
  permanent: {
    "5": { unitPrice: 1 },
    "10": { unitPrice: 1 },
    "25": { unitPrice: 1 },
    "50": { unitPrice: 1 },
    "100": { unitPrice: 1, discount: 0.1 }, // 10% discount
  },
  temporary: {
    "5": { unitPrice: 2 },
    "10": { unitPrice: 2 },
    "25": { unitPrice: 2 },
    "50": { unitPrice: 2, discount: 0.1 }, // 10% discount
    "100": { unitPrice: 2, discount: 0.1 }, // 10% discount
  },
};

export function InitPriceCalculator() {
  // Initialize price calculators for permanent links
  const quantitySelect = document.getElementById(
    "quantity",
  ) as HTMLSelectElement;
  if (quantitySelect) {
    quantitySelect.addEventListener("change", () => {
      updatePriceCalculation("permanent", quantitySelect.value);
    });

    // Initial calculation
    updatePriceCalculation("permanent", quantitySelect.value);
  }

  // Initialize price calculators for temporary links
  const tempQuantitySelect = document.getElementById(
    "temp_quantity",
  ) as HTMLSelectElement;
  if (tempQuantitySelect) {
    tempQuantitySelect.addEventListener("change", () => {
      updatePriceCalculation("temporary", tempQuantitySelect.value);
    });

    // Initial calculation
    updatePriceCalculation("temporary", tempQuantitySelect.value);
  }

  function updatePriceCalculation(
    linkType: "permanent" | "temporary",
    quantity: string,
  ): void {
    const containerId =
      linkType === "permanent" ? "price-calculation" : "temp-price-calculation";
    const container = document.getElementById(containerId);
    if (!container) return;

    const quantityNum = Number.parseInt(quantity);
    const config = priceConfig[linkType][quantity];

    if (!config) return;

    const subtotal = quantityNum * config.unitPrice;
    let discount = 0;

    if (config.discount) {
      discount = subtotal * config.discount;
    }

    const total = subtotal - discount;

    // Create HTML content
    let html = `
      <div class="flex justify-between">
        <span>${quantity} ${linkType} links</span>
        <span>$${subtotal.toFixed(2)}</span>
      </div>
    `;

    if (discount > 0) {
      html += `
        <div class="flex justify-between text-primary">
          <span>Discount</span>
          <span>-$${discount.toFixed(2)}</span>
        </div>
      `;
    }

    html += `
      <div class="separator my-2"></div>
      <div class="flex justify-between font-bold">
        <span>Total</span>
        <span>$${total.toFixed(2)}</span>
      </div>
    `;

    container.innerHTML = html;
  }
}
