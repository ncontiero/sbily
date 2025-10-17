import {
  ArcElement,
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Colors,
  Legend,
  LinearScale,
  PieController,
  Tooltip,
} from "chart.js";
import {
  ChoroplethController,
  ColorScale,
  GeoFeature,
  ProjectionScale,
} from "chartjs-chart-geo";
import { getThemeColors } from "./utils";

export { Chart };

export function initializeChart() {
  const { primaryColor, foregroundColor, backgroundColor } = getThemeColors();

  Chart.register(
    ChoroplethController,
    GeoFeature,
    ProjectionScale,
    ColorScale,

    Legend,
    Tooltip,
    Colors,
    CategoryScale,
    LinearScale,

    BarElement,
    BarController,

    PieController,
    ArcElement,
  );

  Chart.defaults.backgroundColor = `oklch(${backgroundColor})`;
  Chart.defaults.color = `oklch(${foregroundColor})`;
  Chart.defaults.borderColor = `oklch(${backgroundColor})`;
  Chart.overrides.pie.borderColor = `oklch(${backgroundColor})`;
  Chart.defaults.font.family = "Inter";
  Chart.overrides.pie.hoverBackgroundColor = `oklch(${primaryColor})`;

  Chart.defaults.scales.color.ticks = {
    ...Chart.defaults.scales.color.ticks,
    color: `oklch(${foregroundColor}/0.5)`,
  };
  Chart.defaults.scales.color.interpolate = (v) =>
    v < 1 ? `oklch(${foregroundColor}/0.3)` : `oklch(${primaryColor}/0.8)`;

  Chart.overrides.choropleth.hoverBackgroundColor = (ctx) => {
    const { value } = ctx.dataset.data[ctx.dataIndex];
    return value > 0
      ? `oklch(${primaryColor})`
      : `oklch(${foregroundColor}/0.5)`;
  };
  Chart.overrides.choropleth.backgroundColor = `oklch(${primaryColor})`;

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "style"
      ) {
        const { primaryColor, foregroundColor, backgroundColor } =
          getThemeColors();

        for (const chart of Object.values(Chart.instances)) {
          Chart.defaults.backgroundColor = `oklch(${backgroundColor})`;
          chart.options.color = `oklch(${foregroundColor})`;
          chart.options.borderColor = `oklch(${backgroundColor})`;
          Chart.overrides.pie.hoverBackgroundColor = `oklch(${primaryColor})`;

          Chart.overrides.choropleth.hoverBackgroundColor = (ctx) => {
            const { value } = ctx.dataset.data[ctx.dataIndex];
            return value > 0
              ? `oklch(${primaryColor})`
              : `oklch(${foregroundColor}/0.5)`;
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
