import { useState, useEffect } from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Button, Dialog, DialogTitle, DialogContent, DialogActions, IconButton } from '@mui/material';
import { Delete, Download, Visibility } from '@mui/icons-material';
import * as kappaApi from '../api/kappa';
import type { Snapshot, KappaSnapshotDetail } from '../api/types';
import { formatTimestamp } from '../utils/formatters';

export default function KappaBrowser() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selected, setSelected] = useState<KappaSnapshotDetail | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSnapshots();
  }, []);

  const fetchSnapshots = async () => {
    setLoading(true);
    try {
      const data = await kappaApi.fetchSnapshots();
      setSnapshots(data);
    } catch (e) {
      console.error('Failed to fetch snapshots:', e);
    }
    setLoading(false);
  };

  const handleView = async (id: string) => {
    try {
      const detail = await kappaApi.fetchSnapshotDetail(id);
      setSelected(detail);
      setDialogOpen(true);
    } catch (e) {
      console.error('Failed to fetch snapshot detail:', e);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await kappaApi.deleteSnapshot(id);
      setSnapshots((prev) => prev.filter((s) => s.id !== id));
    } catch (e) {
      console.error('Failed to delete snapshot:', e);
    }
  };

  const handleDownload = async (id: string) => {
    try {
      const data = await kappaApi.downloadSnapshot(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `snapshot_${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Failed to download snapshot:', e);
    }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 3 }}>
        κ-Snap 快照浏览器
      </Typography>

      <TableContainer component={Paper} sx={{ backgroundColor: '#0f3460' }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: '#888' }}>ID</TableCell>
              <TableCell sx={{ color: '#888' }}>时间</TableCell>
              <TableCell sx={{ color: '#888' }}>实验</TableCell>
              <TableCell sx={{ color: '#888' }}>指纹</TableCell>
              <TableCell sx={{ color: '#888' }}>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {snapshots.map((s) => (
              <TableRow key={s.id}>
                <TableCell sx={{ color: '#e0e0e0' }}>{s.id}</TableCell>
                <TableCell sx={{ color: '#e0e0e0' }}>{formatTimestamp(s.timestamp)}</TableCell>
                <TableCell sx={{ color: '#1890ff' }}>{s.experiment}</TableCell>
                <TableCell sx={{ color: '#00ff88', fontFamily: '"Roboto Mono", monospace' }}>
                  {s.fingerprint}
                </TableCell>
                <TableCell>
                  <IconButton onClick={() => handleView(s.id)} sx={{ color: '#1890ff' }}>
                    <Visibility />
                  </IconButton>
                  <IconButton onClick={() => handleDownload(s.id)} sx={{ color: '#00ff88' }}>
                    <Download />
                  </IconButton>
                  <IconButton onClick={() => handleDelete(s.id)} sx={{ color: '#e94560' }}>
                    <Delete />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {snapshots.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} sx={{ color: '#555', textAlign: 'center' }}>
                  {loading ? '加载中...' : '无快照数据'}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ color: '#1890ff' }}>快照详情</DialogTitle>
        <DialogContent>
          <Box sx={{ backgroundColor: '#0a0a0a', p: 2, borderRadius: 1, maxHeight: 500, overflow: 'auto' }}>
            <pre style={{ color: '#00ff88', fontFamily: '"Roboto Mono", monospace', fontSize: 13 }}>
              {selected ? JSON.stringify(selected.data, null, 2) : ''}
            </pre>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} sx={{ color: '#888' }}>关闭</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
