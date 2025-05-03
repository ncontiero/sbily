import type { Chart } from "chart.js";
import type { dialog } from "./components/dialog";
import type { Switch } from "./components/switch";
import type { closeToast, toast } from "./components/toast";
import type { initStripe } from "./stripe";
import type { copy } from "./utils/copy";

declare global {
  interface Window extends WindowWithCustomProps {}
}

export interface WindowWithCustomProps {
  copy: typeof copy;
  toast: typeof toast;
  closeToast: typeof closeToast;
  dialog: typeof dialog;
  Switch: typeof Switch;
  stripe: ReturnType<typeof initStripe>;
  Chart: typeof Chart;
}

export type EventHandler<T> = (event: T) => void;
