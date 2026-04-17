import { type FC } from 'react';
import type { DiagnosisMetadata } from '@/types';
import {
  HiOutlineExclamationTriangle,
  HiOutlineWrench,
  HiOutlineChartBar,
  HiOutlineCog6Tooth,
  HiOutlineArrowTrendingUp,
  HiOutlineArrowTrendingDown,
} from 'react-icons/hi2';
import styles from './DiagnosisCard.module.css';

interface DiagnosisCardProps {
  diagnosis: DiagnosisMetadata;
}

const SEVERITY_CONFIG: Record<string, { label: string; className: string }> = {
  low: { label: 'Low', className: 'severityLow' },
  medium: { label: 'Medium', className: 'severityMedium' },
  high: { label: 'High', className: 'severityHigh' },
  critical: { label: 'Critical', className: 'severityCritical' },
};

const CATEGORY_LABELS: Record<string, string> = {
  engine: 'Main Engine',
  fuel_system: 'Fuel System',
  cooling_system: 'Cooling System',
  propulsion: 'Propulsion',
  electrical: 'Electrical',
  auxiliary: 'Auxiliary Systems',
  hull_performance: 'Hull Performance',
  navigation: 'Navigation',
  weather_related: 'Weather Related',
  lubrication: 'Lubrication',
  exhaust: 'Exhaust System',
  turbocharger: 'Turbocharger',
  other: 'General',
};

const DiagnosisCard: FC<DiagnosisCardProps> = ({ diagnosis }) => {
  const severity = SEVERITY_CONFIG[diagnosis.severity] ?? SEVERITY_CONFIG.medium;
  const category = CATEGORY_LABELS[diagnosis.category] ?? diagnosis.category;

  return (
    <div className={styles.card}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <HiOutlineWrench size={16} />
          <span className={styles.headerTitle}>Diagnosis Summary</span>
        </div>
        <div className={styles.headerRight}>
          <span className={`${styles.severityBadge} ${styles[severity.className]}`}>
            <HiOutlineExclamationTriangle size={12} />
            {severity.label} Severity
          </span>
          <span className={styles.categoryBadge}>
            <HiOutlineCog6Tooth size={12} />
            {category}
          </span>
        </div>
      </div>

      {/* Symptoms */}
      {diagnosis.symptoms.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Identified Symptoms</div>
          <div className={styles.tagList}>
            {diagnosis.symptoms.map((s, i) => (
              <span key={i} className={styles.symptomTag}>{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* Affected Components */}
      {diagnosis.affected_components.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Affected Components</div>
          <div className={styles.tagList}>
            {diagnosis.affected_components.map((c, i) => (
              <span key={i} className={styles.componentTag}>{c}</span>
            ))}
          </div>
        </div>
      )}

      {/* Trends */}
      {diagnosis.trends.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>
            <HiOutlineChartBar size={14} />
            Performance Trends
          </div>
          <div className={styles.trendList}>
            {diagnosis.trends.map((trend, i) => (
              <div key={i} className={styles.trendItem}>
                <span className={styles.trendIcon}>
                  {trend.direction === 'increased' ? (
                    <HiOutlineArrowTrendingUp size={14} className={styles.trendUp} />
                  ) : (
                    <HiOutlineArrowTrendingDown size={14} className={styles.trendDown} />
                  )}
                </span>
                <span className={styles.trendMetric}>{trend.metric}</span>
                <span className={`${styles.trendChange} ${trend.direction === 'increased' ? styles.trendUp : styles.trendDown}`}>
                  {trend.direction === 'increased' ? '+' : '-'}{trend.change_percent}%
                </span>
                <span className={styles.trendDetail}>
                  {trend.recent_avg} (was {trend.baseline_avg})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Anomalies */}
      {diagnosis.anomalies.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>
            <HiOutlineExclamationTriangle size={14} />
            Detected Anomalies
          </div>
          <div className={styles.anomalyList}>
            {diagnosis.anomalies.slice(0, 5).map((a, i) => (
              <div key={i} className={styles.anomalyItem}>
                <span className={styles.anomalyDate}>{a.date}</span>
                <span className={styles.anomalyLabel}>{a.label}</span>
                <span className={styles.anomalyValue}>
                  {a.value} <span className={styles.anomalyRange}>
                    (expected: {a.expected_range[0]} – {a.expected_range[1]})
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Sources Indicator */}
      <div className={styles.footer}>
        <span className={`${styles.sourceIndicator} ${diagnosis.data_available ? styles.sourceActive : ''}`}>
          <HiOutlineChartBar size={11} />
          {diagnosis.data_available ? 'Data Analysis' : 'No Data'}
        </span>
        <span className={`${styles.sourceIndicator} ${diagnosis.knowledge_available ? styles.sourceActive : ''}`}>
          <HiOutlineWrench size={11} />
          {diagnosis.knowledge_available ? 'Manual Knowledge' : 'No Manuals'}
        </span>
        {diagnosis.vessel_name && (
          <span className={styles.vesselName}>
            Vessel: {diagnosis.vessel_name}
          </span>
        )}
      </div>
    </div>
  );
};

export default DiagnosisCard;
