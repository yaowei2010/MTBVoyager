import * as React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { config } from '../../constant';
import Bottom_infor from './Bottom_info.js';

import { styled, useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import MuiDrawer from '@mui/material/Drawer';
import MuiAppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import List from '@mui/material/List';
import CssBaseline from '@mui/material/CssBaseline';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import InboxIcon from '@mui/icons-material/MoveToInbox';
import Button from '@mui/material/Button';


import HomeIcon from '@mui/icons-material/Home';
import InfoIcon from '@mui/icons-material/Info';
import SettingsIcon from '@mui/icons-material/Settings';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import CalendarViewMonthIcon from '@mui/icons-material/CalendarViewMonth';
import MonitorIcon from '@mui/icons-material/Monitor';
import BlockIcon from '@mui/icons-material/Block';
import { AuthContext } from '../Auth/AuthContext';
import { useNavigate } from 'react-router-dom';

const drawerWidth = 240;

const openedMixin = (theme) => ({
  width: drawerWidth,
  transition: theme.transitions.create('width', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.enteringScreen,
  }),
  overflowX: 'hidden',
  background: 'linear-gradient(180deg, #0e2e4d 0%, #123d61 62%, #0b5960 100%)',
  color: '#fff',
  borderRight: 0,
});

const closedMixin = (theme) => ({
  transition: theme.transitions.create('width', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  overflowX: 'hidden',
  width: '80px', // 收起狀態的固定寬度
  background: 'linear-gradient(180deg, #0e2e4d 0%, #123d61 62%, #0b5960 100%)',
  color: '#fff',
  borderRight: 0,
  // width: `calc(${theme.spacing(7)} + 1px)`,
  // [theme.breakpoints.up('sm')]: {
  //   width: `calc(${theme.spacing(10)} + 1px)`,
  // },
});

const DrawerHeader = styled('div')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  padding: theme.spacing(0, 1),
  // necessary for content to be below app bar
  ...theme.mixins.toolbar,
}));

