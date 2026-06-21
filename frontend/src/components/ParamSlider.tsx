import { Box, Typography, Slider, TextField } from '@mui/material';

interface ParamSliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}

export default function ParamSlider({ label, value, min, max, step, onChange }: ParamSliderProps) {
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="body2" sx={{ color: '#e0e0e0', mb: 1 }}>
        {label}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Slider
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(Number((e.target as HTMLInputElement).value))}
          sx={{
            color: '#1890ff',
            '& .MuiSlider-thumb': { backgroundColor: '#1890ff' },
            '& .MuiSlider-track': { backgroundColor: '#1890ff' },
            '& .MuiSlider-rail': { backgroundColor: '#0f3460' },
          }}
        />
        <TextField
          type="number"
          value={value}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (!isNaN(v) && v >= min && v <= max) onChange(v);
          }}
          size="small"
          sx={{
            width: 80,
            '& .MuiInputBase-input': { color: '#e0e0e0', textAlign: 'center' },
            '& .MuiOutlinedInput-notchedOutline': { borderColor: '#0f3460' },
          }}
          inputProps={{ min, max, step }}
        />
      </Box>
    </Box>
  );
}
