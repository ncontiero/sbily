import "./index.css";

import type { WindowWithCustomProps } from "./types";
import { dialog, initDialog } from "./components/dialog";
import { initDropdownMenu } from "./components/dropdownMenu";
import { initSwitch, Switch } from "./components/switch";
import { initTabs } from "./components/tabs";
import { initThemeToggle } from "./components/themeToggle";
import { closeToast, toast } from "./components/toast";
import {
  initConfirmPayment,
  InitPriceCalculator,
  initSetupCardForm,
  initStripe,
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
};

document.addEventListener("DOMContentLoaded", initApp);
