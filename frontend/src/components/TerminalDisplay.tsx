import React, { useEffect, useRef, useState } from 'react';

interface TerminalDisplayProps {
  text: string;
  speed?: number; // 打字速度（毫秒）- 仅在流式更新时使用
  isStreaming?: boolean; // 是否为流式更新模式
  maxLines?: number; // 最大显示行数
}

const TerminalDisplay: React.FC<TerminalDisplayProps> = ({ 
  text, 
  speed = 20,
  isStreaming = true,
  maxLines = 3
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [lines, setLines] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const lastTextLengthRef = useRef(0);

  // 流式模式：实时显示新文本
  useEffect(() => {
    if (isStreaming) {
      // 直接同步显示文本（流式更新不需要打字效果，直接显示）
      if (text !== displayedText) {
        setDisplayedText(text);
        lastTextLengthRef.current = text.length;
      }
    } else {
      // 非流式模式：逐字符打字效果
      if (currentIndex < text.length) {
        const timer = setTimeout(() => {
          setDisplayedText(text.slice(0, currentIndex + 1));
          setCurrentIndex(currentIndex + 1);
        }, speed);

        return () => clearTimeout(timer);
      } else if (text.length === 0) {
        // 文本被重置
        setDisplayedText('');
        setCurrentIndex(0);
        lastTextLengthRef.current = 0;
      }
    }
  }, [text, speed, isStreaming, currentIndex, displayedText]);

  // 将文本分割成行，并只保留最后 maxLines 行
  useEffect(() => {
    const textToProcess = displayedText || text;
    const allLines = textToProcess.split('\n');
    // 只保留最后 maxLines 行
    const visibleLines = allLines.slice(-maxLines);
    setLines(visibleLines);
  }, [displayedText, text, maxLines]);

  // 自动滚动到底部（平滑滚动）
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines]);

  // 判断当前是否正在输出
  const isCurrentlyStreaming = isStreaming && displayedText.length > 0 && text.length > displayedText.length;

  return (
    <div
      ref={containerRef}
      style={{
        background: 'rgba(0, 0, 0, 0.3)',
        color: '#ffffff',
        fontFamily: 'monospace, "Courier New", Courier',
        fontSize: '14px',
        lineHeight: '1.6',
        padding: '12px 16px',
        borderRadius: '4px',
        height: `${maxLines * 1.6 * 14 + 24}px`, // 根据行数计算高度
        overflowY: 'auto',
        overflowX: 'hidden',
        position: 'relative',
        scrollBehavior: 'smooth',
      }}
    >
      <div style={{ position: 'relative', zIndex: 2 }}>
        {lines.map((line, index) => {
          const isLastLine = index === lines.length - 1;
          const isStreamingLine = isCurrentlyStreaming && isLastLine;
          
          return (
            <div
              key={index}
              style={{
                marginBottom: index < lines.length - 1 ? '4px' : 0,
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                color: '#ffffff',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {line}
              {isStreamingLine && (
                <span style={{
                  animation: 'blink 1s infinite',
                  color: '#ffffff',
                  marginLeft: '2px',
                }}>█</span>
              )}
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};

export default TerminalDisplay;

