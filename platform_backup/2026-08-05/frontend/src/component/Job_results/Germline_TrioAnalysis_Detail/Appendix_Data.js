import * as React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';
import TabPanel from '@mui/lab/TabPanel';
import TabList from '@mui/lab/TabList';
import TabContext from '@mui/lab/TabContext';

import SV_CNV from './Appendix_Data_table/SV_CNV';

export default function Appendix_Data({ htmlContent }) {
  const [value, setValue] = React.useState('1');
  

  const handleChange = (event, newValue) => {
    setValue(newValue);
  };

  return (
    <Box sx={{ width: '100%' }}>
      <TabContext value={value}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <TabList onChange={handleChange} aria-label="secondary tabs example" textColor="secondary" indicatorColor="secondary">
            <Tab value="1" label="SV/CNV" />
            <Tab value="2" label="CNV plot" />
            
          </TabList>
        </Box>
        <TabPanel value="1">
          <SV_CNV htmlContent={htmlContent} />
        </TabPanel>
        <TabPanel value="2">CNV plot</TabPanel>
        
      </TabContext>
    </Box>
  );
}
