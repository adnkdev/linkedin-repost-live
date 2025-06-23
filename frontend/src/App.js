import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'https://linkedin-repost-live-1.onrender.com/api';
const CALLBACK_PATH = '/linkedin-callback';

export default function App() {
  const [status, setStatus] = useState('idle');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [keyword, setKeyword] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const didExchange = useRef(false);

  useEffect(() => {
    if (
      window.location.pathname === CALLBACK_PATH &&
      !didExchange.current
    ) {
      didExchange.current = true;
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const state = params.get('state');
      if (code && state) {
        setStatus('exchanging');
        axios.post(`${API_BASE}/exchange_token`, { code, state })
          .then(res => {
            setData(res.data);
            setStatus('done');
          })
          .catch(err => {
            console.error(err);
            setError(err.response?.data?.error || 'Exchange failed');
            setStatus('error');
          });
      } else {
        setError('Missing code or state');
        setStatus('error');
      }
    }
  }, []);

  const handleLogin = async () => {
    setStatus('starting');
    try {
      const res = await axios.get(`${API_BASE}/start_oauth`);
      window.location.href = res.data.authUrl;
    } catch (err) {
      console.error(err);
      setError('Failed to initiate LinkedIn login');
      setStatus('error');
    }
  };

  const handleStartBot = async () => {
    if (!data?.access_token || !keyword || !email || !password) {
      alert('Please login and enter a keyword, email, and password.');
      return;
    }
    try {
      const res = await axios.post(`${API_BASE}/start_bot`, {
        access_token: data.access_token,
        keyword: keyword,
        email: email,
        password: password
      });
      if (res.data.started) setStatus('running');
      else alert('Bot is already running.');
    } catch (err) {
      console.error(err);
      alert('Failed to start bot');
    }
  };

  const handleStopBot = async () => {
    try {
      const res = await axios.post(`${API_BASE}/stop_bot`);
      if (res.data.stopped) setStatus('stopped');
      else alert('Bot was not running.');
    } catch (err) {
      console.error(err);
      alert('Failed to stop bot');
    }
  };

  const openVnc = () => {
    window.open(`http://${window.location.hostname}:6080/vnc.html`, '_blank');
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: '#f3f4f6',
      fontFamily: 'sans-serif',
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '2rem',
        borderRadius: '12px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
        width: '100%',
        maxWidth: '500px'
      }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 'bold', marginBottom: '1rem', textAlign: 'center' }}>
          LinkedIn Bot Control
        </h1>
  
        <p style={{ marginBottom: '1rem', textAlign: 'center' }}>
          Status: <strong>{status}</strong>
        </p>
  
        {status === 'error' && (
          <p style={{ color: 'red', marginBottom: '1rem', textAlign: 'center' }}>{error}</p>
        )}
  
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1.5rem' }}>
          <button
            onClick={handleLogin}
            disabled={status === 'running'}
            style={{
              padding: '0.75rem 1.25rem',
              borderRadius: '8px',
              backgroundColor: '#0073b1',
              color: 'white',
              border: 'none',
              fontWeight: 'bold',
              cursor: status === 'running' ? 'not-allowed' : 'pointer'
            }}
          >
            Login with LinkedIn
          </button>
        </div>
  
        {data && (
          <>
            <h3 style={{ textAlign: 'center', marginBottom: '1rem' }}>
              Welcome, {data.profile?.localizedFirstName} {data.profile?.localizedLastName}
            </h3>
  
            <div style={{ marginBottom: '1rem' }}>
              <label>Keyword</label>
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="e.g. Web Development"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  marginTop: '0.25rem',
                  borderRadius: '6px',
                  border: '1px solid #ccc'
                }}
              />
            </div>
  
            <div style={{ marginBottom: '1rem' }}>
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="example@mail.com"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  marginTop: '0.25rem',
                  borderRadius: '6px',
                  border: '1px solid #ccc'
                }}
              />
            </div>
  
            <div style={{ marginBottom: '1.5rem' }}>
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  marginTop: '0.25rem',
                  borderRadius: '6px',
                  border: '1px solid #ccc'
                }}
              />
            </div>
  
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <button onClick={handleStartBot} disabled={status === 'running'} style={{
                padding: '0.75rem',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 'bold',
                cursor: status === 'running' ? 'not-allowed' : 'pointer'
              }}>
                Start Bot
              </button>
  
              <button onClick={handleStopBot} disabled={status !== 'running'} style={{
                padding: '0.75rem',
                backgroundColor: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 'bold',
                cursor: status !== 'running' ? 'not-allowed' : 'pointer'
              }}>
                Stop Bot
              </button>
  
              <button onClick={openVnc} style={{
                padding: '0.75rem',
                backgroundColor: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 'bold'
              }}>
                Open Manual Login (VNC)
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );  
}
