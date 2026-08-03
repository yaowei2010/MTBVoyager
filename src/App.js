import logo from './logo.svg';
import './App.css';
import HomeComp from './component/homePage/homeComp';
import Job_results from './component/Job_results/Job_results.js';
import Job_results_detail_germline from './component/Job_results/Germline_ExomeAnalysis_Detail/Job_results_detail_germline.js';
import Job_results_detail_hg38 from './component/Job_results/Germline_ExomeAnalysis_Detail/Job_results_detail_germline_hg38.js';
import Job_results_detail_germline_trio from './component/Job_results/Germline_TrioAnalysis_Detail/Job_results_detail_germline.js';
import Job_results_detail_somatic from './component/Job_results/Somatic_TissueOnly_Detail/Job_results_detail_somatic.js';
import Job_results_detail_report_germline from './component/Job_results/Germline_ExomeAnalysis_Detail/Job_results_detail_report_germline.js';
import Job_results_detail_report_germline_trio from './component/Job_results/Germline_TrioAnalysis_Detail/Job_results_detail_report_germline_trio.js'
import Job_results_detail_report_somatic from './component/Job_results/Somatic_TissueOnly_Detail/Job_results_detail_report_somatic.js';

import Analysis_protocol from './component/Analysis/Protocol/Analysis_protocol.js';

import Exome_subject from './component/Analysis/Exome_analysis/Subject/Analysis_subject.js';
import Exome_sample from './component/Analysis/Exome_analysis/ana_Sample/Analysis_sample.js';
import Exome_setting from './component/Analysis/Exome_analysis/ana_Settings/Analysis_settings.js'

import Exome_trio_subject from './component/Analysis/Exome_Trio_analysis/Subject/Analysis_subject.js'
import Exome_trio_sample from './component/Analysis/Exome_Trio_analysis/ana_Sample/Analysis_sample.js'
import Exome_trio_setting from './component/Analysis/Exome_Trio_analysis/ana_Settings/Analysis_settings.js'

import Tissue_subject from './component/Analysis/Tissue_analysis/Subject/Analysis_subject.js';
import Tissue_sample from './component/Analysis/Tissue_analysis/ana_Sample/Analysis_sample.js';
import Tissue_setting from './component/Analysis/Tissue_analysis/ana_Settings/Analysis_settings.js';
import WgsGermlineSubject from './component/Analysis/WGS_Germline/WgsGermlineSubject.js';
import WgsGermlineSample from './component/Analysis/WGS_Germline/WgsGermlineSample.js';
import WgsGermlineSettings from './component/Analysis/WGS_Germline/WgsGermlineSettings.js';
import WgsGermlineResult from './component/Job_results/WGS_Germline_Detail/WgsGermlineResult.js';
import WgsSomaticSubject from './component/Analysis/WGS_Somatic/WgsSomaticSubject.js';
import WgsSomaticSample from './component/Analysis/WGS_Somatic/WgsSomaticSample.js';
import WgsSomaticSettings from './component/Analysis/WGS_Somatic/WgsSomaticSettings.js';
import WgsSomaticResult from './component/Job_results/WGS_Somatic_Detail/WgsSomaticResult.js';
import VUS from './component/VUS/vus.js';

import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom';
import { config } from './constant';
import PrivateRoute from './privateRoute.js';
import 'bootstrap/dist/css/bootstrap.min.css';
import { CssBaseline, ThemeProvider } from '@mui/material';
import clinicalTheme from './clinicalTheme';

import LoginPage from './component/Auth/LoginPage.js';
import RegisterPage from './component/Auth/RegisterPage.js';

import { AuthProvider } from './component/Auth/AuthContext.js';
import BlacklistPage from "./component/Blacklist/Blacklist_main.js";
import BlacklistAdd from "./component/Blacklist/Blacklist_add.js";

