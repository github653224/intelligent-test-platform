import React, { useEffect, useRef } from 'react';

interface MatrixRainProps {
  enabled: boolean;
}

const MatrixRain: React.FC<MatrixRainProps> = ({ enabled }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!enabled || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置画布大小
    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // 字符集 - 使用数字、字母和一些符号
    const chars = '01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン';
    const charArray = chars.split('');
    const fontSize = 14;
    const columns = Math.floor(canvas.width / fontSize);
    const drops: number[] = [];

    // 初始化drops数组
    for (let i = 0; i < columns; i++) {
      drops[i] = Math.random() * -100;
    }

    let animationId: number;

    const draw = () => {
      if (!ctx) return;
      
      // 半透明黑色背景，创造拖尾效果
      ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // 设置文字样式 - 使用正常颜色（白色/灰色）
      ctx.fillStyle = '#ffffff'; // 白色
      ctx.font = `${fontSize}px monospace`;

      // 绘制每个字符列
      for (let i = 0; i < drops.length; i++) {
        const text = charArray[Math.floor(Math.random() * charArray.length)];
        const x = i * fontSize;
        const y = drops[i] * fontSize;

        // 绘制字符
        ctx.fillText(text, x, y);

        // 如果到了底部或随机重置
        if (y > canvas.height && Math.random() > 0.975) {
          drops[i] = 0;
        }

        // 增加Y坐标
        drops[i]++;
      }
    };

    const animate = () => {
      draw();
      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [enabled]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1,
        opacity: 0.3,
      }}
    />
  );
};

export default MatrixRain;

