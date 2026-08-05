import React, { useContext, useState } from 'react';
import { Alert, Box, Button, Grid, Paper, Stack, TextField, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { config } from '../../../constant';
import { AuthContext } from '../../Auth/AuthContext';
import { cardSx, contentSx, pageSx, primaryButtonSx, secondaryButtonSx } from '../WGS_Germline/wgsUi';

export default function WgsSomaticSubject() {
  const navigate=useNavigate(); const { userId }=useContext(AuthContext);
  const [form,setForm]=useState({subject_id:'',dob:'',gender:'unknown',history:''}); const [error,setError]=useState(''); const [busy,setBusy]=useState(false);
  const submit=async()=>{ if(!form.subject_id.trim()) return setError('Tumor sample ID is required.'); setBusy(true);setError('');
    try { const {data}=await axios.post(`${config.rootApiIP}/wgs-somatic/subjects`,{...form,user_id:userId}); sessionStorage.setItem('wgsSomaticDraft',JSON.stringify({draft_id:data.draft_id,subject:form})); navigate(`${config.rootPathPrefix}/Analysis/WGS_Somatic/Sample`); }
    catch(e){setError(e.response?.data?.detail||'Unable to create WGS somatic analysis.');} finally{setBusy(false);} };
  return <Box sx={pageSx}><Box sx={contentSx}><Typography variant="h3" fontWeight={800}>WGS Somatic Tumor-Only</Typography><Typography color="text.secondary" sx={{mb:3}}>GRCh38 caller-produced SNV, SV and CNV interpretation</Typography>{error&&<Alert severity="error" sx={{mb:2}}>{error}</Alert>}<Paper sx={cardSx}><Grid container spacing={3}><Grid item xs={12} md={6}><TextField required fullWidth label="Tumor sample ID" value={form.subject_id} onChange={e=>setForm({...form,subject_id:e.target.value})}/></Grid><Grid item xs={12} md={6}><TextField disabled fullWidth label="Protocol" value="WGS Somatic Tumor-Only (GRCh38)"/></Grid><Grid item xs={12} md={6}><TextField fullWidth type="date" label="Date of birth" InputLabelProps={{shrink:true}} value={form.dob} onChange={e=>setForm({...form,dob:e.target.value})}/></Grid><Grid item xs={12} md={6}><TextField fullWidth label="Sex" value={form.gender} onChange={e=>setForm({...form,gender:e.target.value})}/></Grid><Grid item xs={12}><TextField fullWidth multiline rows={3} label="Cancer history / specimen context" value={form.history} onChange={e=>setForm({...form,history:e.target.value})}/></Grid></Grid></Paper><Stack direction="row" spacing={2} justifyContent="center" sx={{mt:4}}><Button variant="outlined" sx={secondaryButtonSx} onClick={()=>navigate(`${config.rootPathPrefix}/Analysis/Protocol`)}>Previous</Button><Button variant="contained" sx={primaryButtonSx} disabled={busy} onClick={submit}>{busy?'Saving…':'Continue'}</Button></Stack></Box></Box>;
}
