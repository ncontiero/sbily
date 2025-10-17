import type { ChartConfiguration, ChartType } from "chart.js";
import { type IChoroplethDataPoint, topojson } from "chartjs-chart-geo";

type Config<T extends ChartType> = ChartConfiguration<T>;
type CustomConfig<T extends ChartType> = {
  labels: string[];
  data: string[];
  dataLabel: string;
  config?: ChartConfiguration<T>;
};

function removeOklch(color: string) {
  const match = color.match(/oklch\((.*)\)/);
  return match ? match[1].trim() : color;
}

export function getThemeColors() {
  const styles = getComputedStyle(document.documentElement);
  const primaryColor = styles.getPropertyValue("--color-primary").trim();
  const foregroundColor = styles.getPropertyValue("--color-foreground").trim();
  const backgroundColor = styles.getPropertyValue("--color-background").trim();

  return {
    primaryColor: removeOklch(primaryColor),
    foregroundColor: removeOklch(foregroundColor),
    backgroundColor: removeOklch(backgroundColor),
  };
}

export function getChartColors(count: number) {
  const { primaryColor } = getThemeColors();

  const colors = [];

  const primaryColorValues = primaryColor.split(" ");
  const lightness = primaryColorValues[0];
  const chroma = primaryColorValues[1];
  const baseHue = Number.parseInt(primaryColorValues[2]);
  const opacity = 0.8;

  if (count <= 1) {
    colors.push(`oklch(${primaryColor} / ${opacity})`);
    return colors;
  }

  for (let i = 0; i < count; i++) {
    const hue = (baseHue + i * 15) % 360;
    colors.push(`oklch(${lightness} ${chroma} ${hue} / ${opacity})`);
  }

  return colors;
}

export function getChartBarConfig({
  labels,
  data,
  dataLabel,
  config,
}: CustomConfig<"bar">): Config<"bar"> {
  const { primaryColor, foregroundColor } = getThemeColors();

  return {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: dataLabel,
          data: data.map((d) => Number.parseInt(d)),
          backgroundColor: `oklch(${primaryColor}/0.2)`,
          borderColor: primaryColor,
          borderWidth: 2,
          borderRadius: 5,
        },
      ],
    },
    options: {
      ...config?.options,
      responsive: true,
      maintainAspectRatio: false,
      hoverBackgroundColor: `oklch(${primaryColor}/0.5)`,
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
            color: `oklch(${foregroundColor}/0.2)`,
            tickColor: `oklch(${foregroundColor}/0.2)`,
          },
          beginAtZero: true,
          ticks: {
            precision: 0,
          },
        },
      },
    },
  };
}

export function getChartPieConfig({
  labels,
  data,
  dataLabel,
  config,
}: CustomConfig<"pie">): Config<"pie"> {
  return {
    type: "pie",
    data: {
      labels,
      datasets: [
        {
          label: dataLabel,
          data: data.map((d) => Number.parseInt(d)),
          backgroundColor: getChartColors(labels.length),
        },
      ],
    },
    options: {
      ...config?.options,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: {
            boxWidth: 15,
            font: {
              size: 14,
            },
          },
        },
      },
    },
  };
}

interface GetGeoCountries {
  countryLabels: string[];
  countryData: string[];
}

export async function getGeoCountries({
  countryData,
  countryLabels,
}: GetGeoCountries) {
  const countriesJson = await import("./countries-50m.json");

  const countries = (
    topojson.feature(
      countriesJson as any,
      countriesJson.objects.countries as any,
    ) as unknown as GeoJSON.FeatureCollection
  ).features;

  const labels = countries.map((d) => d.properties?.name);
  const data = countries.map((d) => ({
    feature: d,
    value: countryData[countryLabels.indexOf(d.properties?.name)] || 0,
  }));

  return { labels, data };
}

interface GetChartGetConfig
  extends Partial<CustomConfig<"choropleth">>,
    GetGeoCountries {}

export async function getChartGetConfig({
  countryLabels,
  countryData,
  dataLabel = "Countries",
  config,
}: GetChartGetConfig): Promise<Config<"choropleth">> {
  const { labels, data } = await getGeoCountries({
    countryLabels,
    countryData,
  });

  return {
    type: "choropleth",
    data: {
      labels,
      datasets: [
        {
          label: dataLabel,
          data: data as unknown as IChoroplethDataPoint[],
        },
      ],
    },
    options: {
      ...config?.options,
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
  };
}
