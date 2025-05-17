import { Chart } from "./chart";
import { getChartBarConfig, getChartGetConfig } from "./utils";

declare const dailyClicksData: { date: string; count: string }[];
declare const countryLabels: string[];
declare const countryData: string[];

export async function initDashboard() {
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

  new Chart(
    ctxCountries,
    await getChartGetConfig({ countryLabels, countryData }),
  );
}
