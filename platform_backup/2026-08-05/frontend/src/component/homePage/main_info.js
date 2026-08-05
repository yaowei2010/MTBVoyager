import * as React from 'react';
import { Paper, Box, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

const DemoPaper = styled(Paper)(({ theme }) => ({
    width: '100%',
    maxWidth: '1200px',
    minHeight: '280px',
    padding: theme.spacing(4),
    textAlign: 'center',
    boxShadow: theme.shadows[3],
    borderRadius: '24px',
    // 移除原本的 backgroundColor
    // backgroundColor: '#f5f5f5',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    
    /* ===== 下面為背景設定重點 ===== */
    // 先用線性漸層加一層黑色透明度，再放背景圖，讓背景圖看起來變暗
    background: `linear-gradient(120deg, rgba(7,35,59,.82), rgba(8,105,104,.68)), url('/img/DNA_2.jpg')`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    // 設定文字顏色為白色，才能清楚顯示在深色背景上
    color: '#fff',
}));

export default function Main_info() {
    return (
        <Box display="flex" justifyContent="center" width="100%" alignSelf="center">
            <DemoPaper>
                <Typography variant="h3" sx={{ fontWeight: 800, fontSize: { xs: 30, md: 44 } }} gutterBottom>
                    國立成功大學醫學院附設醫院
                </Typography>
                <Typography variant="h5" color="inherit" sx={{ opacity: .9, fontWeight: 500 }}>
                    Germline and Somatic Variant Analysis and Annotation Platform
                </Typography>
            </DemoPaper>
        </Box>
    );
}
