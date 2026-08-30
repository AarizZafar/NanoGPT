import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  AlertCircle,
  BarChart3,
  Brain,
  Check,
  CircleDot,
  Code2,
  FileText,
  Loader2,
  Play,
  Settings2,
  Upload,
  Zap,
} from 'lucide-react';
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { apiRequest, apiUrl, websocketUrl } from './api';
import './styles.css';

ChartJS.register(CategoryScale, LinearScale, LineController, LineElement, PointElement, Filler, Tooltip);

const initialParams = {
  block_size: 32,
  batch_size: 32,
  n_embd: 64,
  n_head: 4,
  n_layer: 4,
  max_iters: 5000,
  eval_interval: 200,
  max_new_tokens: 300,
  learning_rate: -2.5,
  dropout: 0.2,
};

const datasetIcons = {
  'shakes_spear.txt': FileText,
  'rich_dad_poor_dad.txt': Zap,
  'law_of_human_nature.txt': Brain,
};

function friendlyName(filename) {
  return filename.replace('.txt', '').replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function clamp(value, min, max) {
  return Math.min(Math.max(Number(value), min), max);
}

function useLossChart(canvasRef, points) {
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return undefined;

    chartRef.current = new ChartJS(canvasRef.current, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Train',
            data: [],
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: '#2563eb',
            tension: 0.35,
            fill: true,
          },
          {
            label: 'Val',
            data: [],
            borderColor: '#14b8a6',
            borderWidth: 2,
            borderDash: [5, 4],
            pointRadius: 3,
            pointBackgroundColor: '#14b8a6',
            tension: 0.35,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#111827',
            titleColor: '#cbd5e1',
            bodyColor: '#ffffff',
            padding: 10,
          },
        },
        scales: {
          x: { grid: { color: '#eef2f7' }, ticks: { color: '#64748b' } },
          y: { grid: { color: '#eef2f7' }, ticks: { color: '#64748b' } },
        },
      },
    });

    return () => chartRef.current?.destroy();
  }, [canvasRef]);

  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.data.labels = points.map((point) => point.epoch);
    chartRef.current.data.datasets[0].data = points.map((point) => point.train_loss);
    chartRef.current.data.datasets[1].data = points.map((point) => point.val_loss);
    chartRef.current.update('none');
  }, [points]);
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Field({ label, value, onChange, min, max }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" min={min} max={max} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function App() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [fileMeta, setFileMeta] = useState('');
  const [vocabSize, setVocabSize] = useState(null);
  const [params, setParams] = useState(initialParams);
  const [points, setPoints] = useState([]);
  const [generatedText, setGeneratedText] = useState('');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);
  const socketRef = useRef(null);

  useLossChart(canvasRef, points);

  const latestPoint = points.at(-1);
  const hasDataset = Boolean(vocabSize);
  const invalidShape = Number(params.n_embd) % Number(params.n_head) !== 0;
  const progress = latestPoint ? `${((latestPoint.epoch / Number(params.max_iters)) * 100).toFixed(1)}%` : '-';
  const learningRate = Math.pow(10, Number(params.learning_rate));
  const canTrain = useMemo(() => hasDataset && !invalidShape && status !== 'training', [hasDataset, invalidShape, status]);

  useEffect(() => {
    apiRequest('/datasets')
      .then((data) => setDatasets(data.datasets || []))
      .catch((err) => setError(err.message));
  }, []);

  function updateParam(key, value) {
    setParams((current) => ({ ...current, [key]: value }));
  }

  async function selectDataset(filename) {
    try {
      setError('');
      const data = await apiRequest(`/upload-default?filename=${encodeURIComponent(filename)}`, { method: 'POST' });
      setSelectedDataset(filename);
      setFileMeta('');
      setVocabSize(data.vocab_size);
    } catch (err) {
      setError(err.message);
    }
  }

  async function uploadFile(file) {
    if (!file) return;
    try {
      setError('');
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(apiUrl('/upload'), { method: 'POST', body: formData });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Upload failed');
      }
      const data = await response.json();
      setSelectedDataset('');
      setFileMeta(`${file.name} - ${(file.size / 1024).toFixed(1)} KB`);
      setVocabSize(data.vocab_size);
    } catch (err) {
      setError(err.message);
    }
  }

  function connectTrainingStream(attempt = 1) {
    const socket = new WebSocket(websocketUrl('/ws/loss'));
    let completed = false;
    socketRef.current = socket;

    socket.onopen = () => {
      setError('');
    };

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'loss') setPoints((current) => [...current, message]);
      if (message.type === 'text') setGeneratedText(message.text);
      if (message.type === 'done') {
        completed = true;
        setStatus('ready');
        socketRef.current = null;
        socket.close(1000, 'training complete');
      }
    };

    socket.onerror = () => {
      socket.close();
    };

    socket.onclose = () => {
      if (completed) return;
      if (socketRef.current !== socket) return;
      setStatus((current) => {
        if (current !== 'training') return current;
        if (attempt < 3) {
          window.setTimeout(() => connectTrainingStream(attempt + 1), 1000 * attempt);
          return current;
        }
        setError('Training stream disconnected. Refresh the page and try again.');
        return 'idle';
      });
    };
  }

  async function startTraining() {
    try {
      setError('');
      setPoints([]);
      setGeneratedText('');
      setStatus('training');
      const previousSocket = socketRef.current;
      socketRef.current = null;
      previousSocket?.close();

      await apiRequest('/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          block_size: clamp(params.block_size, 8, 512),
          batch_size: clamp(params.batch_size, 4, 256),
          n_embd: clamp(params.n_embd, 16, 512),
          n_head: clamp(params.n_head, 1, 16),
          n_layer: clamp(params.n_layer, 1, 12),
          max_iters: clamp(params.max_iters, 100, 100000),
          eval_interval: clamp(params.eval_interval, 50, 1000),
          max_new_tokens: clamp(params.max_new_tokens, 50, 2000),
          learning_rate: learningRate,
          dropout: Number(params.dropout),
        }),
      });

      connectTrainingStream();
    } catch (err) {
      const currentSocket = socketRef.current;
      socketRef.current = null;
      currentSocket?.close();
      setStatus('idle');
      setError(err.message);
    }
  }

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">N</div>
          <div>
            <h1>NanoGPT Training Studio</h1>
            <p>Character-level transformer training workspace</p>
          </div>
        </div>
        <div className="topbar-actions">
          <a href="https://github.com/AarizZafar/NanoGPT" target="_blank" rel="noreferrer" aria-label="Open GitHub repo">
            <Code2 size={18} />
            <span>AarizZafar/NanoGPT</span>
          </a>
          <div className={`status-pill ${status}`}>
            {status === 'training' ? <Loader2 size={16} className="spin" /> : <CircleDot size={16} />}
            <span>{status}</span>
          </div>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <main className="workspace">
        <section className="side-stack">
          <div className="panel">
            <div className="panel-heading">
              <h2>Dataset</h2>
              {vocabSize && <span className="badge">vocab {vocabSize}</span>}
            </div>

            <button
              className={`drop-zone ${dragging ? 'dragging' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                uploadFile(event.dataTransfer.files[0]);
              }}
            >
              <Upload size={26} />
              <span>Drop a text file or browse</span>
              <small>{fileMeta || 'UTF-8 .txt corpus'}</small>
            </button>
            <input ref={fileInputRef} className="hidden-input" type="file" accept=".txt" onChange={(event) => uploadFile(event.target.files[0])} />

            <div className="divider">Default Datasets</div>
            <div className="dataset-list">
              {datasets.map((dataset) => {
                const Icon = datasetIcons[dataset.name] || FileText;
                const selected = selectedDataset === dataset.name;
                return (
                  <button className={`dataset-row ${selected ? 'selected' : ''}`} key={dataset.name} onClick={() => selectDataset(dataset.name)}>
                    <Icon size={18} />
                    <span>
                      <strong>{friendlyName(dataset.name)}</strong>
                      <small>{dataset.size_kb} KB</small>
                    </span>
                    {selected && <Check size={18} />}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <h2>Hyperparameters</h2>
              <Settings2 size={18} />
            </div>
            <div className="params-grid">
              <Field label="Block Size" min="8" max="512" value={params.block_size} onChange={(value) => updateParam('block_size', value)} />
              <Field label="Batch Size" min="4" max="256" value={params.batch_size} onChange={(value) => updateParam('batch_size', value)} />
              <Field label="Embedding Dim" min="16" max="512" value={params.n_embd} onChange={(value) => updateParam('n_embd', value)} />
              <Field label="Heads" min="1" max="16" value={params.n_head} onChange={(value) => updateParam('n_head', value)} />
              <Field label="Layers" min="1" max="12" value={params.n_layer} onChange={(value) => updateParam('n_layer', value)} />
              <Field label="Max Iters" min="100" max="100000" value={params.max_iters} onChange={(value) => updateParam('max_iters', value)} />
              <Field label="Eval Interval" min="50" max="1000" value={params.eval_interval} onChange={(value) => updateParam('eval_interval', value)} />
              <Field label="Generate Tokens" min="50" max="2000" value={params.max_new_tokens} onChange={(value) => updateParam('max_new_tokens', value)} />
            </div>

            {invalidShape && <p className="inline-error">Embedding Dim must be divisible by Heads.</p>}

            <label className="slider-field">
              <span>Learning Rate <strong>{learningRate.toExponential(1)}</strong></span>
              <input type="range" min="-5" max="-1" step="0.25" value={params.learning_rate} onChange={(event) => updateParam('learning_rate', event.target.value)} />
            </label>
            <label className="slider-field">
              <span>Dropout <strong>{Number(params.dropout).toFixed(2)}</strong></span>
              <input type="range" min="0" max="0.5" step="0.05" value={params.dropout} onChange={(event) => updateParam('dropout', event.target.value)} />
            </label>

            <p className="param-note">Embedding Dim must be divisible by Heads.</p>

            <button className="train-button" disabled={!canTrain} onClick={startTraining}>
              {status === 'training' ? <Loader2 size={18} className="spin" /> : <Play size={18} />}
              <span>{status === 'training' ? 'Training' : 'Start Training'}</span>
            </button>
          </div>
        </section>

        <section className="main-stack">
          <div className="panel chart-panel">
            <div className="panel-heading">
              <h2>Training Loss</h2>
              <div className="legend">
                <span><i className="train-line" />Train</span>
                <span><i className="val-line" />Val</span>
              </div>
            </div>
            <div className="stats-grid">
              <Stat label="Step" value={latestPoint?.epoch ?? '-'} />
              <Stat label="Train Loss" value={latestPoint ? latestPoint.train_loss.toFixed(4) : '-'} />
              <Stat label="Val Loss" value={latestPoint ? latestPoint.val_loss.toFixed(4) : '-'} />
              <Stat label="Progress" value={progress} />
            </div>
            <div className="chart-wrap">
              <canvas ref={canvasRef} />
            </div>
          </div>

          <div className="detail-grid">
            <div className="panel">
              <div className="panel-heading">
                <h2>Loss Log</h2>
                <span className="badge">{points.length} entries</span>
              </div>
              <div className="log-pane">
                {points.length === 0 ? (
                  <div className="empty-state">
                    <BarChart3 size={24} />
                    <span>Loss events will appear during training.</span>
                  </div>
                ) : (
                  points.map((point) => (
                    <div className="log-row" key={point.epoch}>
                      <span>step {String(point.epoch).padStart(5, ' ')}</span>
                      <strong>train {point.train_loss.toFixed(4)}</strong>
                      <em>val {point.val_loss.toFixed(4)}</em>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="panel">
              <div className="panel-heading">
                <h2>Generated Text</h2>
                <span className="badge accent">
                  <Activity size={13} />
                  live
                </span>
              </div>
              <pre className="generated-pane">{generatedText || 'Model output will stream here during training.'}</pre>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
