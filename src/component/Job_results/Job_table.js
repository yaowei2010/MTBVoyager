import PropTypes from 'prop-types';
import { alpha } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import TableSortLabel from '@mui/material/TableSortLabel';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Checkbox from '@mui/material/Checkbox';
import Tooltip from '@mui/material/Tooltip';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import DeleteIcon from '@mui/icons-material/Delete';
import { visuallyHidden } from '@mui/utils';
import axios from 'axios';
import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { config } from '../../constant.js';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import TextField from '@mui/material/TextField';
import ErrorDialog from '../ErrorDialog.js';

// 用來排序時比對的函式
function descendingComparator(a, b, orderBy) {
  if (b[orderBy] < a[orderBy]) return -1;
  if (b[orderBy] > a[orderBy]) return 1;
  return 0;
}
function getComparator(order, orderBy) {
  return order === 'desc'
    ? (a, b) => descendingComparator(a, b, orderBy)
    : (a, b) => -descendingComparator(a, b, orderBy);
}
function stableSort(array, comparator) {
  const stabilizedThis = array.map((el, index) => [el, index]);
  stabilizedThis.sort((a, b) => {
    const order = comparator(a[0], b[0]);
    if (order !== 0) return order;
    return a[1] - b[1];
  });
  return stabilizedThis.map((el) => el[0]);
}

// headCells：Genome build 在 Status 前面
const headCells = [
  { id: 'analysis_ID', numeric: false, disablePadding: true, label: 'Analysis ID', width: '150px' },
  { id: 'subject', numeric: true, disablePadding: false, label: 'Name', width: '120px' },
  { id: 'protocol', numeric: true, disablePadding: false, label: 'Protocol', width: '120px' },
  { id: 'phenotypes', numeric: true, disablePadding: false, label: 'Date of Birth', width: '150px' },
  { id: 'genome_build', numeric: true, disablePadding: false, label: 'Genome build', width: '120px' },
  { id: 'status', numeric: true, disablePadding: false, label: 'Status', width: '100px' },
  { id: 'action', numeric: false, disablePadding: false, label: 'Action', width: '110px', align: 'center', disableSorting: true },
];

function EnhancedTableHead(props) {
  const { onSelectAllClick, order, orderBy, numSelected, rowCount, onRequestSort } = props;
  const createSortHandler = (property) => (event) => {
    onRequestSort(event, property);
  };

  return (
    <TableHead>
      <TableRow>
        <TableCell padding="checkbox" sx={{ width: '50px' }}>
          <Checkbox
            color="primary"
            indeterminate={numSelected > 0 && numSelected < rowCount}
            checked={rowCount > 0 && numSelected === rowCount}
            onChange={onSelectAllClick}
          />
        </TableCell>

        {headCells.map((headCell) => {
          const disableSorting = headCell.disableSorting || false;
          const cellAlign = headCell.align
            ? headCell.align
            : headCell.numeric
            ? 'right'
            : 'left';

          return (
            <TableCell
              key={headCell.id}
              align={cellAlign}
              padding={headCell.disablePadding ? 'none' : 'normal'}
              sortDirection={!disableSorting && orderBy === headCell.id ? order : false}
              sx={{ width: headCell.width }}
            >
              {disableSorting ? (
                headCell.label
              ) : (
                <TableSortLabel
                  active={orderBy === headCell.id}
                  direction={orderBy === headCell.id ? order : 'asc'}
                  onClick={createSortHandler(headCell.id)}
                >
                  {headCell.label}
                  {orderBy === headCell.id ? (
                    <Box component="span" sx={visuallyHidden}>
                      {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
                    </Box>
                  ) : null}
                </TableSortLabel>
              )}
            </TableCell>
          );
        })}
      </TableRow>
    </TableHead>
  );
}

EnhancedTableHead.propTypes = {
  numSelected: PropTypes.number.isRequired,
  onRequestSort: PropTypes.func.isRequired,
  onSelectAllClick: PropTypes.func.isRequired,
  order: PropTypes.oneOf(['asc', 'desc']).isRequired,
  orderBy: PropTypes.string.isRequired,
  rowCount: PropTypes.number.isRequired,
};

// Toolbar 搜尋
function EnhancedTableToolbar(props) {
  const { numSelected, onDelete, searchQuery, setSearchQuery } = props;

  return (
    <Toolbar
      sx={{
        pl: { sm: 2 },
        pr: { xs: 1, sm: 1 },
        ...(numSelected > 0 && {
          bgcolor: (theme) =>
            alpha(theme.palette.primary.main, theme.palette.action.activatedOpacity),
        }),
      }}
    >
      {numSelected > 0 ? (
        <Typography sx={{ flex: '1 1 100%' }} color="inherit" variant="subtitle1" component="div">
          {numSelected} selected
        </Typography>
      ) : (
        <Typography sx={{ flex: '1 1 100%' }} variant="h6" id="tableTitle" component="div" />
      )}

      {numSelected > 0 ? (
        <Tooltip title="Delete">
          <IconButton onClick={onDelete}>
            <DeleteIcon />
          </IconButton>
        </Tooltip>
      ) : (
        <TextField
          label="Search"
          variant="outlined"
          size="small"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ width: 200 }}
        />
      )}
    </Toolbar>
  );
}

