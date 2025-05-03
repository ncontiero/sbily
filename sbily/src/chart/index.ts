import Chart, { registerables } from "chart.js/auto";
import {
  ChoroplethController,
  ColorScale,
  GeoFeature,
  ProjectionScale,
} from "chartjs-chart-geo";

export { Chart };

export function initializeChart() {
  const styles = getComputedStyle(document.documentElement);
  const primaryColor = styles.getPropertyValue("--primary").trim();
  const foregroundColor = styles.getPropertyValue("--foreground").trim();
  const backgroundColor = styles.getPropertyValue("--background").trim();

  Chart.register(
    ChoroplethController,
    GeoFeature,
    ProjectionScale,
    ColorScale,
    ...registerables,
  );

  Chart.defaults.color = `hsl(${foregroundColor})`;
  Chart.defaults.borderColor = `hsl(${backgroundColor})`;
  Chart.defaults.font.family = "Inter";

  Chart.defaults.scales.color.ticks = {
    ...Chart.defaults.scales.color.ticks,
    color: `hsl(${foregroundColor}/0.5)`,
  };
  Chart.defaults.scales.color.interpolate = (v) =>
    v < 0.5 ? `hsl(${foregroundColor}/0.3)` : `hsl(${primaryColor}/0.8)`;

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "style"
      ) {
        const styles = getComputedStyle(document.documentElement);
        const primaryColor = styles.getPropertyValue("--primary").trim();
        const foregroundColor = styles.getPropertyValue("--foreground").trim();
        const backgroundColor = styles.getPropertyValue("--background").trim();

        for (const chart of Object.values(Chart.instances)) {
          chart.options.borderColor = `hsl(${backgroundColor})`;
          chart.options.color = `hsl(${foregroundColor})`;

          Chart.overrides.choropleth.hoverBackgroundColor = (ctx) => {
            const { value } = ctx.dataset.data[ctx.dataIndex];
            return value > 0
              ? `hsl(${primaryColor})`
              : `hsl(${foregroundColor}/0.5)`;
          };

          chart.update();
        }
      }
    });
  });
  observer.observe(document.documentElement, {
    attributes: true,
  });

  return Chart;
}
