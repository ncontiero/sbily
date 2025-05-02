import { topojson } from "chartjs-chart-geo";
import { Chart } from ".";
import countriesJson from "./countries-50m.json";

declare const dailyClicksData: { date: string; count: string }[];
declare const countryLabels: string[];
declare const countryData: string[];

export function initDashboard() {
  const inDashboardPage = document.getElementById("dashboard");
  if (!inDashboardPage) return;

  const styles = getComputedStyle(document.documentElement);
  const primaryColor = styles.getPropertyValue("--primary").trim();
  const foregroundColor = styles.getPropertyValue("--foreground").trim();

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

  new Chart(ctxDaily, {
    type: "bar",
    data: {
      labels: dailyClicksData.map((item) => item.date),
      datasets: [
        {
          label: "Clicks",
          data: dailyClicksData.map((item) => item.count),
          backgroundColor: `hsl(${primaryColor}/0.2)`,
          borderColor: `hsl(${primaryColor})`,
          borderWidth: 2,
          borderRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      hoverBackgroundColor: `hsl(${primaryColor}/0.5)`,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          grid: {
            display: false,
          },
        },
        y: {
          grid: {
            color: `hsl(${foregroundColor}/0.2)`,
            tickColor: `hsl(${foregroundColor}/0.2)`,
          },
          beginAtZero: true,
          ticks: {
            precision: 0,
          },
        },
      },
    },
  });

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
