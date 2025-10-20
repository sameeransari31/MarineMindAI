import { createTheme } from '@mui/material/styles';
import { colord } from 'colord';

const palette = {
  primary: '#00BFFF',   // Deep Sky Blue (Neon)
  secondary: '#FF1493', // Deep Pink (Neon)
  background: '#040C18', // Very Dark Blue
  surface: '#111E36',   // Dark Navy Blue
  text: '#E0F2FF',      // Light Cyan
};

export const futuristicTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: palette.primary },
    secondary: { main: palette.secondary },
    background: {
      default: palette.background,
      paper: palette.surface,
    },
    text: {
      primary: palette.text,
      secondary: colord(palette.text).alpha(0.7).toRgbString(),
    },
  },
  typography: {
    fontFamily: '"Orbitron", "Roboto", "Helvetica", "Arial", sans-serif',
    h3: { fontWeight: 700 },
    h5: { fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      variants: [
        {
          props: { variant: 'glass' },
          style: {
            backgroundColor: colord(palette.surface).alpha(0.6).toRgbString(),
            backdropFilter: 'blur(10px)',
            border: `1px solid ${colord(palette.primary).alpha(0.2).toRgbString()}`,
            boxShadow: `0 8px 32px 0 ${colord(palette.background).alpha(0.37).toRgbString()}`,
          },
        },
      ],
    },
  },
});