import "./index.css";

import type { WindowWithCustomProps } from "./types";
import { initStatsPages } from "./chart";
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
import "./components/links/select";
import { copy } from "./utils/copy";

const windowExtensions: WindowWithCustomProps = {
  copy,
  toast,
  closeToast,
  dialog,
  Switch,
  stripe: initStripe(),
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

  initStatsPages();
};

document.addEventListener("DOMContentLoaded", initApp);
