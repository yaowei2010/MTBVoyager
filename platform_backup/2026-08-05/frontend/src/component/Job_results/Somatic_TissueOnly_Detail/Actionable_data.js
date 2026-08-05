import * as React from 'react';
import {
  Box,
  Collapse,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Paper,
  Checkbox,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import Button from '@mui/material/Button';

/**
 * 共用：渲染條列式的描述
 */
function ParsedDescription({ desc }) {
  if (!desc) {
    return (
      <Typography variant="body2" color="text.secondary">
        No detail data
      </Typography>
    );
  }

  let text = desc.trim();
  if (text.startsWith('Description:')) {
    text = text.replace(/^Description:/, '').trim();
  }

  const parts = text.split('||').map((s) => s.trim()).filter(Boolean);

  if (parts.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No detail data
      </Typography>
    );
  }

  return (
    <>
      {parts.map((part, idx) => {
        let content;
        try {
          let parsed = part;
          if (parsed.startsWith('{')) {
            parsed = JSON.parse(parsed);
          }

          if (typeof parsed === 'object') {
            content = (
              <Box sx={{ mt: idx > 0 ? 2 : 0, mb: 1, p: 1, bgcolor: '#f9f9f9', border: '1px solid #ddd', borderRadius: '6px' }}>
                {/* <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Detail Block {idx + 1}
                </Typography> */}
                {Object.entries(parsed).map(([key, value]) => (
                  <div key={key} style={{ marginBottom: '4px' }}>
                    <strong>{key}:</strong>{' '}
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </div>
                ))}
              </Box>
            );
          } else {
            content = (
              <Typography variant="body2">{String(parsed)}</Typography>
            );
          }
        } catch (e) {
          content = (
            <Typography variant="body2">{part}</Typography>
          );
        }

        return (
          <Box key={idx}>
            {content}
          </Box>
        );
      })}
    </>
  );
}