EnhancedTableToolbar.propTypes = {
  numSelected: PropTypes.number.isRequired,
  onDelete: PropTypes.func.isRequired,
  searchQuery: PropTypes.string,
  setSearchQuery: PropTypes.func,
};

export default function Job_table(props) {
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const { rows, refreshRows } = props;

  const [order, setOrder] = useState('asc');
  const [orderBy, setOrderBy] = useState('calories');
  const [selected, setSelected] = useState([]);
  const [page, setPage] = useState(0);
  const [dense, setDense] = useState(false);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [searchQuery, setSearchQuery] = useState('');

  const navigate = useNavigate();

  const handleRequestSort = (event, property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleSelectAllClick = () => {
    setSelected([]);
  };

  const handleClick = (event, id) => {
    if (selected.includes(id)) setSelected([]);
    else setSelected([id]);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleChangeDense = (event) => {
    setDense(event.target.checked);
  };

  const handleDelete = async () => {
    if (selected.length === 0) return;
    try {
      const row = rows.find((item) => item.ID === selected[0]);
      if (!row) return;
      await axios.post(`${config.rootApiIP}/delete_job`, {
        newjobid: row.analysis_ID,
      });
    } catch (error) {
      console.error('刪除出錯:', error);
    } finally {
      setSelected([]);
      window.location.reload();
    }
  };

  // ✅ 統一用 protocol + genome_build 分流（包含 germline_hg38）
  const handleRowClick = async (row) => {
    if (row.status === 'running') {
      setErrorMessage('Analysis still running!');
      setErrorDialogOpen(true);
      return;
    }

    const proto = String(row.protocol || '').trim().toLowerCase();
    const build = String(row.genome_build || '').trim().toLowerCase();

    let detailPath = `/Job_results/detail_germline/${row.analysis_ID}`; // default germline hg19

    if (proto === 'somatic') {
      detailPath = `/Job_results/detail_somatic/${row.analysis_ID}`;
    } else if (proto === 'germline trio') {
      detailPath = `/Job_results/detail_germline_trio/${row.analysis_ID}`;
    } else {
      // Germline
      if (build === 'hg38') {
        detailPath = `/Job_results/detail_germline_hg38/${row.analysis_ID}`;
      } else {
        detailPath = `/Job_results/detail_germline/${row.analysis_ID}`;
      }
    }

    try {
      await axios.post(`${config.rootApiIP}/get_newjobid`, {
        newjobid: row.analysis_ID,
      });
    } catch (error) {
      console.error('查詢出錯:', error);
    } finally {
      window.location.href = config.rootPathPrefix + detailPath;
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
  };

  const isSelected = (id) => selected.indexOf(id) !== -1;
  const emptyRows = page > 0 ? Math.max(0, (1 + page) * rowsPerPage - rows.length) : 0;

  const filteredRows = useMemo(() => {
    if (!searchQuery) return rows;
    const lowerQuery = searchQuery.toLowerCase();
    return rows.filter((row) =>
      Object.values(row).some((value) =>
        String(value).toLowerCase().includes(lowerQuery)
      )
    );
  }, [rows, searchQuery]);

  const visibleRows = useMemo(() => {
    const sorted = stableSort(filteredRows, getComparator(order, orderBy));
    return sorted.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);
  }, [filteredRows, order, orderBy, page, rowsPerPage]);

  return (
    <Box sx={{ width: '100%', marginRight: '20px', marginBottom: '50px' }}>
      <Paper sx={{ width: '100%', mb: 2 }}>
        <EnhancedTableToolbar
          numSelected={selected.length}
          onDelete={handleDelete}
          refreshRows={refreshRows}
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
        />

        <TableContainer sx={{ border: '1px solid #ccc', borderRadius: '8px' }}>
          <Table sx={{ minWidth: 750 }} aria-labelledby="tableTitle" size={dense ? 'small' : 'medium'}>
            <EnhancedTableHead
              numSelected={selected.length}
              order={order}
              orderBy={orderBy}
              onSelectAllClick={handleSelectAllClick}
              onRequestSort={handleRequestSort}
              rowCount={rows.length}
            />

            <TableBody>
              {visibleRows.map((row, index) => {
                const isItemSelected = isSelected(row.ID);
                const labelId = `enhanced-table-checkbox-${index}`;

                return (
                  <TableRow
                    hover
                    onClick={(event) => handleClick(event, row.ID)}
                    role="checkbox"
                    aria-checked={isItemSelected}
                    tabIndex={-1}
                    key={row.ID}
                    selected={isItemSelected}
                    sx={{ cursor: 'pointer' }}
                  >
                    <TableCell padding="checkbox" sx={{ width: '50px' }}>
                      <Checkbox color="primary" checked={isItemSelected} inputProps={{ 'aria-labelledby': labelId }} />
                    </TableCell>

                    <TableCell component="th" id={labelId} scope="row" padding="none" sx={{ width: '150px' }}>
                      {row.analysis_ID}
                    </TableCell>

                    <TableCell align="right" sx={{ width: '120px' }}>
                      {row.subject}
                    </TableCell>

                    <TableCell align="right" sx={{ width: '120px' }}>
                      {row.protocol}
                    </TableCell>

                    <TableCell align="right" sx={{ width: '150px' }}>
                      {row.phenotypes}
                    </TableCell>

                    {/* Genome build */}
                    <TableCell align="right" sx={{ width: '120px' }}>
                      {row.genome_build}
                    </TableCell>

                    {/* Status */}
                    <TableCell align="right" sx={{ width: '100px' }}>
                      {row.status}
                    </TableCell>

                    <TableCell align="center" sx={{ width: '110px' }}>
                      <Button
                        variant="contained"
                        sx={{ minWidth: '80px' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRowClick(row); // ✅ 全部統一走這個分流
                        }}
                      >
                        Detail
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}

              {emptyRows > 0 && (
                <TableRow style={{ height: (dense ? 33 : 53) * emptyRows }}>
                  <TableCell colSpan={8} />
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={filteredRows.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>

      <FormControlLabel control={<Switch checked={dense} onChange={handleChangeDense} />} label="Dense padding" />

      <ErrorDialog open={errorDialogOpen} onClose={() => setErrorDialogOpen(false)} errorMessage={errorMessage} />
    </Box>
  );
}
