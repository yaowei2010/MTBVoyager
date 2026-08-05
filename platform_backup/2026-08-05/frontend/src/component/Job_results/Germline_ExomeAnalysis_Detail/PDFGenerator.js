// PDFGenerator.js
import React, { useState } from 'react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { Button } from '@mui/material';

const PDFGenerator = ({ combinedData = [], jsonData }) => {
  const [pdfUrl, setPdfUrl] = useState(null);

  const tableOrder = [
    'Known Pathogenic Pheno',
    'Known Pathogenic ACMG',
    'Known Pathogenic Other',
    'Predicted Suspect Pheno',
    'Predicted Suspect ACMG',
    'Predicted Suspect Other',
    'Other Variants',
    'Drug Responses'
  ];

  const otherHeaders = [
    'Location',
    'Gene',
    'RS ID',
    'MAF',
    'Genotype VAF',
    'Evidence',
    'Domain',
    'Pathogenicity',
    'Splicing Effect',
    'OMIM',
    'Amelie Max Score',
    'Amelie Mean Score'
  ];

  const drugHeaders = [
    'Location',
    'Gene',
    'RS ID',
    'Drug Evidence',
    'Chemical',
    'ClinVar'
  ];

const generatePDF = () => {
  const doc = new jsPDF();
  let yOffset = 20;

  const checkPageOverflow = () => {
    if (yOffset > doc.internal.pageSize.height - 30) {
      doc.addPage();
      yOffset = 20;
    }
  };

  const safeText = (v) => {
    if (v === null || v === undefined) return 'N/A';
    return String(v);
  };

  const gp0 = jsonData?.genePanelList?.GenePanelList?.[0];
  const panelName = gp0?.panelName ?? 'N/A';
  const genePanelRaw = gp0?.genePanel ?? '';

  // Header
  doc.setFontSize(24);
  doc.text('Report', doc.internal.pageSize.width / 2, 15, { align: 'center' });
  yOffset = 30;

  // Metadata
  // 只要 jsonData 存在就印；但所有欄位都走 safeText，不會炸
  if (jsonData) {
    checkPageOverflow();
    doc.setFontSize(12);

    doc.setFont('helvetica', 'bold');
    doc.text('Panel Name :', 10, yOffset);
    doc.setFont('helvetica', 'normal');
    doc.text(safeText(panelName), 50, yOffset);

    yOffset += 8; checkPageOverflow();
    doc.setFont('helvetica', 'bold');
    doc.text('Subject ID :', 10, yOffset);
    doc.setFont('helvetica', 'normal');
    doc.text(safeText(jsonData?.subject_id), 50, yOffset);

    yOffset += 8; checkPageOverflow();
    doc.setFont('helvetica', 'bold');
    doc.text('MAF Cutoff :', 10, yOffset);
    doc.setFont('helvetica', 'normal');
    doc.text(safeText(jsonData?.maf_cutoff), 50, yOffset);

    yOffset += 8; checkPageOverflow();
    doc.setFont('helvetica', 'bold');
    doc.text('Min AAF :', 10, yOffset);
    doc.setFont('helvetica', 'normal');
    doc.text(safeText(jsonData?.min_aaf), 50, yOffset);

    yOffset += 8; checkPageOverflow();
    doc.setFont('helvetica', 'bold');
    doc.text('Min DP Cutoff :', 10, yOffset);
    doc.setFont('helvetica', 'normal');
    doc.text(safeText(jsonData?.min_dp_cutoff), 50, yOffset);

    yOffset += 12;
    doc.setDrawColor(0);
    doc.setLineWidth(0.2);
    doc.line(10, yOffset, doc.internal.pageSize.width - 10, yOffset);
    yOffset += 10;
  }

  // Group by Gene → table_name
  const genes = Array.from(
    new Set(combinedData.map(item => item.Gene).filter(Boolean))
  );

  genes.forEach(gene => {
    checkPageOverflow();
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text(safeText(gene), 10, yOffset);
    yOffset += 8;

    tableOrder.forEach(tableName => {
      const rows = combinedData.filter(
        item => item.Gene === gene && item.table_name === tableName
      );
      if (!rows.length) return;

      checkPageOverflow();
      doc.setFontSize(14);
      doc.setFont('helvetica', 'bold');
      doc.text(safeText(tableName), 12, yOffset);
      yOffset += 6;

      const isDrug = tableName === 'Drug Responses';
      const headers = isDrug ? drugHeaders : otherHeaders;

      const body = rows.map(r =>
        isDrug
          ? [
              safeText(r.Location),
              safeText(r.Gene),
              safeText(r.RSID),
              safeText(r.Drugevidence),
              safeText(r.Chemical),
              safeText(r.ClinVar)
            ]
          : [
              safeText(r.Location),
              safeText(r.Gene),
              safeText(r.RSID),
              safeText(r.MAF),
              safeText(r.GenotypeVAF),
              safeText(r.Evidence),
              safeText(r.Domain),
              safeText(r.Pathogenicity),
              safeText(r.SplicingEffect),
              safeText(r.OMIM),
              safeText(r.AmelieMaxScore),
              safeText(r.AmelieMeanScore)
            ]
      );

      autoTable(doc, {
        startY: yOffset,
        head: [headers],
        body,
        theme: 'grid',
        styles: { fontSize: 6, cellPadding: 1 },
        headStyles: {
          fillColor: [25, 118, 210],
          textColor: [255, 255, 255],
          halign: 'center'
        },
        margin: { left: 10, right: 10 },
        willDrawCell: data => {
          if (data.cursor.y > doc.internal.pageSize.height - 20) {
            doc.addPage();
            data.cursor.y = 20;
          }
        }
      });

      yOffset = doc.lastAutoTable.finalY + 12;
    });

    yOffset += 10;
  });

  // Gene Panel（有 gp0 + genePanel 才印）
  if (genePanelRaw) {
    checkPageOverflow();
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text('Gene Panel', 10, yOffset);
    yOffset += 10;

    let raw = String(genePanelRaw)
      .replace(/\s+/g, '')
      .replace(/、/g, ',')
      .trim();

    const lines = doc.splitTextToSize(raw, doc.internal.pageSize.width - 20);

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    lines.forEach(line => {
      checkPageOverflow();
      doc.text(line, 10, yOffset);
      yOffset += 6;
    });
  }

  doc.save('report.pdf');
  const blob = doc.output('blob');
  setPdfUrl(URL.createObjectURL(blob));
};


  return (
    <div>
      <Button
        variant="contained"
        sx={{ width: 200, height: 70, fontSize: 20 }}
        onClick={generatePDF}
      >
        Save to report
      </Button>
    </div>
  );
};

export default PDFGenerator;
