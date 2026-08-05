export const pageSx = {
  minHeight: '100vh',
  px: { xs: 2, sm: 3, md: 5 },
  py: { xs: 3, md: 5 },
  pb: 12,
  background: 'linear-gradient(180deg, #f7fbff 0%, #f5f7fb 42%, #ffffff 100%)',
};

export const contentSx = { width: '100%', maxWidth: 1240, mx: 'auto' };

export const cardSx = {
  p: { xs: 2.5, md: 3.5 },
  border: '1px solid',
  borderColor: 'rgba(15, 67, 120, 0.12)',
  borderRadius: 3,
  backgroundColor: 'rgba(255,255,255,0.96)',
  boxShadow: '0 12px 36px rgba(30, 75, 120, 0.08)',
};

export const primaryButtonSx = {
  minWidth: { xs: '100%', sm: 210 },
  minHeight: 52,
  px: 4,
  borderRadius: 2,
  textTransform: 'none',
  fontSize: 17,
  fontWeight: 700,
  boxShadow: '0 8px 20px rgba(25, 118, 210, 0.22)',
};

export const secondaryButtonSx = {
  ...primaryButtonSx,
  boxShadow: 'none',
  backgroundColor: '#fff',
};

export const sectionTitleSx = { fontWeight: 750, color: '#16324f', letterSpacing: '-0.01em' };
