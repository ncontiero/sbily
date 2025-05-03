import { ChevronRight, createElement } from "lucide";

export function initBreadcrumb(): void {
  const breadcrumbElements = document.querySelectorAll<HTMLElement>(
    "[data-jswc-breadcrumb]",
  );

  if (breadcrumbElements.length === 0) return;
  breadcrumbElements.forEach((breadcrumbElement) => {
    const urls = breadcrumbElement.dataset.jswcUrls?.split(",") || [];
    const labels = breadcrumbElement.dataset.jswcLabels?.split(",") || [];

    if (urls.length !== labels.length) {
      console.error("URLs and labels must have the same length");
      return;
    }

    const currentPath = window.location.pathname;
    const currentPathIndex = urls.indexOf(currentPath);

    if (currentPathIndex + 1 < urls.length) {
      urls.splice(currentPathIndex + 1);
      labels.splice(currentPathIndex + 1);
    }

    const breadcrumbList = document.createElement("ol");
    breadcrumbList.classList.add("breadcrumb");
    breadcrumbList.setAttribute("aria-label", "breadcrumb");

    breadcrumbElement.append(breadcrumbList);

    urls.forEach((url, index) => {
      const breadcrumbItem = document.createElement("li");
      breadcrumbItem.classList.add("breadcrumb-item");

      if (index !== currentPathIndex) {
        const link = document.createElement("a");
        link.href = url;
        link.textContent = labels[index];

        breadcrumbItem.append(link);
        breadcrumbList.append(breadcrumbItem);
      } else {
        const span = document.createElement("span");
        span.textContent = labels[index];
        span.role = "link";
        span.ariaCurrent = "page";
        span.ariaDisabled = "true";
        breadcrumbItem.append(span);
        breadcrumbList.append(breadcrumbItem);
      }

      if (index < urls.length - 1) {
        const breadcrumbPresentation = document.createElement("li");
        breadcrumbPresentation.role = "presentation";
        breadcrumbPresentation.classList.add("breadcrumb-item");
        breadcrumbPresentation.append(createElement(ChevronRight));
        breadcrumbList.append(breadcrumbPresentation);
      }
    });
  });
}
