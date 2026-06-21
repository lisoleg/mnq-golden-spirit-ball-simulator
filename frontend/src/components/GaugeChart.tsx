import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';

interface GaugeChartProps {
  value: number;
  min?: number;
  max?: number;
  label?: string;
  color?: string;
}

export default function GaugeChart({ value, min = 0, max = 1, label, color = '#1890ff' }: GaugeChartProps) {
  const normalizedValue = ((value - min) / (max - min)) * 100;
  const data = [{ name: label || '值', value: normalizedValue, fill: color }];

  return (
    <div style={{ width: 200, height: 120 }}>
      <RadialBarChart
        cx={100}
        cy={100}
        innerRadius={60}
        outerRadius={90}
        startAngle={180}
        endAngle={0}
        barSize={20}
        data={data}
      >
        <PolarAngleAxis
          type="number"
          domain={[0, 100]}
          angleAxisId={0}
          tick={false}
        />
        <RadialBar
          dataKey="value"
          cornerRadius={10}
          background={{ fill: '#1a1a2e' }}
        />
      </RadialBarChart>
      <div style={{ textAlign: 'center', marginTop: -30 }}>
        <span style={{ color: color, fontSize: 24, fontWeight: 'bold' }}>
          {value.toFixed(4)}
        </span>
        {label && (
          <span style={{ color: '#888', fontSize: 12, marginLeft: 4 }}>{label}</span>
        )}
      </div>
    </div>
  );
}