function Row({ row, onRankChange, isSelected, onSelect }) {
  const [open, setOpen] = React.useState(false);
  const [detailOpenIndex, setDetailOpenIndex] = React.useState(null);

  const avalArr = Array.isArray(row.Avalibility)
    ? row.Avalibility
    : typeof row.Avalibility === 'string'
    ? row.Avalibility.split(';').map((s) => s.trim())
    : [];

  const descArr = Array.isArray(row.AvalibilityDescription)
    ? row.AvalibilityDescription
    : [];

  const sourcePriority = {
    oncokb: 0,
    civic: 1,
    cgi: 2,
    cosmic: 3,
    mycancergenome: 4,
  };

  const pairs = avalArr
    .map((item, idx) => ({
      item,
      desc: descArr[idx] || '無詳細說明',
    }))
    .sort((a, b) => {
      const srcA = (a.item.split(',')[2] || '').trim().toLowerCase();
      const srcB = (b.item.split(',')[2] || '').trim().toLowerCase();
      return (sourcePriority[srcA] ?? 99) - (sourcePriority[srcB] ?? 99);
    });

  const validPairs = [];
  const invalidPairs = [];

  pairs.forEach((p) => {
    let descText = p.desc;
    let isPrimaryResistance = false;

    if (typeof descText === "string" && descText.startsWith("Description:")) {
      descText = descText.replace(/^Description:/, "").trim();
    }

    if (typeof descText === "string" && descText.startsWith("{")) {
      try {
        const parsed = JSON.parse(descText);
        if (parsed && parsed["Predicted Response"]) {
          const response = parsed["Predicted Response"];
          if (
            response === "Primary Resistance" ||
            (Array.isArray(response) && response.includes("Primary Resistance"))
          ) {
            isPrimaryResistance = true;
          }
        }
      } catch {
        // Ignore parse error
      }
    }

    if (isPrimaryResistance) {
      invalidPairs.push(p);
    } else {
      validPairs.push(p);
    }
  });

  const mainAval = validPairs[0]?.item || '';

  return (
    <>
      <TableRow>
        <TableCell padding="checkbox">
          <Checkbox checked={isSelected} onChange={() => onSelect(row.id)} />
        </TableCell>
        <TableCell width={48}>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>
          <FormControl size="small" sx={{ minWidth: 90 }}>
            <InputLabel id={`rank-${row.id}`}>選擇</InputLabel>
            <Select
              labelId={`rank-${row.id}`}
              value={row.rankValue || '1'}
              label="選擇"
              onChange={(e) => onRankChange(row.id, e.target.value)}
            >
              <MenuItem value="1">Group 1</MenuItem>
              <MenuItem value="2">Group 2</MenuItem>
              <MenuItem value="3">Group 3</MenuItem>
            </Select>
          </FormControl>
        </TableCell>
        <TableCell>{row.Location}</TableCell>
        <TableCell>{row.Gene}</TableCell>
        <TableCell>{row.RSID}</TableCell>
        <TableCell>{row.Match}</TableCell>
        <TableCell>{row.AminoAcidChange}</TableCell>
        <TableCell>{mainAval}</TableCell>
      </TableRow>

      <TableRow>
        <TableCell colSpan={9} sx={{ p: 0, border: 0 }}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ p: 2, bgcolor: '#fafafa' }}>
              {/* Avalibility */}
              <Typography variant="subtitle2" gutterBottom>
                Avalibility
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Tier</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Drug</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Database</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Count</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {validPairs.length > 0 ? (
                    validPairs.map(({ item, desc }, i) => {
                      const [tier, drug, db, cnt] = item.split(',').map((s) => s.trim());
                      const isDetailOpen = detailOpenIndex === i;
                      return (
                        <React.Fragment key={i}>
                          <TableRow>
                            <TableCell>{tier}</TableCell>
                            <TableCell>{drug}</TableCell>
                            <TableCell>{db}</TableCell>
                            <TableCell>{cnt}</TableCell>
                            <TableCell>
                              <Button
                                variant="contained"
                                size="small"
                                onClick={() =>
                                  setDetailOpenIndex(isDetailOpen ? null : i)
                                }
                                sx={{
                                  backgroundColor: '#87CEEB',
                                  color: '#fff',
                                  borderRadius: '6px',
                                  textTransform: 'none',
                                  '&:hover': {
                                    backgroundColor: '#6fb7d6',
                                  },
                                }}
                              >
                                {isDetailOpen ? 'Hide' : 'Detail'}
                              </Button>
                            </TableCell>
                          </TableRow>
                          {isDetailOpen && (
                            <TableRow>
                              <TableCell colSpan={5} sx={{ p: 0, border: 0 }}>
                                <Box
                                  sx={{
                                    p: 2,
                                    bgcolor: '#f0f0f0',
                                    width: '100%',
                                    maxHeight: '200px',
                                    overflowY: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    margin: '0 auto',
                                  }}
                                >
                                  <ParsedDescription desc={desc} />
                                </Box>
                              </TableCell>
                            </TableRow>
                          )}
                        </React.Fragment>
                      );
                    })
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        No Avalibility details
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>

              {/* UnAvalibility */}
              {invalidPairs.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ mt: 3 }}>
                    UnAvalibility
                  </Typography>
                  <Table size="small" sx={{ mt: 1 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Drug</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Database</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Count</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>Details</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {invalidPairs.map(({ item, desc }, i) => {
                      const [, drug, db, cnt] = item.split(',').map((s) => s.trim());
                      const isDetailOpen = detailOpenIndex === `invalid-${i}`;
                      return (
                        <React.Fragment key={`invalid-${i}`}>
                          <TableRow>
                            <TableCell>{drug}</TableCell>
                            <TableCell>{db}</TableCell>
                            <TableCell>{cnt}</TableCell>
                            <TableCell>
                              <Button
                                variant="contained"
                                size="small"
                                onClick={() =>
                                  setDetailOpenIndex(isDetailOpen ? null : `invalid-${i}`)
                                }
                                sx={{
                                  backgroundColor: '#87CEEB',
                                  color: '#fff',
                                  borderRadius: '6px',
                                  textTransform: 'none',
                                  '&:hover': {
                                    backgroundColor: '#6fb7d6',
                                  },
                                }}
                              >
                                {isDetailOpen ? 'Hide' : 'Detail'}
                              </Button>
                            </TableCell>
                          </TableRow>
                          {isDetailOpen && (
                            <TableRow>
                              <TableCell colSpan={4} sx={{ p: 0, border: 0 }}>
                                <Box
                                  sx={{
                                    p: 2,
                                    bgcolor: '#f0f0f0',
                                    width: '100%',
                                    maxHeight: '200px',
                                    overflowY: 'auto',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    margin: '0 auto',
                                  }}
                                >
                                  <ParsedDescription desc={desc} />
                                </Box>
                              </TableCell>
                            </TableRow>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </TableBody>

                  </Table>
                </>
              )}

              {/* Other Details */}
              <Typography variant="subtitle2" sx={{ mt: 3 }}>
                Other Details
              </Typography>
              <Table size="small" sx={{ mt: 1 }}>
                <TableBody>
                  {row.MAF && (
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600, width: 130 }}>MAF</TableCell>
                      <TableCell>{row.MAF}</TableCell>
                    </TableRow>
                  )}
                  {row.Domain && (
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Domain</TableCell>
                      <TableCell>{row.Domain}</TableCell>
                    </TableRow>
                  )}
                  {row.Pathogenicity && (
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Pathogenicity</TableCell>
                      <TableCell>{row.Pathogenicity}</TableCell>
                    </TableRow>
                  )}
                  {row.Prediction && (
                    <TableRow>
                      <TableCell sx={{ fontWeight: 600 }}>Prediction</TableCell>
                      <TableCell>{row.Prediction}</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export default function ActionableCollapsibleTable({ data = [], onSelectionChange }) {
  const [rows, setRows] = React.useState([]);
  const [selected, setSelected] = React.useState([]);

  React.useEffect(() => {
    const initialized = (Array.isArray(data) ? data : []).map((r, idx) => ({
      ...r,
      rankValue: r.rankValue || '1',
      id: r.id ?? idx,
    }));
    setRows(initialized);
  }, [data]);

  const handleRankChange = (id, value) => {
    const updated = rows.map((r) => (r.id === id ? { ...r, rankValue: value } : r));
    setRows(updated);
    sendSelection(updated, selected);
  };

  const handleSelect = (id) => {
    const updatedSelected = selected.includes(id)
      ? selected.filter((v) => v !== id)
      : [...selected, id];
    setSelected(updatedSelected);
    sendSelection(rows, updatedSelected);
  };

  const sendSelection = (rowsData, selectedIds) => {
    const selectedRows = rowsData
      .filter((r) => selectedIds.includes(r.id))
      .map((r) => ({
        ...r,
        groupValue: r.rankValue,
      }));
    onSelectionChange?.(selectedRows);
  };

  return (
    <TableContainer component={Paper}>
      <Table aria-label="collapsible table">
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox">
              <Checkbox
                indeterminate={selected.length > 0 && selected.length < rows.length}
                checked={rows.length > 0 && selected.length === rows.length}
                onChange={(e) =>
                  setSelected(e.target.checked ? rows.map((r) => r.id) : [])
                }
              />
            </TableCell>
            <TableCell width={48} />
            <TableCell>Rank</TableCell>
            <TableCell>Location</TableCell>
            <TableCell>Genes</TableCell>
            <TableCell>RS ID</TableCell>
            <TableCell>Match</TableCell>
            <TableCell>Amino acid change</TableCell>
            <TableCell>Avalibility</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <Row
              key={row.id}
              row={row}
              onRankChange={handleRankChange}
              isSelected={selected.includes(row.id)}
              onSelect={handleSelect}
            />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
