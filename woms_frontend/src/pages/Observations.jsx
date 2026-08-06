import React, { useState, useEffect } from 'react';
import { Radio, Calendar, CheckCircle, RefreshCw, X, AlertCircle, Download } from 'lucide-react';

export default function Observations() {
  const [observations, setObservations] = useState([]);
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedObs, setSelectedObs] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [validatingId, setValidatingId] = useState(null);

  // Filters
  const [filterStation, setFilterStation] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterDate, setFilterDate] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch stations for filter dropdown
      const stationsRes = await fetch('http://localhost:8000/api/stations/');
      if (stationsRes.ok) {
        const stationsData = await stationsRes.json();
        setStations(stationsData);
      }

      // Build observation query
      let url = 'http://localhost:8000/api/observations/';
      const params = [];
      if (filterStation) params.push(`station=${filterStation}`);
      if (filterDate) params.push(`date=${filterDate}`);
      if (filterStatus) params.push(`email_status=${filterStatus}`); // standard filter
      
      if (params.length > 0) {
        url += `?${params.join('&')}`;
      }

      const obsRes = await fetch(url);
      if (!obsRes.ok) throw new Error('Failed to load observations');
      let obsData = await obsRes.json();
      
      // Perform local filtering for validation status if needed
      if (filterStatus === 'validated') {
        obsData = obsData.filter(o => o.is_validated);
      } else if (filterStatus === 'draft') {
        obsData = obsData.filter(o => !o.is_validated);
      }

      setObservations(obsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterStation, filterStatus, filterDate]);

  const handleTriggerValidation = async (id) => {
    setValidatingId(id);
    try {
      const res = await fetch(`http://localhost:8000/api/observations/${id}/validate_obs/`, {
        method: 'POST',
      });
      const result = await res.json();
      if (res.ok && result.is_validated) {
        alert('Observation validated and saved to CSV successfully!');
        fetchData();
        if (selectedObs && selectedObs.id === id) {
          // Update details drawer
          setSelectedObs(prev => ({ ...prev, is_validated: true }));
        }
      } else {
        alert('Validation failed with errors: ' + JSON.stringify(result.errors || result));
      }
    } catch (err) {
      alert('Error communicating with backend: ' + err.message);
    } finally {
      setValidatingId(null);
    }
  };

  const handleRowClick = (obs) => {
    setSelectedObs(obs);
    setShowDetail(true);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2.25rem', marginBottom: '0.25rem' }}>Observation Logs</h1>
          <p style={{ color: 'var(--text-muted)' }}>Synoptic reports history and transmission verification</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <a
            className="btn btn-secondary"
            href="http://localhost:8000/api/observations/csv/all/"
            target="_blank"
            rel="noopener noreferrer"
            style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', textDecoration: 'none' }}
          >
            <Download size={16} />
            Export CSV Log
          </a>
          <button className="btn btn-secondary" onClick={fetchData} disabled={loading} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="glass-card" style={{ borderLeft: '4px solid var(--color-danger)', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <AlertCircle size={20} style={{ color: 'var(--color-danger)' }} />
          <span style={{ color: 'var(--text-muted)' }}>Error loading observations: {error}</span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="glass-card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', padding: '1.25rem', marginBottom: '2rem' }}>
        <div className="input-group" style={{ marginBottom: 0 }}>
          <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Radio size={14} /> Filter by Station</label>
          <select
            className="input-field"
            value={filterStation}
            onChange={(e) => setFilterStation(e.target.value)}
            style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
          >
            <option value="" style={{ background: '#0f1524' }}>All Stations</option>
            {stations.map(s => (
              <option key={s.id} value={s.id} style={{ background: '#0f1524' }}>{s.station_number} - {s.station_name}</option>
            ))}
          </select>
        </div>

        <div className="input-group" style={{ marginBottom: 0 }}>
          <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><CheckCircle size={14} /> Status</label>
          <select
            className="input-field"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
          >
            <option value="" style={{ background: '#0f1524' }}>All Statuses</option>
            <option value="validated" style={{ background: '#0f1524' }}>Validated</option>
            <option value="draft" style={{ background: '#0f1524' }}>Draft / Pending</option>
            <option value="sent" style={{ background: '#0f1524' }}>Transmission Sent</option>
            <option value="failed" style={{ background: '#0f1524' }}>Transmission Failed</option>
          </select>
        </div>

        <div className="input-group" style={{ marginBottom: 0 }}>
          <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}><Calendar size={14} /> Date</label>
          <input
            type="date"
            className="input-field"
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
          />
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading observations data...</div>
      ) : (
        <div className="glass-card">
          <div className="table-container">
            <table className="woms-table">
              <thead>
                <tr>
                  <th>Date/Time</th>
                  <th>Station</th>
                  <th>SYNOP Code</th>
                  <th>Validation</th>
                  <th>Transmission</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {observations.length === 0 ? (
                  <tr>
                    <td colSpan="7" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                      No weather observations found matching filters.
                    </td>
                  </tr>
                ) : (
                  observations.map((obs) => (
                    <tr key={obs.id} style={{ cursor: 'pointer' }} onClick={() => handleRowClick(obs)}>
                      <td style={{ fontWeight: 600 }}>
                        {obs.observation_date} <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 400 }}>{obs.observation_time.substring(0, 5)} UTC</span>
                      </td>
                      <td>{obs.station_details?.station_name || `Station ${obs.station}`}</td>
                      <td>
                        <code style={{ color: 'var(--color-primary)', fontStyle: 'normal' }}>
                          {obs.generated_synop ? (obs.generated_synop.length > 32 ? obs.generated_synop.substring(0, 32) + '...' : obs.generated_synop) : 'No SYNOP generated'}
                        </code>
                      </td>
                      <td>
                        <span className={`badge ${obs.is_validated ? 'badge-success' : 'badge-pending'}`}>
                          {obs.is_validated ? 'Validated' : 'Pending'}
                        </span>
                      </td>
                      <td>
                        <span className={`badge badge-${obs.email_status}`}>
                          {obs.email_status}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
                        {obs.is_validated ? (
                          <a
                            className="btn btn-secondary"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', display: 'inline-flex', gap: '0.35rem', alignItems: 'center', textDecoration: 'none' }}
                            href={`http://localhost:8000/api/observations/${obs.id}/csv/`}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Download CSV"
                          >
                            <Download size={14} /> Download CSV
                          </a>
                        ) : (
                          <button
                            className="btn btn-primary"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                            onClick={() => handleTriggerValidation(obs.id)}
                            disabled={validatingId === obs.id}
                          >
                            {validatingId === obs.id ? 'Validating...' : 'Validate'}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Slide-out details drawer */}
      {showDetail && selectedObs && (
        <div className="modal-overlay" onClick={() => setShowDetail(false)}>
          <div className="modal-content" style={{ maxWidth: '750px', width: '90%', maxHeight: '90vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontSize: '1.5rem' }}>Observation Details</h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  Obs ID: {selectedObs.id} • Station {selectedObs.station_details?.station_number} ({selectedObs.station_details?.station_name})
                </p>
              </div>
              <button style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }} onClick={() => setShowDetail(false)}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
              <div className="glass-card" style={{ flex: '1 1 200px', padding: '1rem', background: 'rgba(255, 255, 255, 0.02)' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Observation Time</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.25rem' }}>{selectedObs.observation_date} {selectedObs.observation_time.substring(0, 5)} UTC</div>
              </div>
              <div className="glass-card" style={{ flex: '1 1 200px', padding: '1rem', background: 'rgba(255, 255, 255, 0.02)', display: 'none' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Observer Name</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.25rem' }}>{selectedObs.observer_name}</div>
              </div>
              <div className="glass-card" style={{ flex: '1 1 200px', padding: '1rem', background: 'rgba(255, 255, 255, 0.02)' }}>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Validation / Email</div>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                  <span className={`badge ${selectedObs.is_validated ? 'badge-success' : 'badge-pending'}`}>
                    {selectedObs.is_validated ? 'Validated' : 'Pending'}
                  </span>
                  <span className={`badge badge-${selectedObs.email_status}`}>
                    {selectedObs.email_status}
                  </span>
                </div>
              </div>
            </div>

            {/* Generated SYNOP Code Display */}
            <div className="glass-card" style={{ background: 'rgba(6, 182, 212, 0.04)', borderColor: 'rgba(6, 182, 212, 0.2)', marginBottom: '2.5rem' }}>
              <h3 style={{ fontSize: '0.95rem', color: 'var(--color-primary)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Generated WMO FM-12 SYNOP Message
              </h3>
              <div style={{ fontFamily: 'monospace', fontSize: '1.25rem', fontWeight: 700, wordBreak: 'break-all', color: '#fff', background: '#070b13', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                {selectedObs.generated_synop || 'NO SYNOP GENERATED (OBSERVATION IS STILL DRAFT)'}
              </div>
            </div>

            {/* Detailed Parameters */}
            <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>Reported Metrics</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Wind Velocity</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.wind_direction}° at {selectedObs.wind_speed} {selectedObs.wind_unit}
                </div>
              </div>

              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Visibility</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.visibility} {selectedObs.visibility_unit} ({selectedObs.visibility_reason !== 'none' ? selectedObs.visibility_reason : 'Normal'})
                </div>
              </div>

              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Cloud Cover</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.total_cloud_cover} oktas (Base: {selectedObs.lowest_cloud_base} m)
                </div>
              </div>

              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Temperatures (Dry / Wet / Dew)</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.dry_bulb}°C / {selectedObs.wet_bulb}°C / {selectedObs.dew_point}°C
                </div>
              </div>

              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Pressures (Station / MSL)</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.station_pressure} hPa / {selectedObs.msl_pressure} hPa
                </div>
              </div>

              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Rainfall (Since 0300 UTC)</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.rainfall} mm ({selectedObs.rain_duration || 0} hours)
                </div>
              </div>
            </div>

            <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', marginTop: '2rem' }}>Section 333 (Regional)</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>24h Max / Min Temp</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.sec333_max_temperature !== null ? `${selectedObs.sec333_max_temperature}°C` : '--'} / {selectedObs.sec333_min_temperature !== null ? `${selectedObs.sec333_min_temperature}°C` : '--'}
                </div>
              </div>

              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Ground State / Sunshine</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  Code {selectedObs.ground_state !== null ? selectedObs.ground_state : '--'} / {selectedObs.sunshine_hours !== null ? `${selectedObs.sunshine_hours} hrs` : '--'}
                </div>
              </div>

              <div style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>24h Rainfall / Evap</span>
                <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.25rem' }}>
                  {selectedObs.rainfall_24h !== null ? `${selectedObs.rainfall_24h} mm` : '--'} / {selectedObs.evaporation !== null ? `${selectedObs.evaporation} mm` : '--'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '2.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
              <a
                className="btn btn-secondary"
                href={`http://localhost:8000/api/observations/${selectedObs.id}/csv/`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', textDecoration: 'none' }}
              >
                <Download size={16} /> Download CSV
              </a>
              {!selectedObs.is_validated && (
                <button
                  className="btn btn-primary"
                  onClick={() => handleTriggerValidation(selectedObs.id)}
                  disabled={validatingId === selectedObs.id}
                >
                  {validatingId === selectedObs.id ? 'Validating...' : 'Validate Report'}
                </button>
              )}
              <button className="btn btn-secondary" onClick={() => setShowDetail(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
