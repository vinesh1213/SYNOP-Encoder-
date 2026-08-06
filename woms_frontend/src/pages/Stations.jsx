import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, X, AlertCircle } from 'lucide-react';

export default function Stations() {
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('add'); // 'add' or 'edit'
  
  // Form State
  const [formValues, setFormValues] = useState({
    id: null,
    station_number: '',
    station_name: '',
    latitude: '',
    longitude: '',
    elevation: '',
    base_station_email: '',
    station_type: 'manned',
    is_active: true
  });
  
  const [formErrors, setFormErrors] = useState({});

  const fetchStations = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/api/stations/');
      if (!res.ok) throw new Error('Failed to load stations data');
      const data = await res.json();
      setStations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStations();
  }, []);

  const openAddModal = () => {
    setModalMode('add');
    setFormValues({
      id: null,
      station_number: '',
      station_name: '',
      latitude: '',
      longitude: '',
      elevation: '',
      base_station_email: '',
      station_type: 'manned',
      is_active: true
    });
    setFormErrors({});
    setShowModal(true);
  };

  const openEditModal = (station) => {
    setModalMode('edit');
    setFormValues({
      id: station.id,
      station_number: station.station_number,
      station_name: station.station_name,
      latitude: station.latitude.toString(),
      longitude: station.longitude.toString(),
      elevation: station.elevation.toString(),
      base_station_email: station.base_station_email,
      station_type: station.station_type,
      is_active: station.is_active
    });
    setFormErrors({});
    setShowModal(true);
  };

  const validateForm = () => {
    const errors = {};
    if (!formValues.station_number) {
      errors.station_number = 'Station WMO code is required';
    } else if (!/^\d{5}$/.test(formValues.station_number)) {
      errors.station_number = 'Station WMO code must be exactly 5 digits (e.g., 42960)';
    }

    if (!formValues.station_name.trim()) {
      errors.station_name = 'Station name is required';
    }

    const lat = parseFloat(formValues.latitude);
    if (isNaN(lat) || lat < -90 || lat > 90) {
      errors.latitude = 'Latitude must be between -90 and 90';
    }

    const lng = parseFloat(formValues.longitude);
    if (isNaN(lng) || lng < -180 || lng > 180) {
      errors.longitude = 'Longitude must be between -180 and 180';
    }

    const elev = parseFloat(formValues.elevation);
    if (isNaN(elev) || elev < -100) {
      errors.elevation = 'Elevation must be a valid number';
    }

    if (!formValues.base_station_email.trim()) {
      errors.base_station_email = 'Email address is required';
    } else if (!/\S+@\S+\.\S+/.test(formValues.base_station_email)) {
      errors.base_station_email = 'Please provide a valid email';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormValues(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      const method = modalMode === 'add' ? 'POST' : 'PUT';
      const url = modalMode === 'add' 
        ? 'http://localhost:8000/api/stations/' 
        : `http://localhost:8000/api/stations/${formValues.id}/`;

      const res = await fetch(url, {
        method: method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          station_number: formValues.station_number,
          station_name: formValues.station_name,
          latitude: parseFloat(formValues.latitude),
          longitude: parseFloat(formValues.longitude),
          elevation: parseFloat(formValues.elevation),
          base_station_email: formValues.base_station_email,
          station_type: formValues.station_type,
          is_active: formValues.is_active,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        // Set field errors if backend reports them
        const backendErrors = {};
        Object.keys(errorData).forEach(key => {
          backendErrors[key] = Array.isArray(errorData[key]) ? errorData[key].join(', ') : errorData[key];
        });
        setFormErrors(backendErrors);
        throw new Error('Save failed');
      }

      setShowModal(false);
      fetchStations();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this station?')) return;
    try {
      const res = await fetch(`http://localhost:8000/api/stations/${id}/`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Deletion failed');
      fetchStations();
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2.25rem', marginBottom: '0.25rem' }}>Meteorological Stations</h1>
          <p style={{ color: 'var(--text-muted)' }}>Index of WMO meteorological observing stations</p>
        </div>
        <button className="btn btn-primary" onClick={openAddModal} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <Plus size={18} />
          Add Station
        </button>
      </div>

      {error && (
        <div className="glass-card" style={{ borderLeft: '4px solid var(--color-danger)', marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <AlertCircle size={20} style={{ color: 'var(--color-danger)' }} />
          <span style={{ color: 'var(--text-muted)' }}>Failed to fetch stations: {error}</span>
        </div>
      )}

      {loading ? (
        <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading stations...</div>
      ) : (
        <div className="glass-card">
          <div className="table-container">
            <table className="woms-table">
              <thead>
                <tr>
                  <th>WMO Index</th>
                  <th>Station Name</th>
                  <th>Type</th>
                  <th>Coordinates (Lat/Lng)</th>
                  <th>Elevation</th>
                  <th>Email Target</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {stations.length === 0 ? (
                  <tr>
                    <td colSpan="8" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                      No meteorological stations found. Record one to start recording observations.
                    </td>
                  </tr>
                ) : (
                  stations.map((station) => (
                    <tr key={station.id}>
                      <td style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{station.station_number}</td>
                      <td style={{ fontWeight: 600 }}>{station.station_name}</td>
                      <td style={{ textTransform: 'capitalize' }}>{station.station_type}</td>
                      <td>
                        {station.latitude}°N, {station.longitude}°E
                      </td>
                      <td>{station.elevation} m</td>
                      <td>
                        <code style={{ fontSize: '0.85rem' }}>{station.base_station_email}</code>
                      </td>
                      <td>
                        <span className={`badge ${station.is_active ? 'badge-success' : 'badge-failed'}`} style={{ minWidth: '70px', justifyContent: 'center' }}>
                          {station.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '0.75rem' }}>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.4rem', border: 'none', borderRadius: '4px' }}
                            onClick={() => openEditModal(station)}
                          >
                            <Edit2 size={15} />
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.4rem', border: 'none', borderRadius: '4px', color: 'var(--color-danger)' }}
                            onClick={() => handleDelete(station.id)}
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2>{modalMode === 'add' ? 'Add Meteorological Station' : 'Edit Station Details'}</h2>
              <button
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                onClick={() => setShowModal(false)}
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="input-group">
                  <label className="input-label">WMO Station Index (IIiii)</label>
                  <input
                    type="text"
                    name="station_number"
                    maxLength="5"
                    className="input-field"
                    placeholder="e.g. 42960"
                    value={formValues.station_number}
                    onChange={handleInputChange}
                    disabled={modalMode === 'edit'}
                  />
                  {formErrors.station_number && <span className="field-error">{formErrors.station_number}</span>}
                </div>

                <div className="input-group">
                  <label className="input-label">Station Name</label>
                  <input
                    type="text"
                    name="station_name"
                    className="input-field"
                    placeholder="e.g. Bhubaneswar"
                    value={formValues.station_name}
                    onChange={handleInputChange}
                  />
                  {formErrors.station_name && <span className="field-error">{formErrors.station_name}</span>}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
                <div className="input-group">
                  <label className="input-label">Latitude (°N)</label>
                  <input
                    type="text"
                    name="latitude"
                    className="input-field"
                    placeholder="e.g. 20.244"
                    value={formValues.latitude}
                    onChange={handleInputChange}
                  />
                  {formErrors.latitude && <span className="field-error">{formErrors.latitude}</span>}
                </div>

                <div className="input-group">
                  <label className="input-label">Longitude (°E)</label>
                  <input
                    type="text"
                    name="longitude"
                    className="input-field"
                    placeholder="e.g. 85.818"
                    value={formValues.longitude}
                    onChange={handleInputChange}
                  />
                  {formErrors.longitude && <span className="field-error">{formErrors.longitude}</span>}
                </div>

                <div className="input-group">
                  <label className="input-label">Elevation (m)</label>
                  <input
                    type="text"
                    name="elevation"
                    className="input-field"
                    placeholder="e.g. 46"
                    value={formValues.elevation}
                    onChange={handleInputChange}
                  />
                  {formErrors.elevation && <span className="field-error">{formErrors.elevation}</span>}
                </div>
              </div>

              <div className="input-group">
                <label className="input-label">Station Email (SYNOP Transmission target)</label>
                <input
                  type="email"
                  name="base_station_email"
                  className="input-field"
                  placeholder="e.g. bhubaneswar@imd.gov.in"
                  value={formValues.base_station_email}
                  onChange={handleInputChange}
                />
                {formErrors.base_station_email && <span className="field-error">{formErrors.base_station_email}</span>}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', alignItems: 'center', marginTop: '0.5rem', marginBottom: '1.5rem' }}>
                <div className="input-group" style={{ marginBottom: 0 }}>
                  <label className="input-label">Station Type</label>
                  <select
                    name="station_type"
                    className="input-field"
                    value={formValues.station_type}
                    onChange={handleInputChange}
                    style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                  >
                    <option value="manned" style={{ background: '#0f1524' }}>Manned Met Station</option>
                    <option value="automatic" style={{ background: '#0f1524' }}>Automatic Weather Station (AWS)</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1.25rem' }}>
                  <input
                    type="checkbox"
                    id="is_active"
                    name="is_active"
                    checked={formValues.is_active}
                    onChange={handleInputChange}
                    style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--color-primary)' }}
                  />
                  <label htmlFor="is_active" style={{ fontSize: '0.9rem', cursor: 'pointer', fontWeight: 500 }}>Active Station</label>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Station
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
