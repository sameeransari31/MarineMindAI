import { type FC } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Scatter } from 'react-chartjs-2';
import type { GraphConfig } from '@/types';
import styles from './ChartRenderer.module.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

interface ChartRendererProps {
  graph: GraphConfig;
}

const ChartRenderer: FC<ChartRendererProps> = ({ graph }) => {
  if (graph.type === 'error') {
    return (
      <div className={styles.chartWrapper}>
        <div className={styles.chartTitle}>{graph.title}</div>
        <div className={styles.noData}>{graph.message ?? 'Unable to render chart.'}</div>
      </div>
    );
  }

  const summaryData = graph.summary ?? graph.data;
  if (graph.type === 'summary' && summaryData) {
    return (
      <div className={styles.chartWrapper}>
        <div className={styles.chartTitle}>{graph.title}</div>
        <div className={styles.summaryGrid}>
          {Object.entries(summaryData).map(([key, value]) => (
            <div key={key} className={styles.summaryCard}>
              <div className={styles.summaryLabel}>{key}</div>
              <div className={styles.summaryValue}>
                {typeof value === 'number' ? value.toFixed(2) : String(value)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const tableRows =
    graph.rows ??
    (graph.anomalies
      ? graph.anomalies.map((row) => Object.values(row).map((value) => value as string | number | null))
      : undefined);
  const tableColumns =
    graph.columns ??
    (graph.anomalies && graph.anomalies.length > 0 ? Object.keys(graph.anomalies[0]) : undefined);

  if (graph.type === 'table' && tableRows) {
    if (tableRows.length === 0) {
      return (
        <div className={styles.chartWrapper}>
          <div className={styles.chartTitle}>{graph.title}</div>
          <div className={styles.noData}>No anomalies detected.</div>
        </div>
      );
    }

    return (
      <div className={styles.chartWrapper}>
        <div className={styles.chartTitle}>{graph.title}</div>
        <table className={styles.table}>
          <thead>
            <tr>
              {(tableColumns ?? []).map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, idx) => (
                  <td key={`${i}-${idx}`}>{String(cell ?? '')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (graph.type === 'chart' && graph.chart_config) {
    const { chart_config } = graph;

    const themeOptions = {
      ...chart_config.options,
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        ...(chart_config.options?.plugins as Record<string, unknown> | undefined),
        legend: {
          labels: { color: '#94b3d0', font: { size: 11 } },
        },
        title: {
          display: true,
          text: graph.title,
          color: '#e8eef4',
          font: { size: 14, weight: 'bold' as const },
        },
      },
      scales: {
        x: {
          ticks: { color: '#5cc8e0', font: { size: 10 } },
          grid: { color: '#1e3f6e33' },
          ...(chart_config.options?.scales as Record<string, unknown> | undefined)?.x as Record<string, unknown> | undefined,
        },
        y: {
          ticks: { color: '#5cc8e0', font: { size: 10 } },
          grid: { color: '#1e3f6e33' },
          ...(chart_config.options?.scales as Record<string, unknown> | undefined)?.y as Record<string, unknown> | undefined,
        },
      },
    };

    const chartData = {
      labels: chart_config.data.labels,
      datasets: chart_config.data.datasets,
    };

    return (
      <div className={styles.chartWrapper}>
        <div className={styles.chartCanvas}>
          {graph.chart_type === 'bar' ? (
            <Bar data={chartData} options={themeOptions} />
          ) : graph.chart_type === 'scatter' ? (
            <Scatter data={chartData} options={themeOptions} />
          ) : (
            <Line data={chartData} options={themeOptions} />
          )}
        </div>
      </div>
    );
  }

  return null;
};

export default ChartRenderer;
