import "./index.css";

import type { WindowWithCustomProps } from "./types";
import { initializeChart } from "./chart";
import { initDashboard } from "./chart/dashboard";
import { initLinkStats } from "./chart/link-stats";
import { dialog, initDialog } from "./components/dialog";
import { initDropdownMenu } from "./components/dropdownMenu";
import { initSwitch, Switch } from "./components/switch";
import { initTabs } from "./components/tabs";
import "./components/links/select";
import { initThemeToggle } from "./components/themeToggle";
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
  initLinkStats();
};

document.addEventListener("DOMContentLoaded", initApp);
