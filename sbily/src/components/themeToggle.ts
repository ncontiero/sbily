/* eslint-disable node/no-unsupported-features/node-builtins */

import { createElement, Moon, Sun } from "lucide";

export function getTheme() {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const storedTheme = localStorage.getItem("theme");
  return storedTheme ?? (prefersDark ? "dark" : "light");
}

export function initThemeToggle() {
  const themeToggle = document.querySelector<HTMLButtonElement>(
    "[data-jswc-theme-toggle]",
  );
  if (!themeToggle) return;
  const iconContainer = themeToggle.querySelector("div");

  const theme = getTheme();
  const moonIcon = createElement(Moon);
  const sunIcon = createElement(Sun);
  const iconsClass = [
    "size-5",
    "animate-in",
    "spin-in",
    "transition-transform",
    "duration-500",
  ];

  const enableDark = () => {
    document.documentElement.classList.add("dark");
    document.documentElement.style.colorScheme = "dark";
    localStorage.setItem("theme", "dark");
    themeToggle.getElementsByTagName("svg")[0]?.remove();
    if (iconContainer) {
      iconContainer.prepend(moonIcon);
    } else {
      themeToggle.prepend(moonIcon);
    }
    moonIcon.classList.add(...iconsClass);
  };
  const enableLight = () => {
    document.documentElement.classList.remove("dark");
    document.documentElement.style.colorScheme = "light";
    localStorage.setItem("theme", "light");
    themeToggle.getElementsByTagName("svg")[0]?.remove();
    if (iconContainer) {
      iconContainer.prepend(sunIcon);
    } else {
      themeToggle.prepend(sunIcon);
    }
    sunIcon.classList.add(...iconsClass);
  };

  if (theme === "dark") enableDark();
  else enableLight();

  themeToggle.addEventListener("click", () => {
    if (document.documentElement.classList.contains("dark")) enableLight();
    else enableDark();
  });
}
