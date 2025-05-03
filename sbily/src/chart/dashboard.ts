import { topojson } from "chartjs-chart-geo";
import { Chart } from ".";
import countriesJson from "./countries-50m.json";
import { getChartBarConfig } from "./utils";

declare const dailyClicksData: { date: string; count: string }[];
declare const countryLabels: string[];
declare const countryData: string[];

export function initDashboard() {
  const inDashboardPage = document.getElementById("dashboard");
  if (!inDashboardPage) return;

  const ctxDaily = (
    document.getElementById("dailyClicksChart") as HTMLCanvasElement
  )?.getContext("2d");
  const ctxCountries = (
    document.getElementById("countriesChart") as HTMLCanvasElement
  )?.getContext("2d");

  if (!ctxDaily) {
    console.error("Canvas element not found");
    return;
  }

  new Chart(
    ctxDaily,
    getChartBarConfig({
      labels: dailyClicksData.map((item) => item.date),
      data: dailyClicksData.map((item) => item.count),
      dataLabel: "Clicks",
    }),
  );

  if (!ctxCountries) return;

  const countries = (
    topojson.feature(
      countriesJson as any,
      countriesJson.objects.countries as any,
    ) as unknown as GeoJSON.FeatureCollection
  ).features;

  new Chart(ctxCountries, {
    type: "choropleth",
    data: {
      labels: countries.map((d) => d.properties?.name),
      datasets: [
        {
          label: "Countries",
          data: countries.map((d) => ({
            feature: d,
            value: countryData[countryLabels.indexOf(d.properties?.name)] || 0,
          })),
        },
      ],
    },
    options: {
      showOutline: true,
      showGraticule: true,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        projection: {
          axis: "x",
          projection: "equalEarth",
        },
      },
    },
  });
}
