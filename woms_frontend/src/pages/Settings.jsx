import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save } from 'lucide-react';

export default function Settings({ theme, setTheme }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/settings/')
      .then(res => res.json())
      .then(data => {
        if (data && data.general) {
          data.general.theme = theme;
        }
        setConfig(data);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  const handleChange = (section, key, value) => {
    if (section === 'general' && key === 'theme' && setTheme) {
      setTheme(value);
    }
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };


  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch('http://localhost:8000/api/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      alert('Settings saved successfully!');
    } catch (err) {
      alert('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Loading settings...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '800px' }}>
      <h1><SettingsIcon className="text-primary" /> Configuration</h1>
      
      <div className="glass-card">
        <h3>General Settings</h3>
        <div className="input-group" style={{ marginTop: '1rem' }}>
          <label>Theme</label>
          <select value={config.general.theme} onChange={(e) => handleChange('general', 'theme', e.target.value)}>
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </div>
      </div>

      <div className="glass-card">
        <h3>Units & Formatting</h3>
        <div className="input-group" style={{ marginTop: '1rem' }}>
          <label>Wind Unit</label>
          <select value={config.units.wind_unit} onChange={(e) => handleChange('units', 'wind_unit', e.target.value)}>
            <option value="knots">Knots</option>
            <option value="m/s">m/s</option>
          </select>
        </div>
        <div className="input-group" style={{ marginTop: '1rem' }}>
          <label>
            <input type="checkbox" checked={config.units.show_section_333} onChange={(e) => handleChange('units', 'show_section_333', e.target.checked)} style={{ marginRight: '0.5rem' }} />
            Show Section 333 (Regional) in Forms
          </label>
        </div>
      </div>

      <div className="glass-card">
        <h3>Auto Decoder (Background Task)</h3>
        <div className="input-group" style={{ marginTop: '1rem' }}>
          <label>
            <input type="checkbox" checked={config.auto_decoder.enabled} onChange={(e) => handleChange('auto_decoder', 'enabled', e.target.checked)} style={{ marginRight: '0.5rem' }} />
            Enable Auto Decoder
          </label>
        </div>
        <div className="input-group" style={{ marginTop: '1rem' }}>
          <label>Interval (Seconds)</label>
          <input type="number" value={config.auto_decoder.interval_seconds} onChange={(e) => handleChange('auto_decoder', 'interval_seconds', parseInt(e.target.value))} />
        </div>
        <div className="input-group" style={{ marginTop: '1rem' }}>
          <label>Input Folder</label>
          <input type="text" value={config.auto_decoder.input_folder} onChange={(e) => handleChange('auto_decoder', 'input_folder', e.target.value)} />
        </div>
      </div>
      
      <button className="btn-primary" onClick={handleSave} disabled={saving} style={{ alignSelf: 'flex-start', display: 'flex', gap: '0.5rem' }}>
        <Save size={18} /> {saving ? 'Saving...' : 'Save Configuration'}
      </button>
    </div>
  );
}
