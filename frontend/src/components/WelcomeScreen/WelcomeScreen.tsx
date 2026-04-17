import { type FC } from 'react';
import {
  HiOutlineWrenchScrewdriver,
  HiOutlineGlobeAlt,
  HiOutlineCog6Tooth,
  HiOutlineBolt,
  HiOutlineBeaker,
  HiOutlineShieldCheck,
} from 'react-icons/hi2';
import styles from './WelcomeScreen.module.css';

interface WelcomeScreenProps {
  onSuggestion: (text: string) => void;
}

const suggestions = [
  { text: 'What is the fuel oil purifier procedure?', icon: HiOutlineWrenchScrewdriver },
  { text: 'Latest IMO emission regulations', icon: HiOutlineGlobeAlt },
  { text: 'Main engine maintenance schedule', icon: HiOutlineCog6Tooth },
  { text: 'Explain turbocharger surging causes', icon: HiOutlineBolt },
  { text: 'How to diagnose high exhaust temperature?', icon: HiOutlineBeaker },
  { text: 'MARPOL Annex VI compliance requirements', icon: HiOutlineShieldCheck },
];

const WelcomeScreen: FC<WelcomeScreenProps> = ({ onSuggestion }) => (
  <div className={styles.welcome}>
    <div className={styles.hero}>
      <div className={styles.iconWrapper}>
        <svg className={styles.icon} width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-1H2v1z"/>
          <path d="M12 2L12 17"/>
          <path d="M8 6l4-4 4 4"/>
          <path d="M4 19c2-3 4-5 8-5s6 2 8 5"/>
        </svg>
      </div>
      <h2 className={styles.heading}>Welcome to MarineMind</h2>
      <p className={styles.description}>
        Your AI-powered maritime intelligence assistant. Ask about ship manuals,
        vessel performance, marine regulations, and machinery diagnostics.
      </p>
    </div>

    <div className={styles.suggestionsLabel}>Try asking</div>
    <div className={styles.chips}>
      {suggestions.map(({ text, icon: Icon }) => (
        <button key={text} className={styles.chip} onClick={() => onSuggestion(text)}>
          <Icon size={16} className={styles.chipIcon} />
          <span>{text}</span>
        </button>
      ))}
    </div>
  </div>
);

export default WelcomeScreen;
