
import Radio from '@mui/material/Radio';
import FormControlLabel from '@mui/material/FormControlLabel';
import TextField from '@mui/material/TextField';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import React, { useState , useEffect } from 'react';
import { Grid, Button } from '@mui/material';
import gene_panel_auto__data from './gene_panel_data.json'
import axios from 'axios';
import InputAdornment from '@mui/material/InputAdornment';
import { config } from '../../../../constant';


function ContentA({ panel_auto_Info, setPanelInfo  }) {

    const [selectedOption, setSelectedOption] = useState('');
    
    const handleSelectChange = (event) => {
        const selectedValue = event.target.value;
        setSelectedOption(selectedValue);
        
        // 在这里根据选项值设置panelName和genes
        const selectedPanel = gene_panel_auto__data[selectedValue];
        if (selectedPanel) {
            setPanelInfo({
                panelName: selectedPanel.panelName,
                genes: selectedPanel.genes,
            });
        } else {
            setPanelInfo({ panelName: '', genes: '' }); // 如果未找到匹配的选项，清空panelInfo
        }
    };

    return (
        <div style={{  marginTop: '1rem' }}>
            <FormControl sx={{ m: 1, minWidth: 320 }}>
                <InputLabel 
                    htmlFor="select_expert_panel"
                    sx={{
                        fontSize: '18px', // 調整選項字體大小
                    }}
                    >
                        select expert panel
                </InputLabel>
                <Select
                    native
                    value={selectedOption}
                    onChange={handleSelectChange}
                    id="select_expert_panel"
                    label="Grouping"
                    sx={{
                        fontSize: '22px', // 調整收起時的字體大小
                        '& .MuiInputBase-input': {
                            fontSize: '22px', // 控制顯示選擇值的字體大小
                        },
                        '& option': {
                            fontSize: '18px', // 調整選單展開後選項的字體大小
                        },
                    }}
                >
                <option aria-label="None" value="" disabled  />
                <optgroup label="Dermatology">
					<option value="EB">Epidermolysis bullosa</option>
					<option value="ED">Ectodermal dysplasia</option>
					<option value="PPKandPC">PPK and PC</option>
					<option value="ichthyosis">Ichthyosis</option>
					<option value="inflammatory">Inflammatory genodermatoses</option>
					<option value="pigmentary">Pigmentary genodermatoses</option>
					<option value="epidermal">Epidermal genodermatoses</option>
					<option value="skinTumoral">Skin tumoral genodermatoses</option>
					<option value="miscellaneous">Miscellaneous genodermatoses</option>
				</optgroup>
				<optgroup label="Ophthalmology">
					<option value="corneal_dystrophy">Corneal dystrophy</option>
					<option value="lens_disease">Lens disease</option>
					<option value="retina_disease">Retina disease</option>
				</optgroup>
				<optgroup label="Otology">
					<option value="NSHLandSHL">Non-syndromic and syndromic hearing loss</option>
					<option value="otosclerosis">Otosclerosis</option>
				</optgroup>
				<optgroup label="Pediatric gynaecology">
					<option value="DSD">Disorders of sexual development</option>
					<option value="NMD">Neuromuscular disorders</option>
					<option value="DSCT">Diseases of the skeletal and connective tissue</option>
					<option value="metabolic">Metabolic disorder</option>
					<option value="kidney">Kidney disease</option>
					<option value="heart">Heart disease</option>
				</optgroup>
				<optgroup label="Neurology">
					<option value="youngStroke">Young stroke</option>
					<option value="myopathyCMS">Myopathy, CMS</option>
					<option value="ALSandHSP">ALS, HSP</option>
					<option value="PDandDystonia">PD, dystonia</option>
				</optgroup>
				<optgroup label="Cancer and cardiotoxicity">
					<option value="hereditaryCancer">Hereditary Cancer</option>
					<option value="cardiotoxicity">Cardiotoxicity</option>
				</optgroup>
                </Select>
            </FormControl>
        </div>
    );
}




function ContentB({ panel_auto_Info, setPanelInfo }) {
  const [hpoId, setHpoId] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSetClick = async () => {
  if (!hpoId.trim()) return;

  const fullHpoId = `HP:${hpoId.trim()}`;
  console.log('HPO ID:', fullHpoId);

  setLoading(true);
  try {
    const response = await axios.post(`${config.rootApiIP}/HPO_search`, {
      HPO: fullHpoId,
    });

    console.log('HPO API 回應:', response.data);

    const { hpo_name, gene_list } = response.data;

    setPanelInfo({
      panelName: hpo_name || `From HPO ${fullHpoId}`,
      genes: Array.isArray(gene_list) ? gene_list.join('\n') : '',
    });
  } catch (error) {
    console.error('HPO API 發生錯誤:', error);
    setPanelInfo({ panelName: `Error: ${fullHpoId}`, genes: '' });
  } finally {
    setLoading(false);
  }
};

  return (
    <Grid container spacing={2} alignItems="center">
      <Grid item xs={8}>
        <label style={{ fontSize: '24px' }}>Enter HPO-Term ID: </label>
        <TextField
          fullWidth
          hiddenLabel
          id="hpo_term_id"
          variant="filled"
          size="small"
          value={hpoId}
          onChange={(e) => setHpoId(e.target.value)}
          InputProps={{
            startAdornment: (
                          <InputAdornment position="start">
                            <span style={{ fontSize: '24px' }}>HP:</span>
                          </InputAdornment>
                        ),
            sx: {
              fontSize: '20px',
            },
          }}
          InputLabelProps={{
            sx: {
              fontSize: '22px',
            },
          }}
        />
      </Grid>
      <Grid item xs={4}>
        <Button
          variant="contained"
          onClick={handleSetClick}
          disabled={loading}
          sx={{
            marginTop: '34px',
            height: '56px',
            fontSize: '18px',
            width: '100%',
            bgcolor: '#1976d2',
            '&:hover': { bgcolor: '#1565c0' },
          }}
        >
          {loading ? 'Loading...' : 'Set'}
        </Button>
      </Grid>
    </Grid>
  );
}





function Radio_change({ panel_auto_Info, setPanelInfo  }) {
    
    const [selectedValue, setSelectedValue] = React.useState('a');

    const handleChange = (event) => {
        const value = event.target.value;
        setSelectedValue(value);

        // 根据选中的值设置要显示的内容组件
        if (value === 'a') {
            setContentToDisplay(<ContentA panel_auto_Info ={panel_auto_Info} setPanelInfo={setPanelInfo} />);
        } else if (value === 'b') {
            setContentToDisplay(<ContentB panel_auto_Info={panel_auto_Info} setPanelInfo={setPanelInfo} />);
        }
    };

    const [contentToDisplay, setContentToDisplay] = React.useState(<ContentA panel_auto_Info ={panel_auto_Info} setPanelInfo={setPanelInfo}  />);

    return (
        <div>
            <FormControlLabel
                value="a"
                control={<Radio checked={selectedValue === 'a'} onChange={handleChange} />}
                label="Select expert panel"
                labelPlacement="end"
                sx={{
                    '& .MuiFormControlLabel-label': {
                    fontSize: '18px',
                    },
                }}
            />
            <FormControlLabel
                value="b"
                control={<Radio checked={selectedValue === 'b'} onChange={handleChange} />}
                label="Input by HPO-term"
                labelPlacement="end"
                sx={{
                    '& .MuiFormControlLabel-label': {
                    fontSize: '18px',
                    },
                }}
            />
            <div>{contentToDisplay}</div>
        </div>
    );
}
export default Radio_change;
