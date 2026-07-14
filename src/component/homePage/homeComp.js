import React from 'react';
import Main_info from './main_info.js';
import { Box, Typography, Paper } from '@mui/material';
import { styled } from '@mui/material/styles';
import CalendarViewMonthIcon from '@mui/icons-material/CalendarViewMonth';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import MonitorIcon from '@mui/icons-material/Monitor';
import SourceIcon from '@mui/icons-material/Source';
import SmsIcon from '@mui/icons-material/Sms';
import DescriptionIcon from '@mui/icons-material/Description';
import { Link } from 'react-router-dom';
import { config } from '../../constant';

const Container = styled(Box)({
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center', 
    alignItems: 'center',
    gap: '40px',
    width: '90%',
    minHeight: '80vh',
    padding: '20px',
});

const InfoBox = styled(Box)({
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '40px',
    width: '100%',
});

const InfoItem = styled(Box)({
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    padding: '20px',
    boxShadow: '0px 4px 10px rgba(0,0,0,0.1)',
    borderRadius: '12px',
    transition: 'transform 0.3s ease-in-out',
    '&:hover': {
        transform: 'scale(1.05)',
    }
});

const RightSection = styled(Paper)(({ theme }) => ({
    maxWidth: '1200px',
    padding: theme.spacing(4),
    textAlign: 'center',
    boxShadow: theme.shadows[3],
    borderRadius: '12px',
    backgroundColor: '#f5f5f5',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '50px'
}));

const IconStyle = {
    fontSize: '80px',
    color: '#1976d2'
};

function HomeComp() {
    return (
        <Container>
            {/* 上方內容 */}
            <Main_info />

            <InfoBox>
                {/* Job Results */}
                <InfoItem>
                    <Link to={config.rootPathPrefix + "/Job_results"} style={{ textDecoration: 'none' }}>
                        <CalendarViewMonthIcon sx={IconStyle} />
                    </Link>
                    <Typography variant="h5" fontWeight="bold">Job Results</Typography>
                    <Typography variant="body1">View and analyze job results in detail.</Typography>
                </InfoItem>

                {/* Analysis */}
                <InfoItem>
                    <Link to={config.rootPathPrefix + "/Analysis/Protocol"} style={{ textDecoration: 'none' }}>
                        <AnalyticsIcon sx={IconStyle} />
                    </Link>
                    <Typography variant="h5" fontWeight="bold">Analysis</Typography>
                    <Typography variant="body1">Perform various analyses based on protocols.</Typography>
                </InfoItem>

                {/* VUS Monitor */}
                <InfoItem>
                    <Link to={config.rootPathPrefix + "/VUS"} style={{ textDecoration: 'none' }}>
                        <MonitorIcon sx={IconStyle} />
                    </Link>
                    <Typography variant="h5" fontWeight="bold">VUS Monitor</Typography>
                    <Typography variant="body1">Monitor Variants of Uncertain Significance (VUS).</Typography>
                </InfoItem>

                {/* BioResources */}
                <InfoItem>
                    <SourceIcon sx={IconStyle} />
                    <Typography variant="h5" fontWeight="bold">BioResources</Typography>
                    <Typography variant="body1"></Typography>
                </InfoItem>

                {/* CallGeneLLM */}
                <InfoItem>
                    <SmsIcon sx={IconStyle} />
                    <Typography variant="h5" fontWeight="bold">CallGeneLLM</Typography>
                    <Typography variant="body1"></Typography>
                </InfoItem>

                {/* Tutorial */}
                <InfoItem>
                    <DescriptionIcon sx={IconStyle} />
                    <Typography variant="h5" fontWeight="bold">Tutorial</Typography>
                    <Typography variant="body1"></Typography>
                </InfoItem>
            </InfoBox>

            {/* 下方平台簡介 */}
            <RightSection>
                <Typography variant="h5" fontWeight="bold">Platform Overview</Typography>
                <Typography variant="body1" color="textSecondary">
                    This platform provides tools for analyzing germline and somatic variants.
                    It includes job results visualization, protocol-based analysis, and VUS monitoring.
                </Typography>
            </RightSection>
        </Container>
    );
}

export default HomeComp;
