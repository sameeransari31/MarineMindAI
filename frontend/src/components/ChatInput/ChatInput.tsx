import { type FC, type FormEvent, useState, useRef, useEffect } from 'react';
import { HiOutlinePaperAirplane } from 'react-icons/hi2';
import styles from './ChatInput.module.css';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const ChatInput: FC<ChatInputProps> = ({ onSend, disabled }) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled) textareaRef.current?.focus();
  }, [disabled]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const msg = value.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 140) + 'px';
    }
  };

  return (
    <form className={styles.inputArea} onSubmit={handleSubmit}>
      <div className={styles.wrapper}>
        <div className={styles.inputContainer}>
          <textarea
            ref={textareaRef}
            className={styles.textarea}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder="Ask about ship systems, manuals, regulations..."
            rows={1}
            disabled={disabled}
          />
          <button
            className={styles.sendBtn}
            type="submit"
            disabled={disabled || !value.trim()}
            aria-label="Send message"
          >
            {disabled ? (
              <div className={styles.spinner} />
            ) : (
              <HiOutlinePaperAirplane size={18} />
            )}
          </button>
        </div>
        <div className={styles.hint}>
          <span>Press <kbd>Enter</kbd> to send, <kbd>Shift+Enter</kbd> for new line</span>
        </div>
      </div>
    </form>
  );
};

export default ChatInput;
