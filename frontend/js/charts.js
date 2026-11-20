export function drawRadialGauge(canvas, value, maxValue = 100, label = "Security Score", color = "#24C8F5") {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 180;
  const height = canvas.clientHeight || 180;
  
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(centerX, centerY) - 18;
  const startAngle = 0.75 * Math.PI;
  const endAngle = 2.25 * Math.PI;
  const currentAngle = startAngle + (value / maxValue) * (endAngle - startAngle);
  
  ctx.clearRect(0, 0, width, height);
  
  // Background track
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, startAngle, endAngle);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
  ctx.lineWidth = 8;
  ctx.lineCap = "round";
  ctx.stroke();
  
  // Active Cyber arc with subtle glow
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, startAngle, currentAngle);
  ctx.strokeStyle = color;
  ctx.lineWidth = 8;
  ctx.lineCap = "round";
  ctx.shadowColor = "rgba(36, 200, 245, 0.4)";
  ctx.shadowBlur = 16;
  ctx.stroke();
  ctx.shadowBlur = 0;
  
  // Center Value
  ctx.fillStyle = "#FFFFFF";
  ctx.font = "700 32px 'IBM Plex Mono', 'Inter', monospace";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(`${Math.round(value)}`, centerX, centerY - 6);
  
  // Label with heavy letter spacing
  ctx.fillStyle = "#24C8F5";
  ctx.font = "700 8.5px 'Inter', sans-serif";
  ctx.fillText(label.toUpperCase(), centerX, centerY + 24);
}

export function drawLineTrendChart(canvas, labels, discovered, resolved) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 500;
  const height = canvas.clientHeight || 220;
  
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  
  ctx.clearRect(0, 0, width, height);
  
  const padLeft = 40;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 35;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;
  
  const maxVal = Math.max(10, ...discovered, ...resolved);
  
  // Grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = padTop + (chartH / 4) * i;
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(width - padRight, y);
    ctx.stroke();
    
    ctx.fillStyle = "#8a8885";
    ctx.font = "10px monospace";
    ctx.textAlign = "right";
    ctx.fillText(`${Math.round(maxVal - (maxVal / 4) * i)}`, padLeft - 8, y + 3);
  }
  
  const stepX = chartW / (labels.length - 1 || 1);
  
  function drawSeries(data, strokeColor, fillColor) {
    const points = data.map((val, idx) => ({
      x: padLeft + idx * stepX,
      y: padTop + chartH - (val / maxVal) * chartH
    }));
    
    // Fill area
    ctx.beginPath();
    ctx.moveTo(points[0].x, padTop + chartH);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, padTop + chartH);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();
    
    // Stroke line
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2.5;
    ctx.shadowColor = strokeColor;
    ctx.shadowBlur = 10;
    ctx.stroke();
    ctx.shadowBlur = 0;
    
    // Nodes
    points.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, 2 * Math.PI);
      ctx.fillStyle = strokeColor;
      ctx.fill();
      ctx.strokeStyle = "#0a0a0a";
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }
  
  drawSeries(discovered, "#FF5578", "rgba(255, 85, 120, 0.08)");
  drawSeries(resolved, "#20D6A0", "rgba(32, 214, 160, 0.10)");
  
  // X axis labels
  ctx.fillStyle = "#8a8885";
  ctx.font = "10px 'Inter', sans-serif";
  ctx.textAlign = "center";
  labels.forEach((lbl, idx) => {
    ctx.fillText(lbl, padLeft + idx * stepX, height - 10);
  });
}
