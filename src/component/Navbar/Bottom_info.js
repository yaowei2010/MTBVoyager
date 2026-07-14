import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import Alert from 'react-bootstrap/Alert';

function BottomAlert() {
  const barRef = useRef(null);
  const [barHeight, setBarHeight] = useState(0);

  // 量測 footer 高度
  const measure = () => {
    const h = barRef.current?.offsetHeight || 0;
    setBarHeight(h);
  };

  useLayoutEffect(() => {
    measure();
  }, []);

  useEffect(() => {
    const onResize = () => measure();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const fixedBarStyle = {
    position: 'fixed',
    bottom: 0,          // 不要用 -20，固定貼底
    left: 0,
    width: '100%',
    zIndex: 1200,       // 稍微高一點
  };

  return (
    <>
      {/* spacer：用 footer 的實際高度把內容往上推，避免被覆蓋 */}
      <div style={{ height: barHeight }} />

      {/* 固定在底部的 bar */}
      <div style={fixedBarStyle} ref={barRef}>
        <Alert variant="dark" className="d-flex justify-content-between align-items-center mb-0 py-2 px-3">
          <span className="mx-auto">Copyright@NCKU</span>
          <span>Contant:000000</span>
        </Alert>
      </div>
    </>
  );
}

export default BottomAlert;
