import * as React from 'react';
import { useEffect, useState } from 'react';
import Papa from 'papaparse';
import { styled } from '@mui/material/styles';
import { useAutocomplete } from '@mui/base/useAutocomplete';
import { autocompleteClasses } from '@mui/material/Autocomplete';
import CheckIcon from '@mui/icons-material/Check';

const Root = styled('div')(({ theme }) => `
  position: relative;
  color: ${
    theme.palette.mode === 'dark'
      ? 'rgba(255,255,255,0.85)'
      : 'rgba(0,0,0,.85)'
  };
  font-size: 18px;
`);

const InputWrapper = styled('div')(({ theme }) => `
  width: 100%;
  border: 2px solid #ccc;
  background-color: ${theme.palette.mode === 'dark' ? '#141414' : '#fff'};
  border-radius: 6px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  min-height: 56px;

  &:hover {
    border-color: ${theme.palette.mode === 'dark' ? '#177ddc' : '#40a9ff'};
  }

  &.focused {
    border-color: ${theme.palette.mode === 'dark' ? '#177ddc' : '#40a9ff'};
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }

  & input {
    background-color: inherit;
    color: inherit;
    height: 36px;
    box-sizing: border-box;
    padding: 6px 4px;
    width: 100%;
    border: 0;
    margin: 0;
    outline: 0;
    font-size: 20px;
  }
`);

const Listbox = styled('ul')(({ theme }) => `
  width: 100%;
  margin: 4px 0 0;
  padding: 0;
  position: absolute;
  list-style: none;
  background-color: ${theme.palette.mode === 'dark' ? '#141414' : '#fff'};
  overflow: auto;
  max-height: 280px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  z-index: 9999;

  & li {
    padding: 8px 12px;
    display: flex;
    align-items: center;
  }

  & li span {
    flex-grow: 1;
    font-size: 18px;
  }

  & li svg {
    color: transparent;
  }

  & li[aria-selected='true'] {
    background-color: ${
      theme.palette.mode === 'dark' ? '#2b2b2b' : '#fafafa'
    };
    font-weight: 600;
  }

  & li[aria-selected='true'] svg {
    color: #1890ff;
  }

  & li.${autocompleteClasses.focused} {
    background-color: ${
      theme.palette.mode === 'dark' ? '#003b57' : '#e6f7ff'
    };
    cursor: pointer;
  }

  & li.${autocompleteClasses.focused} svg {
    color: currentColor;
  }
`);

export default function Diagnosis_AutoComplete({ diagnosis, setDiagnosis }) {
  const [options, setOptions] = useState([]);
  const [selectedValue, setSelectedValue] = useState(null);

  useEffect(() => {
    const fileUrl = `${process.env.PUBLIC_URL}/Mondo_combined.tsv`;

    console.log('Start loading:', fileUrl);

    fetch(fileUrl)
      .then((r) => {
        console.log('fetch status:', r.status);
        console.log('fetch url:', r.url);

        if (!r.ok) {
          throw new Error(
            `Failed to load Mondo_combined.tsv, status: ${r.status}`
          );
        }

        return r.text();
      })
      .then((text) => {
        console.log('TSV first 200 chars:', text.slice(0, 200));

        if (text.trim().startsWith('<!DOCTYPE html>')) {
          console.error(
            'You loaded index.html, not Mondo_combined.tsv. Please check file path.'
          );
          setOptions([]);
          return;
        }

        Papa.parse(text, {
          header: true,
          delimiter: '\t',
          skipEmptyLines: true,
          complete: (res) => {
            console.log('Parsed first 5 rows:', res.data.slice(0, 5));

            const labels = res.data
              .filter((row) => row?.label)
              .map((row) => ({
                label: String(row.label).trim(),
              }))
              .filter((row) => row.label !== '');

            console.log('labels count:', labels.length);
            console.log('labels first 10:', labels.slice(0, 10));

            setOptions(labels);
          },
          error: (err) => {
            console.error('Papa parse error:', err);
          },
        });
      })
      .catch((err) => {
        console.error('Diagnosis autocomplete load error:', err);
      });
  }, []);

  const {
    getRootProps,
    getInputProps,
    getListboxProps,
    getOptionProps,
    groupedOptions,
    focused,
    setAnchorEl,
  } = useAutocomplete({
    id: 'diagnosis-autocomplete',
    options,
    freeSolo: true,
    multiple: false,

    value: selectedValue,
    inputValue: diagnosis || '',

    getOptionLabel: (option) => {
      if (typeof option === 'string') return option;
      return option?.label || '';
    },

    isOptionEqualToValue: (option, value) => {
      return option?.label === value?.label;
    },

    onInputChange: (_event, newInputValue) => {
      console.log('typing:', newInputValue);

      setDiagnosis(newInputValue || '');
      setSelectedValue(null);
    },

    onChange: (_event, newValue) => {
      console.log('selected:', newValue);

      if (typeof newValue === 'string') {
        setDiagnosis(newValue);
        setSelectedValue(null);
      } else if (newValue?.label) {
        setDiagnosis(newValue.label);
        setSelectedValue(newValue);
      } else {
        setDiagnosis('');
        setSelectedValue(null);
      }
    },

    filterOptions: (opts, state) => {
      const q = (state.inputValue || '').trim().toLowerCase();

      if (q.length < 2) return [];

      return opts
        .filter((o) => o.label.toLowerCase().includes(q))
        .slice(0, 50);
    },
  });

  return (
    <Root>
      <div {...getRootProps()}>
        <InputWrapper
          ref={setAnchorEl}
          className={focused ? 'focused' : ''}
        >
          <input
            {...getInputProps()}
            placeholder="Type or select a disease (e.g., Colon adenocarcinoma)"
          />
        </InputWrapper>
      </div>

      {groupedOptions.length > 0 && (
        <Listbox {...getListboxProps()}>
          {groupedOptions.map((option, index) => {
            const optionProps = getOptionProps({ option, index });

            return (
              <li key={`${option.label}-${index}`} {...optionProps}>
                <span>{option.label}</span>
                <CheckIcon fontSize="small" />
              </li>
            );
          })}
        </Listbox>
      )}
    </Root>
  );
}