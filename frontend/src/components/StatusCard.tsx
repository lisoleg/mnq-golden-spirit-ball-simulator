import { Card, CardContent, Typography } from '@mui/material';

interface StatusCardProps {
  title: string;
  value: string | number;
  unit?: string;
  color?: string;
}

export default function StatusCard({ title, value, unit, color = '#1890ff' }: StatusCardProps) {
  return (
    <Card sx={{ minWidth: 160, backgroundColor: '#0f3460' }}>
      <CardContent sx={{ textAlign: 'center', py: 2 }}>
        <Typography variant="body2" sx={{ color: '#888', mb: 1 }}>
          {title}
        </Typography>
        <Typography
          variant="h4"
          sx={{
            color,
            fontWeight: 'bold',
            fontFamily: '"Roboto Mono", monospace',
          }}
        >
          {value}
        </Typography>
        {unit && (
          <Typography variant="caption" sx={{ color: '#666', mt: 0.5 }}>
            {unit}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}
