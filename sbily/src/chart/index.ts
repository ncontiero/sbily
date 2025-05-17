export async function initStatsPages() {
  const inDashboardPage = document.getElementById("dashboard");
  const inLinkStatsPage = document.getElementById("links-stats");

  if (!inDashboardPage && !inLinkStatsPage) return;

  const { initializeChart } = await import("./chart");
  const Chart = initializeChart();

  if (inDashboardPage) {
    const { initDashboard } = await import("./dashboard");
    await initDashboard();
  }

  if (inLinkStatsPage) {
    const { initLinkStats } = await import("./link-stats");
    await initLinkStats();
  }

  const charts = Object.values(Chart.instances);
  if (charts.length === 0) return;
  for (const chart of charts) {
    chart.update();
  }
}
