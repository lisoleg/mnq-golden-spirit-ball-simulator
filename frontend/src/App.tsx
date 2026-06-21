import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import theme from './theme';
import Layout from './components/Layout';
import ExperimentRunner from './pages/ExperimentRunner';
import FrozenKernelPanel from './pages/FrozenKernelPanel';
import MassFacePanel from './pages/MassFacePanel';
import SCFPanel from './pages/SCFPanel';
import CGDPanel from './pages/CGDPanel';
import MNQ9Panel from './pages/MNQ9Panel';
import DeepPanel from './pages/DeepPanel';
import KappaBrowser from './pages/KappaBrowser';
import ExperimentHistory from './pages/ExperimentHistory';

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<ExperimentRunner />} />
            <Route path="kernel" element={<FrozenKernelPanel />} />
            <Route path="massface" element={<MassFacePanel />} />
            <Route path="scf" element={<SCFPanel />} />
            <Route path="cgd" element={<CGDPanel />} />
            <Route path="mnq9" element={<MNQ9Panel />} />
            <Route path="deep" element={<DeepPanel />} />
            <Route path="kappa" element={<KappaBrowser />} />
            <Route path="history" element={<ExperimentHistory />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
