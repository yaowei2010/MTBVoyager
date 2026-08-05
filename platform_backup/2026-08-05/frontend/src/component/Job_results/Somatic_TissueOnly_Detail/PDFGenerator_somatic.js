import React, { useState } from 'react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Button, Stack } from '@mui/material';

const PDFGenerator = ({ groupedData, jsonData }) => {
  const [pdfUrl, setPdfUrl] = useState(null);

  const generatePDF = () => {
    const doc = new jsPDF();
    let yOffset = 10; // 初始 y offset

    // 判斷是否需換頁
    const checkPageOverflow = (offset) => {
      if (offset >= doc.internal.pageSize.height - 20) { // 20 為邊界留白
        doc.addPage();
        return 10; // 新頁重設 offset
      }
      return offset;
    };

    // 報告標題
    doc.setFontSize(40);
    doc.text('Report', 105, 20, null, null, 'center');
    yOffset = 35;
    doc.setFontSize(12);

    // 加入 jsonData 內容
    if (jsonData) {
      doc.setFontSize(10);
      yOffset = checkPageOverflow(yOffset);
      doc.text('===========================================================================================', 10, yOffset);
      yOffset += 8;

      doc.setFontSize(16);
      doc.setFont("helvetica", "bold");
      doc.text(`Diagnosis : `, 10, yOffset);
      doc.setFont("helvetica", "normal");
      doc.text(`${jsonData.diagnosis}`, 50, yOffset);
      yOffset += 10;

      yOffset = checkPageOverflow(yOffset);
      doc.setFont("helvetica", "bold");
      doc.text(`Subject ID : `, 10, yOffset);
      doc.setFont("helvetica", "normal");
      doc.text(`${jsonData.subject_id}`, 50, yOffset);
      yOffset += 8;

      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      yOffset = checkPageOverflow(yOffset);
      doc.text('===========================================================================================', 10, yOffset);
      yOffset += 13;
    }

    // 依據不同 table 產生對應的表格內容
    Object.keys(groupedData).forEach((tableName) => {
      // 顯示 table 標題（使用藍色字體）
      doc.setFontSize(17);
      yOffset = checkPageOverflow(yOffset);
      let displayTableName = tableName;
      if (tableName === 'single_snp_actionable') {
        displayTableName = 'Single SNP - Actionable';
      } else if (tableName === 'single_snp_cosmic') {
        displayTableName = 'Single SNP - Cosmic';
      } else if (tableName === 'single_snp_hereidty') {
        displayTableName = 'Single SNP - Hereidty';
      } else if (tableName === 'single_snp_prediction') {
        displayTableName = 'Single SNP - Prediction';
      } else if (tableName === 'single_snp_germline_prediction') {
        displayTableName = 'Single SNP - Germline Prediction';
      } else if (tableName === 'muti_snp_cosmic') {
        displayTableName = 'Multiple SNP - Cosmic';
      } else if (tableName === 'muti_snp_civic') {
        displayTableName = 'Multiple SNP - Civic';
      }
      doc.setTextColor(0, 0, 255); // 設定藍色
      doc.text(`Table: ${displayTableName}`, 13, yOffset);
      doc.setTextColor(0, 0, 0); // 恢復黑色
      yOffset += 15;

      // 依據每個 table 中的 gene 分組產生各自的表格
      Object.keys(groupedData[tableName]).forEach((gene) => {
        doc.setFontSize(17);
        yOffset = checkPageOverflow(yOffset);
        doc.text(`• ${gene}`, 13, yOffset);
        yOffset += 5;

        // 根據不同 table 定義欄位
        let headColumns = [];
        let bodyColumnsFunc = null;

        if (tableName === 'single_snp_actionable') {
          headColumns = ['Location', 'Gene', 'RS ID', 'MAF', 'Domain', 'Pathogenicity', 'Prediction', 'Match', 'Amino Acid Change', 'Avalibility'];
          bodyColumnsFunc = (row) => [
            row.Location,
            row.Gene,
            row.RSID,
            row.MAF,
            row.Domain,
            row.Pathogenicity,
            row.Prediction,
            row.Match,
            row.AminoAcidChange,
            Array.isArray(row.Avalibility) ? row.Avalibility.join(', ') : row.Avalibility,
          ];
        } else if (
          tableName === 'single_snp_cosmic' ||
          tableName === 'single_snp_hereidty' ||
          tableName === 'single_snp_prediction' ||
          tableName === 'single_snp_germline_prediction'
        ) {
          headColumns = ['Location', 'Gene', 'RS ID', 'MAF', 'Domain', 'Prediction', 'Pathogenicity'];
          bodyColumnsFunc = (row) => [
            row.Location,
            row.Gene,
            row.RSID,
            row.MAF,
            row.Domain,
            row.Prediction,
            row.Pathogenicity,
            row.AminoAcidChange,
          ];
        } else if (tableName === 'muti_snp_cosmic') {
          headColumns = ['Location', 'Detailed Location', 'Gene', 'RS ID', 'MAF', 'Domain', 'Prediction', 'Pathogenicity', 'Drug Combination', 'Phenotype', 'Cosmic Preprocessor'];
          bodyColumnsFunc = (row) => [
            row.Location,
            row.DetailedLocation,
            row.Gene,
            row.RSID,
            row.MAF,
            row.Domain,
            row.Prediction,
            row.Pathogenicity,
            row.DRUGCOMBINATION,
            row.Phenotype,
            row.CosmicPreprocessor,
          ];
        } else if (tableName === 'muti_snp_civic') {
          headColumns = ['Location', 'Detailed Location', 'Gene', 'RS ID', 'MAF', 'Domain', 'Prediction', 'Pathogenicity', 'Phenotype', 'Therapies', 'Civic Variant'];
          bodyColumnsFunc = (row) => [
            row.Location,
            row.DetailedLocation,
            row.Gene,
            row.RSID,
            row.MAF,
            row.Domain,
            row.Prediction,
            row.Pathogenicity,
            row.Phenotype,
            row.Therapies,
            row.CivicVariantName,
          ];
        } else {
          headColumns = ['Location', 'Gene', 'RS ID', 'MAF', 'Domain', 'Prediction', 'Pathogenicity'];
          bodyColumnsFunc = (row) => [
            row.Location,
            row.Gene,
            row.RSID,
            row.MAF,
            row.Domain,
            row.Prediction,
            row.Pathogenicity,
          ];
        }

        // 準備此 gene 群組的表格資料
        const tableData = groupedData[tableName][gene].map(row => bodyColumnsFunc(row));

        autoTable(doc, {
          startY: yOffset,
          head: [headColumns],
          body: tableData,
          theme: 'striped',
          styles: {
            fontSize: 5,
          },
        });

        yOffset = doc.lastAutoTable.finalY + 15;
      });

      // 在每個 table 之間加入分隔線
      yOffset = checkPageOverflow(yOffset);
      doc.setFontSize(12);
      doc.text('==========================================', 13, yOffset);
      yOffset += 15;
    });

    doc.setFontSize(10);
    // yOffset += 10;
    // doc.text('===========================================================================================', 10, yOffset);
    // yOffset += 20;

    if (jsonData) {
      doc.setFontSize(12);
      yOffset = checkPageOverflow(yOffset);
      doc.text(`• MAF Cutoff : ${jsonData.maf_cutoff}`, 10, yOffset);
      yOffset += 10;
      yOffset = checkPageOverflow(yOffset);
      doc.text(`• Min AAF : ${jsonData.min_aaf}`, 10, yOffset);
      yOffset += 10;
      yOffset = checkPageOverflow(yOffset);
      doc.text(`• Min DP Cutoff : ${jsonData.min_dp_cutoff}`, 10, yOffset);
      yOffset += 10;
      yOffset = checkPageOverflow(yOffset);
      doc.text(`• Gene Panel : ${jsonData.gene_panel_list.GenePanelList[0].genePanel.split('\n').length} genes`, 10, yOffset);
      yOffset += 10;

      const genePanelList = jsonData.gene_panel_list.GenePanelList[0].genePanel.replace(/\n/g, ', ');
      const splitGenePanelList = genePanelList.split(', ').reduce((acc, curr, idx) => {
        return idx % 10 === 0 && idx !== 0 ? acc + '\n' + curr : acc + ', ' + curr;
      });

      const genePanelLines = splitGenePanelList.split('\n');
      genePanelLines.forEach(line => {
        yOffset = checkPageOverflow(yOffset);
        doc.text(line, 10, yOffset);
        yOffset += 10;
      });

      yOffset += 10;
    }

    doc.save('report.pdf');
    const pdfBlob = doc.output('blob');
    const pdfBlobUrl = URL.createObjectURL(pdfBlob);
    setPdfUrl(pdfBlobUrl);
  };

  return (
    <div>
      <Button
        variant="contained"
        sx={{ width: '200px', height: '70px', fontSize: '20px' }}
        onClick={generatePDF}
      >
        Save to report
      </Button>
    </div>
  );
};

export default PDFGenerator;
