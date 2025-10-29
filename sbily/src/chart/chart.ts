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
import { applyOpacity, getThemeColors } from "./utils";

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

  Chart.defaults.backgroundColor = backgroundColor;
  Chart.defaults.color = foregroundColor;
  Chart.defaults.borderColor = backgroundColor;
  Chart.overrides.pie.borderColor = backgroundColor;
  Chart.defaults.font.family = "Inter";
  Chart.overrides.pie.hoverBackgroundColor = primaryColor;

  Chart.defaults.scales.color.ticks = {
    ...Chart.defaults.scales.color.ticks,
    color: applyOpacity(foregroundColor, 50),
  };
  Chart.defaults.scales.color.interpolate = (v) =>
    v < 1 ? applyOpacity(foregroundColor, 30) : applyOpacity(primaryColor, 80);

  Chart.overrides.choropleth.hoverBackgroundColor = (ctx) => {
    const { value } = ctx.dataset.data[ctx.dataIndex];
    return value > 0 ? primaryColor : applyOpacity(foregroundColor, 50);
  };
  Chart.overrides.choropleth.backgroundColor = primaryColor;

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "style"
      ) {
        const { primaryColor, foregroundColor, backgroundColor } =
          getThemeColors();

        for (const chart of Object.values(Chart.instances)) {
          Chart.defaults.backgroundColor = backgroundColor;
          chart.options.color = foregroundColor;
          chart.options.borderColor = backgroundColor;
          Chart.overrides.pie.hoverBackgroundColor = primaryColor;

          Chart.overrides.choropleth.hoverBackgroundColor = (ctx) => {
            const { value } = ctx.dataset.data[ctx.dataIndex];
            return value > 0 ? primaryColor : applyOpacity(foregroundColor, 50);
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
