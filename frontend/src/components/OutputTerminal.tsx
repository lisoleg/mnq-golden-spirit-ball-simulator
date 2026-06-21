import { useRef, useEffect } from 'react';
import { Box, Typography } from '@mui/material';

interface OutputTerminalProps {
  lines: string[];
  maxLines?: number;
}

export default function OutputTerminal({ lines, maxLines = 500 }: OutputTerminalProps) {
  const containerRef = useRef<HTMLPreElement>(null);
  const displayLines = lines.slice(-maxLines);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [displayLines.length]);

  return (
    <Box
      sx={{
        backgroundColor: '#0a0a0a',
        borderRadius: 8,
        p: 2,
        height: 400,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Typography variant="body2" sx={{ color: '#888', mb: 1 }}>
        输出终端
      </Typography>
      <pre
        ref={containerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          margin: 0,
          padding: 0,
          fontFamily: '"Roboto Mono", "Consolas", monospace',
          fontSize: 13,
          lineHeight: 1.6,
          color: '#00ff88',
          backgroundColor: 'transparent',
        }}
      >
        {displayLines.map((line, i) => (
          <span key={i}>
            {line}
            {'\n'}
          </span>
        ))}
        {displayLines.length === 0 && (
          <span style={{ color: '#555' }}>等待输出...</span>
        )}
      </pre>
    </Box>
  );
}
