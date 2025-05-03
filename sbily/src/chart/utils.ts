import type { ChartConfiguration, ChartType } from "chart.js";

type Config<T extends ChartType> = ChartConfiguration<T>;
type CustomConfig<T extends ChartType> = {
  labels: string[];
  data: string[];
  dataLabel: string;
  config?: ChartConfiguration<T>;
};

export function getChartColors(count: number) {
  const primaryColor = getComputedStyle(document.documentElement)
    .getPropertyValue("--primary")
    .trim();

  const colors = [];
  const opacity = 0.8;

  // Primary color with varying brightness
  for (let i = 0; i < count; i++) {
    const hue = Number.parseInt(primaryColor) + ((i * 30) % 360);
    colors.push(`hsl(${hue}, 70%, 60%, ${opacity})`);
  }

  return colors;
}

export function getChartBarConfig({
  labels,
  data,
  dataLabel,
  config,
}: CustomConfig<"bar">): Config<"bar"> {
  const styles = getComputedStyle(document.documentElement);
  const primaryColor = styles.getPropertyValue("--primary").trim();
  const foregroundColor = styles.getPropertyValue("--foreground").trim();

  return {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: dataLabel,
          data: data.map((d) => Number.parseInt(d)),
          backgroundColor: `hsl(${primaryColor}/0.2)`,
          borderColor: `hsl(${primaryColor})`,
          borderWidth: 2,
          borderRadius: 5,
        },
      ],
    },
    options: {
      ...config?.options,
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
