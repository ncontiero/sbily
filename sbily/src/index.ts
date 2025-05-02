import "./index.css";

import type { WindowWithCustomProps } from "./types";
import { getChartColors, initializeChart } from "./chart";
import { initDashboard } from "./chart/dashboard";
import { dialog, initDialog } from "./components/dialog";
import { initDropdownMenu } from "./components/dropdownMenu";
import { initSwitch, Switch } from "./components/switch";
import { initTabs } from "./components/tabs";
import { initThemeToggle } from "./components/themeToggle";
import "./components/links/select";
import { closeToast, toast } from "./components/toast";
import {
  initConfirmPayment,
  InitPriceCalculator,
  initSetupCardForm,
  initStripe,
} from "./stripe";
import { copy } from "./utils/copy";

const windowExtensions: WindowWithCustomProps = {
  copy,
  toast,
  closeToast,
  dialog,
  Switch,
  stripe: initStripe(),
  Chart: initializeChart(),
  getChartColors,
};

Object.assign(window, windowExtensions);

const initApp = (): void => {
  setTimeout(() => {
    document.documentElement.classList.replace("opacity-0", "opacity-100");
  }, 500);
  initConfirmPayment();
  InitPriceCalculator();
  initSetupCardForm();
  initDialog();
  initDropdownMenu();
  initSwitch();
  initThemeToggle();
  initTabs();

  initializeChart();
  initDashboard();
};

document.addEventListener("DOMContentLoaded", initApp);
