import React, { useEffect, useRef } from 'react';

export const WaveBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener('resize', handleResize);

    let step = 0;

    const render = () => {
      step += 0.008;
      ctx.clearRect(0, 0, width, height);

      // Deep dark background gradient
      const bgGrad = ctx.createLinearGradient(0, 0, 0, height);
      bgGrad.addColorStop(0, '#040508');
      bgGrad.addColorStop(0.5, '#0a0d14');
      bgGrad.addColorStop(1, '#020305');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Draw undulating sine wave lines
      const numLines = 14;
      for (let i = 0; i < numLines; i++) {
        ctx.beginPath();
        const baseHeight = height * 0.4 + i * 25;
        const opacity = 0.08 + (i / numLines) * 0.18;

        ctx.strokeStyle = i % 2 === 0
          ? `rgba(99, 102, 241, ${opacity})`
          : `rgba(225, 29, 72, ${opacity * 0.8})`;
        ctx.lineWidth = 1.5;

        for (let x = 0; x < width; x += 10) {
          const y =
            baseHeight +
            Math.sin(x * 0.004 + step + i * 0.3) * 45 +
            Math.cos(x * 0.002 - step * 0.5) * 25;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ opacity: 0.85 }}
    />
  );
};