const AppBar = styled(MuiAppBar, {
  shouldForwardProp: (prop) => prop !== 'open',
})(({ theme, open }) => ({
  zIndex: theme.zIndex.drawer + 1,
  transition: theme.transitions.create(['width', 'margin'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  background: 'linear-gradient(90deg, #0e2e4d 0%, #124f70 100%)',
  boxShadow: '0 4px 22px rgba(7,35,59,.18)',
  ...(open && {
    marginLeft: drawerWidth,
    width: `calc(100% - ${drawerWidth}px)`,
    transition: theme.transitions.create(['width', 'margin'], {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.enteringScreen,
    }),
  }),
}));



const Drawer = styled(MuiDrawer, { shouldForwardProp: (prop) => prop !== 'open' })(
  ({ theme, open }) => ({
    width: drawerWidth,
    flexShrink: 0,
    whiteSpace: 'nowrap',
    boxSizing: 'border-box',
    ...(open && {
      ...openedMixin(theme),
      '& .MuiDrawer-paper': openedMixin(theme),
    }),
    ...(!open && {
      ...closedMixin(theme),
      '& .MuiDrawer-paper': closedMixin(theme),
    }),
  }),
);




function Left_navigation() {
  const theme = useTheme();
  const [open, setOpen] = React.useState(false);
  const location = useLocation();

  const handleDrawerOpen = () => {
    setOpen(true);
  };

  const handleDrawerClose = () => {
    setOpen(false);
  };

  const { logout } = React.useContext(AuthContext);
  const navigate = useNavigate();

  return (
    <Box sx={{ display: 'flex' }}>
      <Bottom_infor />
      <Box sx={{ flexGrow: 1 }}>
        <CssBaseline />
        <AppBar position="fixed" open={open}>
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              onClick={handleDrawerOpen}
              edge="start"
              sx={{
                marginRight: 5,
                ...(open && { display: 'none' }),
              }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 800, letterSpacing: '.04em' }}>
              NCKU Genomics
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              <Button
                color="inherit"
                onClick={() => {
                  logout();         // 清除 token
                  navigate(config.rootPathPrefix + '/login'); // 回到登入頁
                }}
                style={{
                  fontSize: '1rem',
                  backgroundColor: 'rgba(255,255,255,.12)',
                  color: '#fff',
                  border: '1px solid rgba(255,255,255,.35)',
                }}
              >
                Sign out
              </Button>
            </Box>
          </Toolbar>
        </AppBar>
        <Drawer variant="permanent" open={open}>
          <DrawerHeader>
            <IconButton onClick={handleDrawerClose}>
              {theme.direction === 'rtl' ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            </IconButton>
          </DrawerHeader>
          <Divider />
          <List>
            {[
              { text: 'Home', link:  config.rootPathPrefix + "/home" , icon: <HomeIcon /> },
              { text: 'Job Result', link: config.rootPathPrefix + "/Job_results" , icon: <CalendarViewMonthIcon />},
              { text: 'Analyses', link: config.rootPathPrefix + "/Analysis/Protocol" , icon: <AnalyticsIcon />},
              { text: 'VUS monitor', link: config.rootPathPrefix + "/VUS" , icon: <MonitorIcon />},
              { text: 'Blacklist', link: config.rootPathPrefix + "/Blacklist" , icon: <BlockIcon /> },
            ].map((item, index) => (
              <ListItem key={index} disablePadding sx={{ display: 'block' }}>
                <ListItemButton
                  component={Link}
                  to={item.link}
                  sx={{
                    minHeight: 48,
                    justifyContent: open ? 'initial' : 'center',
                    px: 2.5,
                    mx: 1, my: .5,
                    color: '#fff',
                    bgcolor: location.pathname === item.link ? 'rgba(72,201,190,.24)' : 'transparent',
                    border: location.pathname === item.link ? '1px solid rgba(110,231,218,.28)' : '1px solid transparent',
                    borderRadius: '10px',
                    '&:hover': { bgcolor: 'rgba(255,255,255,.10)' }
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 0,
                      mr: open ? 3 : 'auto',
                      justifyContent: 'center',
                      '& .MuiSvgIcon-root': {
                        fontSize: open ? '36px' : '36px', // 收起狀態為18px，展開為24px
                        color: location.pathname === item.link ? '#63dfd0' : '#d7e8f3',
                      },
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText 
                    primary={item.text} 
                    sx={{ opacity: open ? 1 : 0,
                      '& .MuiTypography-root': {
                        fontSize: open ? '20px' : '14px', // 展開時16px，收起時14px
                        
                      },
                    }} 

                    />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
          <Divider />
          <List sx={{ marginTop: 'auto' }}>
            {[
              
              { text: 'Settings', link: config.rootPathPrefix + '/Settings' , icon: <SettingsIcon />},
              { text: 'User', link: config.rootPathPrefix + '/User' , icon: <AccountCircleIcon />},
            ].map((item, index) => (
              <ListItem key={index} disablePadding sx={{ display: 'block' }}>
                <ListItemButton
                  component={Link}
                  to={item.link}
                  sx={{
                    minHeight: 48,
                    justifyContent: open ? 'initial' : 'center',
                    px: 2.5,
                    mx: 1, my: .5, color: '#fff',
                    bgcolor: location.pathname === item.link ? 'rgba(72,201,190,.24)' : 'transparent',
                    borderRadius: '10px', '&:hover': { bgcolor: 'rgba(255,255,255,.10)' }
                  }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 0,
                      mr: open ? 3 : 'auto',
                      justifyContent: 'center',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.text} sx={{ opacity: open ? 1 : 0 }} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Drawer>
        <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
          <DrawerHeader />
          {/* <Typography paragraph>Ldgsfgsf</Typography>
          <Typography paragraph>Cfdgsdfgsd</Typography> */}
        </Box>
      </Box>
    </Box>
  );
}

export default Left_navigation;
