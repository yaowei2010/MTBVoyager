import React from 'react';

const SV_CNV = ({ htmlContent }) => {

  console.log(htmlContent)
  return (
    <div>
      <iframe
        title="HTML Content"
        srcDoc={htmlContent}
        style={{ width: '100%', height: '120vh', border: 'none' }}
      />
    </div>
  );
};

export default SV_CNV;