function App() {
  return (
    <ThemeProvider theme={clinicalTheme}>
      <CssBaseline />
      <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path={config.rootPathPrefix + "/"}element={<Navigate to={config.rootPathPrefix + "/login"} replace />}/>
          <Route path={config.rootPathPrefix + "/login"} element={<LoginPage />} />
          <Route path={config.rootPathPrefix + "/register"} element={<RegisterPage />} />
          
          <Route element = { <PrivateRoute /> } >
          
            <Route path = { config.rootPathPrefix + "/home" } element = { <HomeComp /> }></Route>

            <Route path = { config.rootPathPrefix + "/Job_results" } element = { <Job_results /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail_germline/:analysis_ID" } element = { <Job_results_detail_germline /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail_germline_hg38/:analysis_ID" } element = { <Job_results_detail_hg38 /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail_germline_trio/:analysis_ID" } element = { <Job_results_detail_germline_trio /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail_somatic/:analysis_ID" } element = { <Job_results_detail_somatic /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail_wgs_germline/:analysis_ID" } element = { <WgsGermlineResult /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail_wgs_somatic/:analysis_ID" } element = { <WgsSomaticResult /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail/:analysis_ID/summary_report_germline" } element = { <Job_results_detail_report_germline /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail/:analysis_ID/summary_report_germline_trio" } element = { <Job_results_detail_report_germline_trio /> }></Route>
            <Route path = { config.rootPathPrefix + "/Job_results/detail/:analysis_ID/summary_report_somatic" } element = { <Job_results_detail_report_somatic /> }></Route>
            
            <Route path = { config.rootPathPrefix + "/Analysis/Protocol" } element = { <Analysis_protocol /> }></Route>

            <Route path = { config.rootPathPrefix + "/Analysis/Exome/Subject" } element = { <Exome_subject /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/Exome/Sample" } element = { <Exome_sample /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/Exome/Settings" } element = { <Exome_setting /> }></Route>

            <Route path = { config.rootPathPrefix + "/Analysis/Exome_Trio/Subject" } element = { <Exome_trio_subject /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/Exome_Trio/Sample" } element = { <Exome_trio_sample /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/Exome_Trio/Settings" } element = { <Exome_trio_setting  /> }></Route>

            <Route path = { config.rootPathPrefix + "/Analysis/Tissue/Subject" } element = { <Tissue_subject /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/Tissue/Sample" } element = { <Tissue_sample /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/Tissue/Settings" } element = { <Tissue_setting /> }></Route>

            <Route path = { config.rootPathPrefix + "/Analysis/WGS_hg38_Germline" } element = { <Navigate to={config.rootPathPrefix + "/Analysis/WGS_Germline/Subject"} replace /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/WGS_Germline/Subject" } element = { <WgsGermlineSubject /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/WGS_Germline/Sample" } element = { <WgsGermlineSample /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/WGS_Germline/Settings" } element = { <WgsGermlineSettings /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/WGS_hg38_Somatic" } element = { <Navigate to={config.rootPathPrefix + "/Analysis/WGS_Somatic/Subject"} replace /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/WGS_Somatic/Subject" } element = { <WgsSomaticSubject /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/WGS_Somatic/Sample" } element = { <WgsSomaticSample /> }></Route>
            <Route path = { config.rootPathPrefix + "/Analysis/WGS_Somatic/Settings" } element = { <WgsSomaticSettings /> }></Route>

            <Route path = { config.rootPathPrefix + "/VUS" } element = { <VUS /> }></Route>
            <Route path = { config.rootPathPrefix + "/Blacklist" } element = { <BlacklistPage  /> }></Route>
            <Route path={config.rootPathPrefix + "/blacklist/add"} element={<BlacklistAdd />} />
          </Route>  
        </Routes>
      </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;























//                        _ooOoo
//                       o8888888o
//                       88" . "88 
//                       (| -_- |)
//                       O\  =  /O
//                     ___/`---'\____
//                  .'  \\|     |//  `.
//                 /  \\|||  :  |||//  \
//                /  _||||| -:- |||||_  \
//                |   | \\\  -  /// |   |
//                | \_|  ''\---/''  |   |
//                \  .-\__       __/-.  /
//              ___`. .'  /--.--\ `. . __
//           ."" '<  `.___\_<|>_/__.'  >'"".
//          | | :  `- \`.;`\ _ /`;.`/ - ` : | |
//          \  \ `-.   \_ __\ /__ _/   .-` /  /
//     ======`-.____`-.___\_____/___.-`____.-'======
//                        `=---='
//  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
//                 佛祖保佑       永無BUG

//                         ~  ~  ~
//                        |  |  |
//                        |  |  |
//                      ( |  |  | ) 
//                       |       | 
//                       |_______|




//                           |~~~~~~~|
//                           |       |
//                           |       |
//                           |       |
//                           |       |
//                           |       |
// |~.\\\_\~~~~~~~~~~~~~~xx~~~         ~~~~~~~~~~~~~~~~~~~~~/_//;~|
// |  \  o \_         ,XXXXX),                         _..-~ o /  |
// |    ~~\  ~-.     XXXXX`)))),                 _.--~~   .-~~~   |
// ~~~~~~~`\   ~\~~~XXX' _/ ';))     |~~~~~~..-~     _.-~ ~~~~~~~
//           `\   ~~--`_\~\, ;;;\)__.---.~~~      _.-~
//             ~-.       `:;;/;; \          _..-~~
//               ~-._      `''        /-~-~
//                   `\              /  /
//                     |         ,   | |
//                       |  '        /  |
//                       \/;          |
//                         ;;          |
//                         `;   .       |
//                         |~~~-----.....|
//                       | \             \
//                       | /\~~--...__    |
//                       (|  `\       __-\|
//                       ||    \_   /~    |
//                       |)     \~-'      |
//                       |      | \      '
//                       |      |  \    :
//                         \     |  |    |
//                         |    )  (    )
//                           \  /;  /\  |
//                           |    |/   |
//                           |    |   |
//                           \  .'  ||
//                           |  |  | |
//                           (  | |  |
//                           |   \ \ |
//                           || o `.)|
//                           |`\\\\) |
//                           |       |
//                           |       |
// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

//                 耶穌保佑                永無 BUG
