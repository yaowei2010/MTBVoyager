import * as React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';
import TabPanel from '@mui/lab/TabPanel';
import TabList from '@mui/lab/TabList';
import TabContext from '@mui/lab/TabContext';


import Germline_Trio_table from './Germline_Trio_table';


function Incidental_Finding({   ACMGvariantsData, 
                                ACMGSelectionChange, 
                                ACMGrowSelectionModel, 
                                ACMGsetrowSelectionModel, 
                                OtherpathogenicVariantsData, 
                                OtherpathogenicSelectionChange,
                                OtherpathogenicrowSelectionModel,
                                OtherpathogenicsetrowSelectionModel,
                            }) 
    {
    const [value, setValue] = React.useState('1');

    const handleChange = (event, newValue) => {
        setValue(newValue);
    };

    return (

        <Box sx={{ width: '100%' }}>
            <TabContext value={value}>
                <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <TabList onChange={handleChange} 
                            aria-label="secondary tabs example"
                            textColor="secondary"
                            indicatorColor="secondary"
                    >
                        <Tab value="1" label="ACMG variants" />
                        <Tab value="2" label="Other pathogenic variants" />
                    </TabList>
                </Box>
                <TabPanel value="1">
                    <Germline_Trio_table
                        data={ACMGvariantsData}
                        onSelectionChange={ACMGSelectionChange}
                        rowSelectionModel={ACMGrowSelectionModel}
                        setrowSelectionModel={ACMGsetrowSelectionModel}
                        />
                    {/* <ACMG_variants 
                        ACMGvariantsData={ACMGvariantsData} 
                        ACMGSelectionChange={ACMGSelectionChange}
                        ACMGrowSelectionModel={ACMGrowSelectionModel}
                        ACMGsetrowSelectionModel={ACMGsetrowSelectionModel}
                    /> */}
                </TabPanel>
                <TabPanel value="2">
                    <Germline_Trio_table
                        data={OtherpathogenicVariantsData}
                        onSelectionChange={OtherpathogenicSelectionChange}
                        rowSelectionModel={OtherpathogenicrowSelectionModel}
                        setrowSelectionModel={OtherpathogenicsetrowSelectionModel}
                        />
                    {/* <Other_pathogenic_variants 
                        OtherpathogenicVariantsData={OtherpathogenicVariantsData} 
                        OtherpathogenicSelectionChange={OtherpathogenicSelectionChange}
                        OtherpathogenicrowSelectionModel={OtherpathogenicrowSelectionModel}
                        OtherpathogenicsetrowSelectionModel={OtherpathogenicsetrowSelectionModel} 
                    /> */}
                </TabPanel>
            </TabContext>
        </Box>
        
        
    );
    }

    export default Incidental_Finding;