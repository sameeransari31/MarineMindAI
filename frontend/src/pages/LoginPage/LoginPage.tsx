import { type FC, type FormEvent, useState } from 'react';
import { HiOutlineEnvelope, HiOutlineLockClosed, HiOutlineEye, HiOutlineEyeSlash } from 'react-icons/hi2';
import styles from './LoginPage.module.css';

interface LoginPageProps {
  onLogin: (email: string, password: string) => Promise<boolean>;
  error: string | null;
}

const LoginPage: FC<LoginPageProps> = ({ onLogin, error }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setSubmitting(true);
    await onLogin(email.trim(), password);
    setSubmitting(false);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.leftPanel}>
        <div className={styles.brandSection}>
          <div className={styles.brandLogo}>
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-1H2v1z"/>
              <path d="M12 2L12 17"/>
              <path d="M8 6l4-4 4 4"/>
              <path d="M4 19c2-3 4-5 8-5s6 2 8 5"/>
            </svg>
          </div>
          <h1 className={styles.brandName}>MarineMind</h1>
          <p className={styles.brandTagline}>AI-Powered Maritime Intelligence</p>
        </div>

        <div className={styles.features}>
          <div className={styles.feature}>
            <div className={styles.featureDot} />
            <span>Ship manual Q&A with AI</span>
          </div>
          <div className={styles.feature}>
            <div className={styles.featureDot} />
            <span>Vessel performance analytics</span>
          </div>
          <div className={styles.feature}>
            <div className={styles.featureDot} />
            <span>Maritime regulation lookup</span>
          </div>
          <div className={styles.feature}>
            <div className={styles.featureDot} />
            <span>Document knowledge base</span>
          </div>
        </div>
      </div>

      <div className={styles.rightPanel}>
        <div className={styles.container}>
          <div className={styles.header}>
            <h2 className={styles.loginTitle}>Sign in</h2>
            <p className={styles.desc}>Enter your credentials to continue</p>
          </div>

          {error && (
            <div className={styles.error}>
              <span className={styles.errorIcon}>!</span>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.field}>
              <label htmlFor="email">Email</label>
              <div className={styles.inputWrapper}>
                <HiOutlineEnvelope size={16} className={styles.inputIcon} />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  autoFocus
                  required
                />
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="password">Password</label>
              <div className={styles.inputWrapper}>
                <HiOutlineLockClosed size={16} className={styles.inputIcon} />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  className={styles.togglePassword}
                  onClick={() => setShowPassword((p) => !p)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <HiOutlineEyeSlash size={16} /> : <HiOutlineEye size={16} />}
                </button>
              </div>
            </div>
            <button type="submit" className={styles.btn} disabled={submitting}>
              {submitting ? (
                <span className={styles.btnLoading}>
                  <span className={styles.btnSpinner} />
                  Signing in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
