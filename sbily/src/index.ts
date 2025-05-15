import "./index.css";

import type { WindowWithCustomProps } from "./types";
import { initializeChart } from "./chart";
import { initDashboard } from "./chart/dashboard";
import { initLinkStats } from "./chart/link-stats";
import { initAddLoad } from "./components/addLoad";
import { initBreadcrumb } from "./components/breadcrumb";
import { dialog, initDialog } from "./components/dialog";
import { initDropdownMenu } from "./components/dropdownMenu";
import { initPriceToggle } from "./components/priceToggle";
import { initSwitch, Switch } from "./components/switch";
import { initTabs } from "./components/tabs";
import { initThemeToggle } from "./components/themeToggle";
import { closeToast, toast } from "./components/toast";
import {
  initConfirmPayment,
  initSetupCardForm,
  initStripe,
  initUpgradeCheckout,
} from "./stripe";
import { copy } from "./utils/copy";
import "./components/links/select";

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
  initSetupCardForm();
  initPriceToggle();
  initUpgradeCheckout();
  initDialog();
  initDropdownMenu();
  initSwitch();
  initThemeToggle();
  initTabs();
  initBreadcrumb();
  initAddLoad();

  initializeChart();
  initDashboard();
  initLinkStats();
};

document.addEventListener("DOMContentLoaded", initApp);
