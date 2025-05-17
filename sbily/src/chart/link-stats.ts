import { Chart } from "./chart";
import {
  getChartBarConfig,
  getChartGetConfig,
  getChartPieConfig,
} from "./utils";

declare const dailyClicksData: { date: string; count: string }[];
declare const hourlyClicksData: { hour: string; count: string }[];
declare const countriesAndCitiesData: {
  country: string;
  city: string;
  count: string;
}[];
declare const devicesData: { device_type: string; count: string }[];
declare const browsersData: { browser: string; count: string }[];
declare const osData: { operating_system: string; count: string }[];

export async function initLinkStats() {
  const dailyClicksCtx = (
    document.getElementById("dailyClicksChart") as HTMLCanvasElement
  )?.getContext("2d");
  if (!dailyClicksCtx) {
    console.error("Failed to get canvas contexts.");
    return;
  }

  new Chart(
    dailyClicksCtx,
    getChartBarConfig({
      labels: dailyClicksData.map((data) => data.date),
      data: dailyClicksData.map((data) => data.count),
      dataLabel: "Daily Clicks",
    }),
  );

  const hourlyClicksCtx = (
    document.getElementById("hourlyClicksChart") as HTMLCanvasElement
  )?.getContext("2d");
  if (!hourlyClicksCtx) {
    console.error("Failed to get canvas contexts.");
    return;
  }

  new Chart(
    hourlyClicksCtx,
    getChartBarConfig({
      labels: hourlyClicksData.map((data) => data.hour),
      data: hourlyClicksData.map((data) => data.count),
      dataLabel: "Clicks",
    }),
  );

  const countriesAndCitiesChartCtx = (
    document.getElementById("countriesAndCitiesChart") as HTMLCanvasElement
  )?.getContext("2d");
  if (!countriesAndCitiesChartCtx) {
    console.error("Failed to get canvas contexts.");
    return;
  }

  const countryLabels = countriesAndCitiesData.map((data) => data.country);
  const countryData = countriesAndCitiesData.map((data) => data.count);

  new Chart(
    countriesAndCitiesChartCtx,
    await getChartGetConfig({ countryLabels, countryData }),
  );

  const devicesChartCtx = (
    document.getElementById("devicesChart") as HTMLCanvasElement
  )?.getContext("2d");
  const browsersChartCtx = (
    document.getElementById("browsersChart") as HTMLCanvasElement
  )?.getContext("2d");
  const osChartCtx = (
    document.getElementById("osChart") as HTMLCanvasElement
  )?.getContext("2d");

  if (!devicesChartCtx || !browsersChartCtx || !osChartCtx) {
    console.error("Failed to get canvas contexts.");
    return;
  }

  new Chart(
    devicesChartCtx,
    getChartPieConfig({
      labels: devicesData.map((data) => data.device_type),
      data: devicesData.map((data) => data.count),
      dataLabel: "Devices",
    }),
  );
  new Chart(
    browsersChartCtx,
    getChartPieConfig({
      labels: browsersData.map((data) => data.browser),
      data: browsersData.map((data) => data.count),
      dataLabel: "Devices",
    }),
  );
  new Chart(
    osChartCtx,
    getChartPieConfig({
      labels: osData.map((data) => data.operating_system),
      data: osData.map((data) => data.count),
      dataLabel: "Devices",
    }),
  );
}
