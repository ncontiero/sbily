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

  Chart.defaults.color = `hsl(${foregroundColor})`;
  Chart.defaults.borderColor = `hsl(${backgroundColor})`;
  Chart.overrides.pie.borderColor = `hsl(${backgroundColor})`;
  Chart.defaults.font.family = "Inter";

  Chart.defaults.scales.color.ticks = {
    ...Chart.defaults.scales.color.ticks,
    color: `hsl(${foregroundColor}/0.5)`,
  };
  Chart.defaults.scales.color.interpolate = (v) =>
    v < 1 ? `hsl(${foregroundColor}/0.3)` : `hsl(${primaryColor}/0.8)`;

  Chart.overrides.choropleth.hoverBackgroundColor = (ctx) => {
    const { value } = ctx.dataset.data[ctx.dataIndex];
    return value > 0 ? `hsl(${primaryColor})` : `hsl(${foregroundColor}/0.5)`;
  };

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "style"
      ) {
        const { primaryColor, foregroundColor, backgroundColor } =
          getThemeColors();

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
