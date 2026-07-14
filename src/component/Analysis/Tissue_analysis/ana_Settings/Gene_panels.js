import React, { useState, useEffect } from 'react';
import { Grid, Box, Typography, TextField } from '@mui/material';

function Gene_panels({ index, panelData, onChange, panel_auto_Info, setPanelInfo, autoFillTargetIndex, }) {
  // 控制是否啟用自動填入，預設為 true
  const [isAutoFillActive, setIsAutoFillActive] = useState(true);

  // 格式化基因資料：將每個換行符號(\n)替換為「、」
  // 每10個基因後若需要換行，可再擴充此函式，目前僅用「、」連接
  const formatGenes = (geneStr) => {
    if (!geneStr) return '';
    const genesArray = geneStr.split('\n').filter(g => g.trim() !== '');
    let result = '';
    for (let i = 0; i < genesArray.length; i++) {
      result += genesArray[i];
      if (i !== genesArray.length - 1) {
        result += "、";
      }
    }
    return result;
  };

  const handlePanelNameChange = (event) => {
    const newData = { ...panelData, panelName: event.target.value };
    onChange(index, newData);
    setIsAutoFillActive(false); // 一旦使用者手動修改，就關閉自動填入狀態
  };

  const handleGenesChange = (event) => {
    const newData = { ...panelData, genes: event.target.value };
    onChange(index, newData);
    setIsAutoFillActive(false);
  };

  useEffect(() => {
  if (
    index === autoFillTargetIndex && // 只 auto-fill 目前選中的那筆
    isAutoFillActive &&
    panel_auto_Info.panelName &&
    panel_auto_Info.genes
  ) {
    const formattedGenes = formatGenes(panel_auto_Info.genes);
    if (
      panelData.panelName !== panel_auto_Info.panelName ||
      panelData.genes !== formattedGenes
    ) {
      const newData = {
        panelName: panel_auto_Info.panelName,
        genes: formattedGenes,
      };
      onChange(index, newData);
    }
  }
}, [panel_auto_Info, index, onChange, panelData, isAutoFillActive, autoFillTargetIndex]);

  return (
    
    <Grid item xs={12}>
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12}>
          <Typography sx={{ fontWeight: 'bold', fontSize: '22px' }}>
            Extra gene for panel {index + 1} (optional)
          </Typography>
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Enter additional gene(s), separate with 、"
            variant="outlined"
            value={panelData.extraGene || ''}
            onChange={(e) =>
              onChange(index, { extraGene: e.target.value })
            }
          />
        </Grid>
      </Grid>
      <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
        Gene panels {index + 1}
      </Typography>
      <Box
        // 移除固定的 height 設定讓容器可隨內部內容自動延伸
        width={700}
        my={2}
        display="flex"
        gap={4}
        p={2}
        sx={{ border: '2px solid grey' }}
        borderRadius={6}
      >
        <div style={{ display: 'flex', flexDirection: 'column', marginBottom: '20px', width: '100%' }}>
          <label style={{ fontSize: '18px', marginLeft: '5px' }}>
            Panel name {index + 1}
          </label>
          <TextField
            disabled={isAutoFillActive && panel_auto_Info.panelName && panel_auto_Info.genes}
            hiddenLabel
            id={`Panel_name_${index}`}
            variant="filled"
            size="small"
            style={{ width: '660px', marginBottom: '70px' }}
            value={panelData.panelName}
            onChange={handlePanelNameChange}
            InputProps={{
              sx: { fontSize: '20px' },
            }}
            InputLabelProps={{
              sx: { fontSize: '22px' },
            }}
          />
          <label style={{ fontSize: '18px', marginLeft: '5px' }}>
            Genes {index + 1}
          </label>
          <TextField
            disabled={isAutoFillActive && panel_auto_Info.panelName && panel_auto_Info.genes}
            hiddenLabel
            id={`Genes_${index}`}
            variant="filled"
            size="small"
            multiline
            // 使用 minRows 讓輸入框根據內容自動調整高度
            minRows={3}
            // 不設定固定 height
            style={{ width: '660px', overflow: 'hidden' }}
            value={panelData.genes}
            onChange={handleGenesChange}
            InputProps={{
              sx: { fontSize: '20px', overflow: 'hidden' },
            }}
            InputLabelProps={{
              sx: { fontSize: '22px' },
            }}
          />
        </div>
      </Box>
    </Grid>
  );
}

export default Gene_panels;
