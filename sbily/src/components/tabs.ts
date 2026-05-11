export function initTabs() {
  const tabLists = document.querySelectorAll<HTMLDivElement>(
    "[data-jwsc-tab-list]",
  );

  tabLists.forEach((tabs) => {
    tabs.role = "tablist";

    const tabDefault = tabs.dataset.jwscTabDefault;
    const tabUrlQuery = tabs.dataset.jwscTabUrlQuery;
    const urlParams = new URLSearchParams(window.location.search);

    const tabButtons = tabs.querySelectorAll<HTMLButtonElement>(
      "[data-jwsc-tab-value]",
    );
    const tabPanels = document.querySelectorAll<HTMLDivElement>(
      "[data-jwsc-tab-panel]",
    );

    tabButtons.forEach((button) => {
      button.role = "tab";
      button.ariaSelected = "false";

      button.addEventListener("click", () => {
        if (button.dataset.state === "active") return;

        const target = button.dataset.jwscTabValue;
        const targetElement =
          target != null &&
          document.querySelector(`[data-jwsc-tab-panel=${target}]`);
        if (targetElement == null) return;

        if (tabUrlQuery != null && target != null) {
          urlParams.set(tabUrlQuery, target);
          const newUrl = `${window.location.pathname}?${urlParams.toString()}`;
          window.history.replaceState({}, "", newUrl);
        }

        button.dataset.state = "active";
        button.ariaSelected = "true";
        tabPanels.forEach((panel) => {
          panel.dataset.state =
            panel.dataset.jwscTabPanel === target ? "active" : "inactive";
        });
        tabButtons.forEach((otherButton) => {
          if (otherButton !== button) {
            otherButton.dataset.state = "inactive";
            otherButton.ariaSelected = "false";
          }
        });
      });
    });

    const tabParam = urlParams.get(tabUrlQuery ?? tabDefault ?? "");
    if (tabParam != null) {
      const tabButton = tabs.querySelector<HTMLButtonElement>(
        `[data-jwsc-tab-value=${tabParam}]`,
      );
      if (tabButton) tabButton.click();
    } else {
      const defaultButton = tabs.querySelector<HTMLButtonElement>(
        `[data-jwsc-tab-value=${tabDefault}]`,
      );
      if (defaultButton) defaultButton.click();
    }
  });
}
