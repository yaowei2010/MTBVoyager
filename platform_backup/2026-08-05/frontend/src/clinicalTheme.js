import { createTheme } from '@mui/material/styles';

const clinicalTheme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#0b67b2', dark: '#12456f', light: '#e7f4ff', contrastText: '#fff' },
    secondary: { main: '#0d8f80', dark: '#07685e', light: '#e8f7f2' },
    success: { main: '#16856b' }, warning: { main: '#c77b16' }, error: { main: '#c73e4d' },
    background: { default: '#f5f8fb', paper: '#fff' },
    text: { primary: '#102a43', secondary: '#5d7184' }, divider: '#dce7f0',
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: 'Inter, Roboto, "Noto Sans TC", Arial, sans-serif',
    h1: { fontWeight: 800, letterSpacing: '-0.04em' }, h2: { fontWeight: 800, letterSpacing: '-0.035em' },
    h3: { fontWeight: 780, letterSpacing: '-0.03em' }, h4: { fontWeight: 750, letterSpacing: '-0.02em' },
    h5: { fontWeight: 730 }, h6: { fontWeight: 700 }, button: { fontWeight: 700, textTransform: 'none' },
  },
  components: {
    MuiCssBaseline: { styleOverrides: { body: { backgroundColor: '#f5f8fb', color: '#102a43' }, '::selection': { backgroundColor: '#b9def8' } } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: 'none' }, elevation1: { boxShadow: '0 8px 28px rgba(27,72,111,.07)' }, elevation3: { boxShadow: '0 12px 34px rgba(27,72,111,.10)' } } },
    MuiCard: { styleOverrides: { root: { border: '1px solid #dce7f0', boxShadow: '0 10px 30px rgba(27,72,111,.08)' } } },
    MuiButton: { defaultProps: { disableElevation: true }, styleOverrides: { root: { borderRadius: 10, minHeight: 42, paddingLeft: 20, paddingRight: 20 }, contained: { boxShadow: '0 7px 18px rgba(11,103,178,.18)' } } },
    MuiTextField: { defaultProps: { size: 'small' } },
    MuiOutlinedInput: { styleOverrides: { root: { backgroundColor: '#fff', '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#79aeda' }, '&.Mui-focused': { boxShadow: '0 0 0 3px rgba(11,103,178,.10)' } } } },
    MuiFilledInput: { styleOverrides: { root: { borderRadius: '10px 10px 4px 4px', backgroundColor: '#f0f5f9', '&:hover': { backgroundColor: '#eaf2f8' } } } },
    MuiTabs: { styleOverrides: { indicator: { height: 3, borderRadius: '3px 3px 0 0' } } },
    MuiTab: { styleOverrides: { root: { textTransform: 'none', fontWeight: 700 } } },
    MuiChip: { styleOverrides: { root: { fontWeight: 650 } } }, MuiAlert: { styleOverrides: { root: { borderRadius: 10 } } },
    MuiDialogTitle: { styleOverrides: { root: { color: '#102a43', fontWeight: 750 } } },
    MuiTableCell: { styleOverrides: { head: { backgroundColor: '#edf5fb', color: '#16324f', fontWeight: 800 }, root: { borderColor: '#e4edf4' } } },
    MuiDataGrid: { styleOverrides: { root: { borderColor: '#dce7f0', backgroundColor: '#fff' }, columnHeaders: { backgroundColor: '#edf5fb', color: '#16324f' }, columnHeaderTitle: { fontWeight: 800 }, row: { '&:nth-of-type(even)': { backgroundColor: '#fbfdff' }, '&:hover': { backgroundColor: '#eef7ff' } }, toolbarContainer: { padding: '10px 14px', borderBottom: '1px solid #e4edf4', backgroundColor: '#fbfdff' }, footerContainer: { backgroundColor: '#fbfdff' } } },
  },
});

export default clinicalTheme;
