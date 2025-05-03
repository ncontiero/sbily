import { Check, createElement, X } from "lucide";
import { toast } from "@/components/toast";

export function copy(
  value: string,
  btnId: string,
  showMessage: boolean = true,
  timeout: number = 2000,
): void {
  const button = document.getElementById(btnId);
  if (!button) return;

  const ICONS = {
    success: createElement(Check),
    error: createElement(X),
  };
  const MESSAGES = {
    success: "Copied to clipboard",
    error: "Failed to copy",
  };

  const buttonContent = button.innerHTML;
  button.setAttribute("disabled", "true");

  const copyToClipboard = async (): Promise<void> => {
    try {
      // eslint-disable-next-line node/no-unsupported-features/node-builtins
      await navigator.clipboard.writeText(value);
      button.innerHTML = `${ICONS.success.outerHTML}${showMessage ? " Copied" : ""}`;
      toast(MESSAGES.success, "toast-success");
    } catch (error) {
      toast(MESSAGES.error, "toast-error");
      button.innerHTML = `${ICONS.error.outerHTML}${showMessage ? " Error" : ""}`;
      console.error("Clipboard copy failed:", error);
    } finally {
      setTimeout(() => {
        button.innerHTML = buttonContent;
        button.removeAttribute("disabled");
      }, timeout);
    }
  };

  copyToClipboard();
}
