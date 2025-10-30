import type { ChartConfiguration, ChartType } from "chart.js";
import { type IChoroplethDataPoint, topojson } from "chartjs-chart-geo";
import { modeLab, modeOklch, useMode } from "culori/fn";

type Config<T extends ChartType> = ChartConfiguration<T>;
type CustomConfig<T extends ChartType> = {
  labels: string[];
  data: string[];
  dataLabel: string;
  config?: ChartConfiguration<T>;
};

export function applyOpacity(color: string, opacity: number) {
  if (opacity < 0 || opacity > 100) {
    throw new RangeError(
      `applyOpacity: opacity must be between 0 and 100 (received ${opacity})`,
    );
  }

  return `color-mix(in oklab, ${color} ${opacity}%, transparent)`;
}

export function getThemeColors() {
  const styles = getComputedStyle(document.documentElement);
  const primaryColor = styles.getPropertyValue("--color-primary").trim();
  const foregroundColor = styles.getPropertyValue("--color-foreground").trim();
  const backgroundColor = styles.getPropertyValue("--color-background").trim();

  return {
    primaryColor,
    foregroundColor,
    backgroundColor,
  };
}

useMode(modeLab);
const toOklch = useMode(modeOklch);

export function getChartColors(count: number, opacity = 80) {
  const { primaryColor } = getThemeColors();
  const colors: string[] = [];

  if (count <= 1) {
    colors.push(applyOpacity(primaryColor, opacity));
    return colors;
  }

  const baseColor = toOklch(primaryColor);
  if (!baseColor) {
    for (let i = 0; i < count; i++) {
      const newOpacity = opacity - i * (opacity / count);
      colors.push(applyOpacity(primaryColor, Math.max(newOpacity, 0)));
    }

    return colors;
  }

  const baseHue = baseColor.h || 0;

  for (let i = 0; i < count; i++) {
    const newHue = (baseHue + i * 8) % 360;
    const newColorString = `oklch(${baseColor.l} ${baseColor.c} ${newHue})`;
    colors.push(applyOpacity(newColorString, opacity));
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
          backgroundColor: applyOpacity(primaryColor, 20),
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
      hoverBackgroundColor: applyOpacity(primaryColor, 50),
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
            color: applyOpacity(foregroundColor, 20),
            tickColor: applyOpacity(foregroundColor, 20),
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
          hoverBackgroundColor: getChartColors(labels.length, 100),
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
