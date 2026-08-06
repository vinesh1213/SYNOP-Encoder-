import React, { useState, useEffect } from 'react';
import { HelpCircle, Save, Check, Radio, Cloud, CloudRain, CloudLightning, CloudSnow, Thermometer, Plus, Trash2, AlertTriangle, Zap, Eye } from 'lucide-react';

const calculateDewPoint = (tDry, tWet, pressure) => {
  if (tDry === '' || tWet === '' || pressure === '') return '';
  const t = parseFloat(tDry);
  const tw = parseFloat(tWet);
  const p = parseFloat(pressure);
  if (isNaN(t) || isNaN(tw) || isNaN(p)) return '';

  const a = 17.27;
  const b = 237.7;
  const A = 0.000799;

  const eSatDry = 6.1078 * Math.exp((a * t) / (b + t));
  const eSatWet = 6.1078 * Math.exp((a * tw) / (b + tw));

  const eActual = eSatWet - A * p * (t - tw);
  const rh = (eActual / eSatDry) * 100.0;

  if (rh <= 0) return '';

  const alpha = ((a * t) / (b + t)) + Math.log(rh / 100.0);
  const td = (b * alpha) / (a - alpha);
  
  return td.toFixed(1);
};

// ─── Manual SYNOP Codes ────────

export default function NewObservation({ setCurrentPage }) {
  const [stations, setStations] = useState([]);
  const [loadingStations, setLoadingStations] = useState(true);
  const [saving, setSaving] = useState(false);
  // Station type from station settings (not user-entered per observation)
  const [stationType, setStationType] = useState('manned');

  const getCurrentSynopticHour = () => {
    const currentUtcHour = new Date().getUTCHours();
    const synopticHour = Math.floor(currentUtcHour / 3) * 3;
    return synopticHour.toString().padStart(2, '0');
  };

  // Form State — Observer enters ONLY meteorological observations
  const [formValues, setFormValues] = useState({
    station: '',
    observation_date: new Date().toISOString().substring(0, 10),
    observation_time: getCurrentSynopticHour(),
    observer_name: 'System',
    observation_type: 'routine',
    
    // ── Legacy SYNOP code fields ──
    precipitation_indicator: '1', // Default to section 1
    weather_indicator: '1',       // Default to 7-group included
    
    // Wind
    compass_direction: '',
    wind_direction: '',
    wind_readings: [],
    wind_speed: '',
    wind_unit: 'knots',


    // Visibility
    visibility: '',
    visibility_unit: 'meters',
    visibility_reason: 'none',

    // Clouds
    total_cloud_cover: '',
    lowest_cloud_base: '',
    low_cloud_amount: '',
    low_cloud_type: '',
    middle_cloud_type: '',
    high_cloud_type: '',
    
    // Advanced Cloud Parameters
    low_cloud_movement: '',
    middle_cloud_movement: '',
    high_cloud_movement: '',
    cloud_development_c: '',
    cloud_development_da: '',
    cloud_development_ec: '',
    cloud_layer_amount: '',
    special_cloud_phenomena: '',

    // Temperatures
    dry_bulb: '',
    wet_bulb: '',
    dew_point: '',
    max_temperature: '',
    min_temperature: '',
    thermograph_reading: '',
    hygrograph_reading: '',

    // Pressure
    station_pressure: '',
    msl_pressure: '',
    pressure_tendency: '',
    pressure_change: '',

    // Weather
    present_weather: '',
    past_weather_1: '',
    past_weather_2: '',
    rainfall: '0.0',
    rain_duration: '',

    // Phenomena
    phenomenon_thunder: false,
    phenomenon_lightning: false,
    phenomenon_hail: false,
    phenomenon_dust_storm: false,
    phenomenon_fog: false,
    phenomenon_mist: false,
    phenomenon_snow: false,

    // Section 333
    sec333_max_temperature: '',
    sec333_min_temperature: '',
    ground_state: '',
    sunshine_hours: '',
    evaporation: '',
    rainfall_24h: '',
  });

  const [formErrors, setFormErrors] = useState({});
  
  // Continuous Temperature Readings State
  const [tempReadings, setTempReadings] = useState([]);
  const [newTempReading, setNewTempReading] = useState('');
  const [tempReadingStats, setTempReadingStats] = useState(null);
  const [tempAutoMode, setTempAutoMode] = useState(false);
  
  // Live Preview State
  const [previewSynop, setPreviewSynop] = useState('');
  const [previewExplanations, setPreviewExplanations] = useState({});
  const [previewDecisionEngine, setPreviewDecisionEngine] = useState({});
  const [previewError, setPreviewError] = useState('');

  // Fetch stations on mount
  useEffect(() => {
    const loadStations = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/stations/');
        if (res.ok) {
          const data = await res.json();
          const activeStations = data.filter(s => s.is_active);
          setStations(activeStations);
          if (activeStations.length > 0) {
            const targetStation = activeStations.find(s => s.station_number === '43279');
            const selectedStation = targetStation || activeStations[0];
            setFormValues(prev => ({ ...prev, station: selectedStation.id.toString() }));
            setStationType(selectedStation.station_type || 'manned');
          }
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingStations(false);
      }
    };
    loadStations();
  }, []);

  // Update station_type when station changes
  useEffect(() => {
    if (formValues.station) {
      const st = stations.find(s => s.id.toString() === formValues.station);
      if (st) {
        setStationType(st.station_type || 'manned');
      }
    }
  }, [formValues.station, stations]);

  // Helper to build numeric fields correctly (convert empty string to null/0 or format values)
  const formatSubmitData = (values) => {
    const formatted = { ...values };
    
    // Convert foreign key ID to integer
    formatted.station = parseInt(values.station);
    
    // ── Legacy SYNOP code fields are preserved in values object ──
    
    // Numeric conversions for floats and integers
    const intFields = [
      'total_cloud_cover', 'low_cloud_amount', 
      'low_cloud_type', 'middle_cloud_type', 'high_cloud_type',
      'low_cloud_movement', 'middle_cloud_movement', 'high_cloud_movement',
      'cloud_development_c', 'cloud_development_da', 'cloud_development_ec',
      'cloud_layer_amount', 'special_cloud_phenomena',
      'pressure_tendency', 'present_weather', 'past_weather_1', 
      'past_weather_2', 'rain_duration', 'ground_state'
    ];

    const floatFields = [
      'wind_speed', 'visibility', 'lowest_cloud_base',

      'dry_bulb', 'wet_bulb', 'dew_point', 'max_temperature', 'min_temperature',
      'thermograph_reading', 'hygrograph_reading',
      'station_pressure', 'msl_pressure', 'pressure_change', 'rainfall',
      'sec333_max_temperature', 'sec333_min_temperature', 'sunshine_hours',
      'evaporation', 'rainfall_24h'
    ];

    intFields.forEach(field => {
      if (values[field] === '' || values[field] === undefined) {
        formatted[field] = null;
      } else {
        formatted[field] = parseInt(values[field]);
      }
    });

    floatFields.forEach(field => {
      if (values[field] === '' || values[field] === undefined) {
        formatted[field] = null;
      } else {
        formatted[field] = parseFloat(values[field]);
      }
    });

    formatted.wind_readings = values.wind_readings.map(r => parseFloat(r));
    // wind_direction is compass string, don't parseFloat it
    formatted.wind_direction = values.compass_direction;

    return formatted;
  };

  // Debounced live SYNOP preview
  useEffect(() => {
    if (!formValues.station) return;
    
    if (!formValues.compass_direction) {
      setPreviewError('Please select a valid wind direction.');
      setPreviewSynop('');
      setPreviewExplanations({});
      setPreviewDecisionEngine({});
      return;
    }

    const controller = new AbortController();
    const delayDebounce = setTimeout(async () => {
      setPreviewError('');
      try {
        const payload = formatSubmitData(formValues);
        const res = await fetch('http://localhost:8000/api/synop/preview/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          signal: controller.signal
        });
        
        const data = await res.json();
        if (res.ok) {
          setPreviewSynop(data.synop);
          setPreviewExplanations(data.explanations || {});
          setPreviewDecisionEngine(data.decision_engine || {});
        } else {
          setPreviewError('Missing or incomplete fields for standard SYNOP encoding');
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error(err);
          setPreviewError('Failed to fetch preview');
        }
      }
    }, 400);

    return () => {
      clearTimeout(delayDebounce);
      controller.abort();
    };
  }, [formValues]);

  // Auto-calculate dew point
  useEffect(() => {
    const { dry_bulb, wet_bulb, station_pressure } = formValues;
    const computedDp = calculateDewPoint(dry_bulb, wet_bulb, station_pressure);
    
    setFormValues(prev => {
      if (prev.dew_point !== computedDp) {
        return { ...prev, dew_point: computedDp };
      }
      return prev;
    });
  }, [formValues.dry_bulb, formValues.wet_bulb, formValues.station_pressure]);

  // ── (Removed) Weather and Rainfall Fields disable hooks ──
  // Handle Cloud Code 9 (Sky obscured)
  useEffect(() => {
    if (formValues.total_cloud_cover === '9') {
      setFormValues(prev => ({
        ...prev,
        low_cloud_amount: '',
        lowest_cloud_base: '',
        low_cloud_type: '/',
        middle_cloud_type: '/',
        high_cloud_type: '/'
      }));
    }
  }, [formValues.total_cloud_cover]);

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormValues(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const [newWindReading, setNewWindReading] = useState('');

  const addWindReading = () => {
    const val = parseFloat(newWindReading);
    if (isNaN(val) || val < 0) return;
    const newReadings = [...formValues.wind_readings, val];
    const avg = (newReadings.reduce((a, b) => a + b, 0) / newReadings.length).toFixed(1);
    setFormValues(prev => ({
      ...prev,
      wind_readings: newReadings,
      wind_speed: avg
    }));
    setNewWindReading('');
  };

  const removeWindReading = (index) => {
    const newReadings = formValues.wind_readings.filter((_, i) => i !== index);
    const avg = newReadings.length > 0 
      ? (newReadings.reduce((a, b) => a + b, 0) / newReadings.length).toFixed(1) 
      : '';
    setFormValues(prev => ({
      ...prev,
      wind_readings: newReadings,
      wind_speed: avg
    }));
  };

  // --- Continuous Temperature Recording Helpers ---
  const addTempReading = () => {
    const val = parseFloat(newTempReading);
    if (isNaN(val) || val < -80.0 || val > 60.0) return;
    const newReadings = [...tempReadings, { temperature: val, time: new Date().toISOString() }];
    setTempReadings(newReadings);
    setNewTempReading('');
    
    const temps = newReadings.map(r => r.temperature);
    const stats = {
      current: temps[temps.length - 1],
      max: Math.max(...temps),
      min: Math.min(...temps),
      count: temps.length
    };
    setTempReadingStats(stats);
    
    // Auto-populate if auto mode is enabled
    if (tempAutoMode) {
      setFormValues(prev => ({
        ...prev,
        dry_bulb: stats.current.toFixed(1),
        max_temperature: stats.max.toFixed(1),
        min_temperature: stats.min.toFixed(1),
      }));
    }
  };

  const removeTempReading = (index) => {
    const newReadings = tempReadings.filter((_, i) => i !== index);
    setTempReadings(newReadings);
    if (newReadings.length > 0) {
      const temps = newReadings.map(r => r.temperature);
      setTempReadingStats({
        current: temps[temps.length - 1],
        max: Math.max(...temps),
        min: Math.min(...temps),
        count: temps.length
      });
    } else {
      setTempReadingStats(null);
    }
  };

  // Client-side SYNOP temperature group calculation (1snTTT)
  const getSynopTempGroup = () => {
    const db = parseFloat(formValues.dry_bulb);
    if (isNaN(db)) return null;
    const sn = db < 0 ? '1' : '0';
    const ttt = String(Math.round(Math.abs(db) * 10)).padStart(3, '0').slice(-3);
    return `1${sn}${ttt}`;
  };

  // Client-side temperature validation
  const getTempValidation = () => {
    const errors = {};
    const warnings = {};
    const db = parseFloat(formValues.dry_bulb);
    const wb = parseFloat(formValues.wet_bulb);
    const maxT = parseFloat(formValues.max_temperature);
    const minT = parseFloat(formValues.min_temperature);

    // Dry bulb range
    if (formValues.dry_bulb !== '' && !isNaN(db)) {
      if (db < -80 || db > 60) errors.dry_bulb = 'Must be between -80.0°C and 60.0°C';
    }

    // Wet bulb range + cross-check
    if (formValues.wet_bulb !== '' && !isNaN(wb)) {
      if (wb < -80 || wb > 60) errors.wet_bulb = 'Must be between -80.0°C and 60.0°C';
      else if (!isNaN(db) && wb > db) errors.wet_bulb = 'Validation Error: Wet Bulb Temperature cannot be greater than Dry Bulb Temperature.';
    }

    // Max/Min range
    if (formValues.max_temperature !== '' && !isNaN(maxT)) {
      if (maxT < -80 || maxT > 60) errors.max_temperature = 'Must be between -80.0°C and 60.0°C';
    }
    if (formValues.min_temperature !== '' && !isNaN(minT)) {
      if (minT < -80 || minT > 60) errors.min_temperature = 'Must be between -80.0°C and 60.0°C';
    }

    // Max >= Min
    if (!isNaN(maxT) && !isNaN(minT) && maxT < minT) {
      errors.max_temperature = 'Maximum temperature must be ≥ minimum temperature.';
    }

    // Current between max/min
    if (!isNaN(db) && !isNaN(maxT) && !isNaN(minT)) {
      if (db > maxT) warnings.max_temperature = 'Current temp exceeds max — verify max thermometer.';
      if (db < minT) warnings.min_temperature = 'Current temp is below min — verify min thermometer.';
    }

    // Thermograph range
    const thermo = parseFloat(formValues.thermograph_reading);
    if (formValues.thermograph_reading !== '' && !isNaN(thermo)) {
      if (thermo < -80 || thermo > 60) errors.thermograph_reading = 'Must be between -80.0°C and 60.0°C';
    }

    // Hygrograph range (0-100%)
    const hygro = parseFloat(formValues.hygrograph_reading);
    if (formValues.hygrograph_reading !== '' && !isNaN(hygro)) {
      if (hygro < 0 || hygro > 100) errors.hygrograph_reading = 'Must be between 0% and 100%';
    }

    return { errors, warnings, valid: Object.keys(errors).length === 0 };
  };

  const tempValidation = getTempValidation();
  const synopTempGroup = getSynopTempGroup();

  const getCloudBaseCode = (m) => {
    if (m === '' || m === null || m === undefined) return '';
    const h = parseFloat(m);
    if (h < 0) return '';
    if (h < 50) return '0';
    if (h < 100) return '1';
    if (h < 200) return '2';
    if (h < 300) return '3';
    if (h < 600) return '4';
    if (h < 1000) return '5';
    if (h < 1500) return '6';
    if (h < 2000) return '7';
    if (h < 2500) return '8';
    return '9';
  };

  const getVisibilityCode = (val, unit) => {
    if (val === '' || val === null || val === undefined) return '';
    const v = parseFloat(val);
    if (v < 0) return '';
    const visM = unit === 'km' ? v * 1000 : v;
    if (visM < 50) return '90';
    if (visM === 50) return '91';
    if (visM === 200) return '92';
    if (visM === 500) return '93';
    if (visM === 1000) return '94';
    if (visM === 2000) return '95';
    if (visM === 4000) return '96';
    if (visM === 10000) return '97';
    if (visM === 20000) return '98';
    if (visM >= 50000) return '99';
    
    const visKm = visM / 1000.0;
    if (visKm < 0.1) return '00';
    if (visKm <= 5.0) return Math.round(visKm * 10).toString().padStart(2, '0');
    if (visKm <= 30.0) return Math.round(visKm + 50).toString();
    if (visKm <= 70.0) return Math.round((visKm - 30) / 5 + 80).toString();
    return '89';
  };

  const handleSave = async (isValidateSave) => {
    setSaving(true);
    let newErrors = {};
    if (formValues.lowest_cloud_base === '') newErrors.lowest_cloud_base = 'Cloud base is required';
    else if (parseFloat(formValues.lowest_cloud_base) < 0) newErrors.lowest_cloud_base = 'Cannot be negative';
    
    if (formValues.visibility === '') newErrors.visibility = 'Visibility is required';
    else if (parseFloat(formValues.visibility) < 0) newErrors.visibility = 'Cannot be negative';

    // No longer validate precipitation_indicator or weather_indicator — derived automatically

    if (Object.keys(newErrors).length > 0) {
      setFormErrors(newErrors);
      setSaving(false);
      setTimeout(() => {
        const errorField = document.querySelector('.field-error');
        if (errorField) errorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 100);
      return;
    }
    setFormErrors({});
    
    if (!formValues.compass_direction) {
      setFormErrors({ wind_direction: 'Please select a valid wind direction.' });
      setSaving(false);
      
      const errorField = document.querySelector('.field-error');
      if (errorField) {
        errorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      return;
    }

    // First obtain the final SYNOP preview string to save it with the observation
    let finalSynop = previewSynop;
    try {
      const payload = formatSubmitData(formValues);
      const previewRes = await fetch('http://localhost:8000/api/synop/preview/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      if (previewRes.ok) {
        const previewData = await previewRes.json();
        finalSynop = previewData.synop;
      }
    } catch (e) {
      console.warn("Could not retrieve final SYNOP preview string", e);
    }

    try {
      const bodyPayload = {
        ...formatSubmitData(formValues),
        is_validated: isValidateSave,
        generated_synop: finalSynop || null
      };

      const res = await fetch('http://localhost:8000/api/observations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(bodyPayload)
      });

      const responseData = await res.json();
      if (!res.ok) {
        const errors = {};
        let engineErrors = [];

        // Check if this is a Validation Engine rejection
        if (responseData.detail && responseData.detail.status === "REJECTED" && responseData.detail.errors_list) {
          engineErrors = responseData.detail.errors_list.map(e => e.error_message);
          errors._engine = engineErrors;
        } 
        // Fallback for standard field errors
        else if (responseData.errors) {
          Object.keys(responseData.errors).forEach(key => {
            errors[key] = Array.isArray(responseData.errors[key]) 
              ? responseData.errors[key].join(', ') 
              : responseData.errors[key];
          });
        } else if (responseData.detail && typeof responseData.detail === 'object' && !Array.isArray(responseData.detail)) {
          Object.keys(responseData.detail).forEach(key => {
             // Handle simple dict details
             if(Array.isArray(responseData.detail[key])) {
                errors[key] = responseData.detail[key].join(', ');
             } else if (typeof responseData.detail[key] === 'string') {
                errors[key] = responseData.detail[key];
             }
          });
        } else {
          errors._engine = [typeof responseData.detail === 'string' ? responseData.detail : "Unknown validation error occurred."];
        }

        setFormErrors(errors);
        
        const firstErrorField = document.querySelector('.field-error');
        if (firstErrorField) {
          firstErrorField.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        alert('Cannot save. Please resolve the validation errors highlighted in red.');
      } else {
        alert(isValidateSave ? 'Observation validated, saved to database, and exported as CSV file!' : 'Draft observation saved successfully.');
        setCurrentPage('observations');
      }
    } catch (err) {
      alert('Network error: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loadingStations) {
    return <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>Loading stations list...</div>;
  }

  // ── Derived values for display ──
  const weatherFieldsDisabled = !['1', '4'].includes(formValues.weather_indicator);
  const rainfallFieldsDisabled = ['3', '4'].includes(formValues.precipitation_indicator);


  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.25rem', marginBottom: '0.25rem' }}>Record Weather Observation</h1>
        <p style={{ color: 'var(--text-muted)' }}>Enter meteorological observations and select appropriate WMO codes</p>
      </div>

      {formErrors._engine && formErrors._engine.length > 0 && (
        <div style={{
          padding: '1.5rem', marginBottom: '2rem', background: 'rgba(239, 68, 68, 0.1)',
          borderLeft: '4px solid var(--color-danger)', borderRadius: '4px'
        }}>
          <h3 style={{ color: 'var(--color-danger)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            Validation Engine Rejected Observation
          </h3>
          <ul style={{ margin: 0, paddingLeft: '1.5rem', color: 'var(--text-muted)' }}>
            {formErrors._engine.map((err, i) => (
              <li key={i} style={{ marginBottom: '0.25rem' }}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="wizard-container">
        {/* Left Form Panel */}
        <div className="glass-card">


          <form onSubmit={(e) => e.preventDefault()}>
            {/* Header Section */}
            <div style={{ paddingBottom: '2rem', borderBottom: '1px solid var(--border-color)', marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: '#fff' }}>Header Info</h2>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
                  <div className="input-group">
                    <label className="input-label">Station</label>
                    <select
                      name="station"
                      className="input-field"
                      value={formValues.station}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      {stations.map(s => (
                        <option key={s.id} value={s.id} style={{ background: '#0f1524' }}>
                          {s.station_number} - {s.station_name}
                        </option>
                      ))}
                    </select>
                    {formErrors.station && <span className="field-error">{formErrors.station}</span>}
                    {/* Station type from settings (read-only indicator) */}
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-primary)', marginTop: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Zap size={12} /> Station Type: <strong>{stationType === 'automatic' ? 'Automatic' : 'Manned'}</strong>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.65rem' }}>(from station settings)</span>
                    </div>
                  </div>

                  <div className="input-group" style={{ display: 'none' }}>
                    <label className="input-label">Observer Name</label>
                    <input
                      type="text"
                      name="observer_name"
                      className="input-field"
                      placeholder="e.g. John Doe"
                      value={formValues.observer_name}
                      onChange={handleInputChange}
                    />
                    {formErrors.observer_name && <span className="field-error">{formErrors.observer_name}</span>}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.25rem' }}>
                  <div className="input-group">
                    <label className="input-label">Observation Date</label>
                    <input
                      type="date"
                      name="observation_date"
                      className="input-field"
                      value={formValues.observation_date}
                      onChange={handleInputChange}
                    />
                    {formErrors.observation_date && <span className="field-error">{formErrors.observation_date}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Observation Time (UTC)</label>
                    <select
                      name="observation_time"
                      className="input-field"
                      value={formValues.observation_time}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="00" style={{ background: '#0f1524' }}>00 UTC</option>
                      <option value="03" style={{ background: '#0f1524' }}>03 UTC</option>
                      <option value="06" style={{ background: '#0f1524' }}>06 UTC</option>
                      <option value="09" style={{ background: '#0f1524' }}>09 UTC</option>
                      <option value="12" style={{ background: '#0f1524' }}>12 UTC</option>
                      <option value="15" style={{ background: '#0f1524' }}>15 UTC</option>
                      <option value="18" style={{ background: '#0f1524' }}>18 UTC</option>
                      <option value="21" style={{ background: '#0f1524' }}>21 UTC</option>
                    </select>
                    {formErrors.observation_time && <span className="field-error">{formErrors.observation_time}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Observation Type</label>
                    <select
                      name="observation_type"
                      className="input-field"
                      value={formValues.observation_type}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="routine" style={{ background: '#0f1524' }}>Routine Synoptic</option>
                      <option value="special" style={{ background: '#0f1524' }}>Special</option>
                    </select>
                  </div>
                </div>
              </div>

            {/* Wind Section */}
            <div style={{ paddingBottom: '2rem', borderBottom: '1px solid var(--border-color)', marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: '#fff' }}>Wind</h2>
                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Wind Velocity & Direction</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
                  <div className="input-group">
                    <label className="input-label">Wind Direction</label>
                    <select
                      name="compass_direction"
                      className="input-field"
                      value={formValues.compass_direction}
                      onChange={(e) => {
                        const val = e.target.value;
                        setFormValues(prev => ({
                          ...prev,
                          compass_direction: val,
                          wind_direction: val
                        }));
                      }}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="" style={{ background: '#0f1524' }}>Select Direction...</option>
                      <option value="N" style={{ background: '#0f1524' }}>North (N)</option>
                      <option value="NNE" style={{ background: '#0f1524' }}>North-Northeast (NNE)</option>
                      <option value="NE" style={{ background: '#0f1524' }}>Northeast (NE)</option>
                      <option value="ENE" style={{ background: '#0f1524' }}>East-Northeast (ENE)</option>
                      <option value="E" style={{ background: '#0f1524' }}>East (E)</option>
                      <option value="ESE" style={{ background: '#0f1524' }}>East-Southeast (ESE)</option>
                      <option value="SE" style={{ background: '#0f1524' }}>Southeast (SE)</option>
                      <option value="SSE" style={{ background: '#0f1524' }}>South-Southeast (SSE)</option>
                      <option value="S" style={{ background: '#0f1524' }}>South (S)</option>
                      <option value="SSW" style={{ background: '#0f1524' }}>South-Southwest (SSW)</option>
                      <option value="SW" style={{ background: '#0f1524' }}>Southwest (SW)</option>
                      <option value="WSW" style={{ background: '#0f1524' }}>West-Southwest (WSW)</option>
                      <option value="W" style={{ background: '#0f1524' }}>West (W)</option>
                      <option value="WNW" style={{ background: '#0f1524' }}>West-Northwest (WNW)</option>
                      <option value="NW" style={{ background: '#0f1524' }}>Northwest (NW)</option>
                      <option value="NNW" style={{ background: '#0f1524' }}>North-Northwest (NNW)</option>
                    </select>
                    {formErrors.wind_direction && <span className="field-error">{formErrors.wind_direction}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Wind Unit</label>
                    <select
                      name="wind_unit"
                      className="input-field"
                      value={formValues.wind_unit}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="knots" style={{ background: '#0f1524' }}>Knots (kt)</option>
                      <option value="mps" style={{ background: '#0f1524' }}>Meters/sec (m/s)</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Wind Speed ({formValues.wind_unit})</label>
                    <input
                      type="number"
                      name="wind_speed"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 12"
                      value={formValues.wind_speed}
                      onChange={handleInputChange}
                      disabled={formValues.wind_readings.length > 0}
                    />
                    {formErrors.wind_speed && <span className="field-error">{formErrors.wind_speed}</span>}
                  </div>
                </div>


                <div style={{ marginBottom: '1.5rem', background: 'rgba(255, 255, 255, 0.02)', padding: '1.25rem', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <label className="input-label">Minute-by-Minute Readings</label>
                  <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                    <input 
                      type="number" 
                      step="0.1"
                      className="input-field" 
                      placeholder="Enter reading" 
                      value={newWindReading}
                      onChange={(e) => setNewWindReading(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addWindReading(); } }}
                      style={{ flex: 1 }}
                    />
                    <button type="button" onClick={addWindReading} className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Plus size={16} /> Add Reading
                    </button>
                  </div>

                  {formValues.wind_readings.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
                      {formValues.wind_readings.map((reading, index) => (
                        <div key={index} style={{ 
                          background: 'rgba(59, 130, 246, 0.2)', 
                          padding: '0.25rem 0.75rem', 
                          borderRadius: '16px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          fontSize: '0.9rem',
                          color: '#bfdbfe'
                        }}>
                          {reading} {formValues.wind_unit}
                          <button type="button" onClick={() => removeWindReading(index)} style={{ background: 'none', border: 'none', color: '#93c5fd', cursor: 'pointer', display: 'flex', padding: 0 }}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="input-group" style={{ maxWidth: '200px' }}>
                    <label className="input-label">Calculated Average</label>
                    <input type="text" className="input-field" value={formValues.wind_speed || '--'} disabled style={{ background: 'rgba(0, 0, 0, 0.2)', color: 'var(--color-primary)', fontWeight: 'bold' }} />
                  </div>
                </div>

                <div style={{ padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                  <h4 style={{ margin: '0 0 0.75rem 0', color: '#93c5fd', fontSize: '0.9rem' }}>Nddff Group Summary (Pre-encode)</h4>
                  <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.9rem' }}>
                    <div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Cloud Amount (N)</div>
                      <div style={{ fontWeight: 'bold' }}>{formValues.total_cloud_cover || '/'}</div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Direction (dd)</div>
                      <div style={{ fontWeight: 'bold' }}>
                        {formValues.compass_direction || '--'} 
                        {formValues.compass_direction && (() => {
                          const ddMap = {
                            'N': '36', 'NNE': '02', 'NE': '05', 'ENE': '07',
                            'E': '09', 'ESE': '11', 'SE': '14', 'SSE': '16',
                            'S': '18', 'SSW': '20', 'SW': '23', 'WSW': '25',
                            'W': '27', 'WNW': '29', 'NW': '32', 'NNW': '34'
                          };
                          return ` (Code ${ddMap[formValues.compass_direction]})`;
                        })()}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Avg Speed (ff)</div>
                      <div style={{ fontWeight: 'bold' }}>
                        {formValues.wind_speed ? String(Math.round(parseFloat(formValues.wind_speed))).padStart(2, '0') : '--'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            {/* Clouds Section */}
            <div style={{ paddingBottom: '2rem', borderBottom: '1px solid var(--border-color)', marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: '#fff' }}>Clouds</h2>
                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Cloud size={20} /> Cloud Cover & Formations
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label">Total Cloud Cover (Oktas)</label>
                    <select
                      name="total_cloud_cover"
                      className="input-field"
                      value={formValues.total_cloud_cover}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="" style={{ background: '#0f1524' }}>Select Cloud Cover...</option>
                      <option value="0" style={{ background: '#0f1524' }}>Clear (0 Oktas)</option>
                      <option value="1" style={{ background: '#0f1524' }}>1 Okta or less</option>
                      <option value="2" style={{ background: '#0f1524' }}>2 Oktas</option>
                      <option value="3" style={{ background: '#0f1524' }}>3 Oktas</option>
                      <option value="4" style={{ background: '#0f1524' }}>4 Oktas</option>
                      <option value="5" style={{ background: '#0f1524' }}>5 Oktas</option>
                      <option value="6" style={{ background: '#0f1524' }}>6 Oktas</option>
                      <option value="7" style={{ background: '#0f1524' }}>7 Oktas (almost overcast)</option>
                      <option value="8" style={{ background: '#0f1524' }}>8 Oktas (Completely Overcast)</option>
                      <option value="9" style={{ background: '#0f1524' }}>Sky Obscured / Cannot Estimate (Code 9)</option>
                      <option value="/" style={{ background: '#0f1524' }}>Missing (/)</option>
                    </select>
                    {formErrors.total_cloud_cover && <span className="field-error">{formErrors.total_cloud_cover}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Lowest Cloud Base (m)</label>
                    <input
                      type="number"
                      name="lowest_cloud_base"
                      className="input-field"
                      placeholder="e.g. 450"
                      value={formValues.lowest_cloud_base}
                      onChange={handleInputChange}
                      disabled={formValues.total_cloud_cover === '9'}
                    />
                    {formValues.lowest_cloud_base !== '' && (
                      <div style={{ fontSize: '0.85rem', color: 'var(--color-primary)', marginTop: '0.2rem' }}>
                        Calculated h = {getCloudBaseCode(formValues.lowest_cloud_base)}
                      </div>
                    )}
                    {formErrors.lowest_cloud_base && <span className="field-error">{formErrors.lowest_cloud_base}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Low Cloud Amount (oktas)</label>
                    <input
                      type="number"
                      name="low_cloud_amount"
                      min="0"
                      max="8"
                      className="input-field"
                      placeholder="e.g. 5"
                      value={formValues.low_cloud_amount}
                      onChange={handleInputChange}
                      disabled={formValues.total_cloud_cover === '9'}
                    />
                    {formErrors.low_cloud_amount && <span className="field-error">{formErrors.low_cloud_amount}</span>}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}><CloudRain size={16} /> Low Cloud Type CL</label>
                    <input
                      type="number"
                      name="low_cloud_type"
                      min="0"
                      max="9"
                      className="input-field"
                      placeholder="e.g. 2"
                      value={formValues.low_cloud_type}
                      onChange={handleInputChange}
                      disabled={formValues.total_cloud_cover === '9'}
                    />
                    {formErrors.low_cloud_type && <span className="field-error">{formErrors.low_cloud_type}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}><Cloud size={16} /> Mid Cloud Type CM</label>
                    <input
                      type="number"
                      name="middle_cloud_type"
                      min="0"
                      max="9"
                      className="input-field"
                      placeholder="e.g. 1"
                      value={formValues.middle_cloud_type}
                      onChange={handleInputChange}
                      disabled={formValues.total_cloud_cover === '9'}
                    />
                    {formErrors.middle_cloud_type && <span className="field-error">{formErrors.middle_cloud_type}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}><CloudLightning size={16} /> High Cloud Type CH</label>
                    <input
                      type="number"
                      name="high_cloud_type"
                      min="0"
                      max="9"
                      className="input-field"
                      placeholder="e.g. 0"
                      value={formValues.high_cloud_type}
                      onChange={handleInputChange}
                      disabled={formValues.total_cloud_cover === '9'}
                    />
                    {formErrors.high_cloud_type && <span className="field-error">{formErrors.high_cloud_type}</span>}
                  </div>
                </div>

                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Cloud Movement (Sec 333 - 6DLDMDH)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label">Low Movement (DL)</label>
                    <input type="number" name="low_cloud_movement" min="0" max="9" className="input-field" placeholder="e.g. 2" value={formValues.low_cloud_movement} onChange={handleInputChange} />
                  </div>
                  <div className="input-group">
                    <label className="input-label">Mid Movement (DM)</label>
                    <input type="number" name="middle_cloud_movement" min="0" max="9" className="input-field" placeholder="e.g. 3" value={formValues.middle_cloud_movement} onChange={handleInputChange} />
                  </div>
                  <div className="input-group">
                    <label className="input-label">High Movement (DH)</label>
                    <input type="number" name="high_cloud_movement" min="0" max="9" className="input-field" placeholder="e.g. 1" value={formValues.high_cloud_movement} onChange={handleInputChange} />
                  </div>
                </div>

                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Cloud Development (Sec 333 - 7CDaec)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label">Cloud Genus (C)</label>
                    <input type="number" name="cloud_development_c" min="0" max="9" className="input-field" placeholder="e.g. 8" value={formValues.cloud_development_c} onChange={handleInputChange} />
                  </div>
                  <div className="input-group">
                    <label className="input-label">Direction (Da)</label>
                    <input type="number" name="cloud_development_da" min="0" max="9" className="input-field" placeholder="e.g. 4" value={formValues.cloud_development_da} onChange={handleInputChange} />
                  </div>
                  <div className="input-group">
                    <label className="input-label">Elevation (ec)</label>
                    <input type="number" name="cloud_development_ec" min="0" max="9" className="input-field" placeholder="e.g. 2" value={formValues.cloud_development_ec} onChange={handleInputChange} />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}><CloudSnow size={16} /> Cloud Layer Amount (Ns)</label>
                    <input type="number" name="cloud_layer_amount" min="0" max="9" className="input-field" placeholder="e.g. 5" value={formValues.cloud_layer_amount} onChange={handleInputChange} />
                  </div>
                  <div className="input-group">
                    <label className="input-label">Special Phenomena (Sp)</label>
                    <input type="number" name="special_cloud_phenomena" min="0" max="9" className="input-field" placeholder="e.g. 2" value={formValues.special_cloud_phenomena} onChange={handleInputChange} />
                  </div>
                </div>
              </div>

            {/* Temperatures & Pressures Section */}
            <div style={{ paddingBottom: '2rem', borderBottom: '1px solid var(--border-color)', marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Thermometer size={22} style={{ color: 'var(--color-primary)' }} /> Temperature Observation
                {/* Validation Status Badge */}
                <span style={{
                  fontSize: '0.7rem', padding: '0.2rem 0.6rem', borderRadius: '12px', fontWeight: 600,
                  background: tempValidation.valid ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                  color: tempValidation.valid ? '#22c55e' : '#ef4444',
                  border: `1px solid ${tempValidation.valid ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
                }}>
                  {tempValidation.valid ? '✓ Valid' : '✗ Errors'}
                </span>
              </h2>

                {/* SYNOP Temperature Group Preview */}
                {synopTempGroup && (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem',
                    padding: '0.75rem 1rem', borderRadius: '8px',
                    background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.2)'
                  }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      SYNOP Temp Group (1snTTT):
                    </span>
                    <code style={{
                      fontFamily: 'monospace', fontSize: '1.1rem', fontWeight: 700,
                      color: 'var(--color-primary)', letterSpacing: '2px'
                    }}>
                      {synopTempGroup}
                    </code>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      = {parseFloat(formValues.dry_bulb) >= 0 ? '+' : ''}{formValues.dry_bulb}°C (Dry Bulb only)
                    </span>
                  </div>
                )}

                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>
                  Temperature Readings (°C)
                </h3>

                {/* Row 1: Dry Bulb (mandatory), Wet Bulb, Dew Point */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      Dry Bulb Temp <span style={{ color: '#ef4444', fontWeight: 700 }}>*</span>
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>(Current Air Temp)</span>
                    </label>
                    <input
                      type="number"
                      name="dry_bulb"
                      step="0.1"
                      min="-80" max="60"
                      className="input-field"
                      placeholder="e.g. 28.3"
                      value={formValues.dry_bulb}
                      onChange={handleInputChange}
                      style={tempValidation.errors.dry_bulb ? { borderColor: '#ef4444', boxShadow: '0 0 0 1px rgba(239,68,68,0.3)' } : {}}
                    />
                    {tempValidation.errors.dry_bulb && <span className="field-error">{tempValidation.errors.dry_bulb}</span>}
                    {formErrors.dry_bulb && <span className="field-error">{formErrors.dry_bulb}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      Wet Bulb Temp
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>(Humidity calc only)</span>
                    </label>
                    <input
                      type="number"
                      name="wet_bulb"
                      step="0.1"
                      min="-80" max="60"
                      className="input-field"
                      placeholder="e.g. 22.1"
                      value={formValues.wet_bulb}
                      onChange={handleInputChange}
                      style={tempValidation.errors.wet_bulb ? { borderColor: '#ef4444', boxShadow: '0 0 0 1px rgba(239,68,68,0.3)' } : {}}
                    />
                    {tempValidation.errors.wet_bulb && <span className="field-error">{tempValidation.errors.wet_bulb}</span>}
                    {formErrors.wet_bulb && <span className="field-error">{formErrors.wet_bulb}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Dew Point (°C)</label>
                    <input
                      type="number"
                      name="dew_point"
                      step="0.1"
                      className="input-field"
                      placeholder="Auto-calculated"
                      value={formValues.dew_point}
                      readOnly
                      style={{ background: 'rgba(0, 0, 0, 0.2)', cursor: 'not-allowed', color: '#888' }}
                    />
                    {formErrors.dew_point && <span className="field-error">{formErrors.dew_point}</span>}
                  </div>
                </div>

                {/* Row 2: Max Temp, Min Temp */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      Maximum Temperature
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>(Today's Max)</span>
                    </label>
                    <input
                      type="number"
                      name="max_temperature"
                      step="0.1"
                      min="-80" max="60"
                      className="input-field"
                      placeholder="e.g. 35.4"
                      value={formValues.max_temperature}
                      onChange={handleInputChange}
                      style={tempValidation.errors.max_temperature ? { borderColor: '#ef4444', boxShadow: '0 0 0 1px rgba(239,68,68,0.3)' } : 
                             tempValidation.warnings.max_temperature ? { borderColor: '#f59e0b', boxShadow: '0 0 0 1px rgba(245,158,11,0.3)' } : {}}
                    />
                    {tempValidation.errors.max_temperature && <span className="field-error">{tempValidation.errors.max_temperature}</span>}
                    {!tempValidation.errors.max_temperature && tempValidation.warnings.max_temperature && (
                      <span style={{ fontSize: '0.75rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.25rem' }}>
                        <AlertTriangle size={12} /> {tempValidation.warnings.max_temperature}
                      </span>
                    )}
                    {formErrors.max_temperature && <span className="field-error">{formErrors.max_temperature}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      Minimum Temperature
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>(Today's Min)</span>
                    </label>
                    <input
                      type="number"
                      name="min_temperature"
                      step="0.1"
                      min="-80" max="60"
                      className="input-field"
                      placeholder="e.g. 21.4"
                      value={formValues.min_temperature}
                      onChange={handleInputChange}
                      style={tempValidation.errors.min_temperature ? { borderColor: '#ef4444', boxShadow: '0 0 0 1px rgba(239,68,68,0.3)' } : 
                             tempValidation.warnings.min_temperature ? { borderColor: '#f59e0b', boxShadow: '0 0 0 1px rgba(245,158,11,0.3)' } : {}}
                    />
                    {tempValidation.errors.min_temperature && <span className="field-error">{tempValidation.errors.min_temperature}</span>}
                    {!tempValidation.errors.min_temperature && tempValidation.warnings.min_temperature && (
                      <span style={{ fontSize: '0.75rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.3rem', marginTop: '0.25rem' }}>
                        <AlertTriangle size={12} /> {tempValidation.warnings.min_temperature}
                      </span>
                    )}
                    {formErrors.min_temperature && <span className="field-error">{formErrors.min_temperature}</span>}
                  </div>
                </div>

                {/* Row 3: Thermograph (Optional), Hygrograph (Optional) */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      Thermograph Reading
                      <span style={{ fontSize: '0.6rem', padding: '0.1rem 0.4rem', borderRadius: '4px', background: 'rgba(99,102,241,0.1)', color: 'var(--color-primary)', fontWeight: 500 }}>Optional</span>
                    </label>
                    <input
                      type="number"
                      name="thermograph_reading"
                      step="0.1"
                      min="-80" max="60"
                      className="input-field"
                      placeholder="Continuous temp trend (°C)"
                      value={formValues.thermograph_reading}
                      onChange={handleInputChange}
                      style={tempValidation.errors.thermograph_reading ? { borderColor: '#ef4444', boxShadow: '0 0 0 1px rgba(239,68,68,0.3)' } : {}}
                    />
                    {tempValidation.errors.thermograph_reading && <span className="field-error">{tempValidation.errors.thermograph_reading}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      Hygrograph Reading (%)
                      <span style={{ fontSize: '0.6rem', padding: '0.1rem 0.4rem', borderRadius: '4px', background: 'rgba(99,102,241,0.1)', color: 'var(--color-primary)', fontWeight: 500 }}>Optional</span>
                    </label>
                    <input
                      type="number"
                      name="hygrograph_reading"
                      step="0.1"
                      min="0" max="100"
                      className="input-field"
                      placeholder="Humidity trend (%)"
                      value={formValues.hygrograph_reading}
                      onChange={handleInputChange}
                      style={tempValidation.errors.hygrograph_reading ? { borderColor: '#ef4444', boxShadow: '0 0 0 1px rgba(239,68,68,0.3)' } : {}}
                    />
                    {tempValidation.errors.hygrograph_reading && <span className="field-error">{tempValidation.errors.hygrograph_reading}</span>}
                  </div>
                </div>

                {/* Continuous Temperature Recording Panel */}
                <div style={{
                  marginBottom: '2rem', padding: '1.25rem', borderRadius: '10px',
                  background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ fontSize: '0.95rem', color: 'var(--color-primary)', margin: 0 }}>
                      📊 Continuous Temperature Recording
                    </h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={tempAutoMode}
                          onChange={(e) => setTempAutoMode(e.target.checked)}
                          style={{ accentColor: 'var(--color-primary)', marginRight: '0.3rem', cursor: 'pointer' }}
                        />
                        Auto-fill Max/Min from readings
                      </label>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
                    <input
                      type="number"
                      step="0.1"
                      min="-80" max="60"
                      className="input-field"
                      placeholder="Enter temperature reading (°C)"
                      value={newTempReading}
                      onChange={(e) => setNewTempReading(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTempReading(); } }}
                      style={{ flex: 1 }}
                    />
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={addTempReading}
                      disabled={!newTempReading || isNaN(parseFloat(newTempReading)) || parseFloat(newTempReading) < -80 || parseFloat(newTempReading) > 60}
                      style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', padding: '0.5rem 1rem', fontSize: '0.8rem' }}
                    >
                      <Plus size={14} /> Add
                    </button>
                  </div>

                  {tempReadings.length > 0 && (
                    <div>
                      {/* Stats Display */}
                      {tempReadingStats && (
                        <div style={{
                          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1rem'
                        }}>
                          <div style={{ padding: '0.6rem', borderRadius: '8px', background: 'rgba(34, 197, 94, 0.08)', border: '1px solid rgba(34, 197, 94, 0.2)', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.65rem', color: '#22c55e', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.2rem' }}>Current</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#22c55e' }}>{tempReadingStats.current.toFixed(1)}°C</div>
                          </div>
                          <div style={{ padding: '0.6rem', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.65rem', color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.2rem' }}>Maximum</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ef4444' }}>{tempReadingStats.max.toFixed(1)}°C</div>
                          </div>
                          <div style={{ padding: '0.6rem', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)', textAlign: 'center' }}>
                            <div style={{ fontSize: '0.65rem', color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.2rem' }}>Minimum</div>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#3b82f6' }}>{tempReadingStats.min.toFixed(1)}°C</div>
                          </div>
                        </div>
                      )}

                      {/* Readings List */}
                      <div style={{ maxHeight: '150px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                        {tempReadings.map((r, i) => (
                          <div key={i} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '0.35rem 0.6rem', borderRadius: '6px',
                            background: 'rgba(255, 255, 255, 0.03)', fontSize: '0.8rem'
                          }}>
                            <span style={{ fontFamily: 'monospace', color: 'var(--text-muted)' }}>
                              #{i + 1}
                            </span>
                            <span style={{ fontWeight: 600, color: '#fff' }}>{r.temperature.toFixed(1)}°C</span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                              {new Date(r.time).toLocaleTimeString()}
                            </span>
                            <button
                              type="button"
                              onClick={() => removeTempReading(i)}
                              style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0.15rem', display: 'flex' }}
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        ))}
                      </div>
                      <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontStyle: 'italic' }}>
                        {tempReadings.length} reading(s) recorded. Current = latest, Max = highest, Min = lowest.
                      </p>
                    </div>
                  )}
                </div>

                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Pressure Readings (hPa)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                  <div className="input-group">
                    <label className="input-label">Station Pressure</label>
                    <input
                      type="number"
                      name="station_pressure"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 1001.2"
                      value={formValues.station_pressure}
                      onChange={handleInputChange}
                    />
                    {formErrors.station_pressure && <span className="field-error">{formErrors.station_pressure}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">MSL Pressure</label>
                    <input
                      type="number"
                      name="msl_pressure"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 1015.6"
                      value={formValues.msl_pressure}
                      onChange={handleInputChange}
                    />
                    {formErrors.msl_pressure && <span className="field-error">{formErrors.msl_pressure}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Tendency Code (0-8)</label>
                    <input
                      type="number"
                      name="pressure_tendency"
                      min="0"
                      max="8"
                      className="input-field"
                      placeholder="e.g. 2"
                      value={formValues.pressure_tendency}
                      onChange={handleInputChange}
                    />
                    {formErrors.pressure_tendency && <span className="field-error">{formErrors.pressure_tendency}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Change (3h hPa)</label>
                    <input
                      type="number"
                      name="pressure_change"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 1.2"
                      value={formValues.pressure_change}
                      onChange={handleInputChange}
                    />
                    {formErrors.pressure_change && <span className="field-error">{formErrors.pressure_change}</span>}
                  </div>
                </div>
              </div>

            {/* ── Weather & Rainfall Section (Redesigned — Observation-Based) ── */}
            <div style={{ paddingBottom: '2rem', borderBottom: '1px solid var(--border-color)', marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: '#fff' }}>Weather & Rainfall</h2>
                
                {/* ── Weather Indicator (iX) ── */}
                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Weather Indicator</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '2rem' }}>
                  <div className="input-group">
                    <label className="input-label">Weather Indicator (iX)</label>
                    <select
                      name="weather_indicator"
                      className="input-field"
                      value={formValues.weather_indicator}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="1" style={{ background: '#0f1524' }}>1 - Manned: Included</option>
                      <option value="2" style={{ background: '#0f1524' }}>2 - Manned: Omitted (no sig. weather)</option>
                      <option value="3" style={{ background: '#0f1524' }}>3 - Manned: Omitted (not observed)</option>
                      <option value="4" style={{ background: '#0f1524' }}>4 - Auto: Included</option>
                      <option value="5" style={{ background: '#0f1524' }}>5 - Auto: Omitted (no sig. weather)</option>
                      <option value="6" style={{ background: '#0f1524' }}>6 - Auto: Omitted (not observed)</option>
                    </select>
                  </div>
                </div>

                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Visibility & Atmospheric State</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginBottom: '2rem' }}>
                  <div className="input-group">
                    <label className="input-label">Visibility Value</label>
                    <input
                      type="number"
                      name="visibility"
                      className="input-field"
                      placeholder="e.g. 5000"
                      value={formValues.visibility}
                      onChange={handleInputChange}
                    />
                    {formValues.visibility !== '' && (
                      <div style={{ fontSize: '0.85rem', color: 'var(--color-primary)', marginTop: '0.2rem' }}>
                        Calculated VV = {getVisibilityCode(formValues.visibility, formValues.visibility_unit)}
                      </div>
                    )}
                    {formErrors.visibility && <span className="field-error">{formErrors.visibility}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Visibility Unit</label>
                    <select
                      name="visibility_unit"
                      className="input-field"
                      value={formValues.visibility_unit}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="meters" style={{ background: '#0f1524' }}>Meters (m)</option>
                      <option value="km" style={{ background: '#0f1524' }}>Kilometers (km)</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Obscuration Reason</label>
                    <select
                      name="visibility_reason"
                      className="input-field"
                      value={formValues.visibility_reason}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="none" style={{ background: '#0f1524' }}>None (Clear)</option>
                      <option value="fog" style={{ background: '#0f1524' }}>Fog</option>
                      <option value="mist" style={{ background: '#0f1524' }}>Mist</option>
                      <option value="smoke" style={{ background: '#0f1524' }}>Smoke</option>
                      <option value="dust" style={{ background: '#0f1524' }}>Dust Storm</option>
                      <option value="rain" style={{ background: '#0f1524' }}>Rain</option>
                      <option value="snow" style={{ background: '#0f1524' }}>Snow</option>
                    </select>
                  </div>
                </div>

                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Present & Past Weather</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginBottom: '2rem' }}>
                  <div className="input-group">
                    <label className="input-label">Present Weather ww (0-99 WMO)</label>
                    <input
                      type="number"
                      name="present_weather"
                      min="0"
                      max="99"
                      className="input-field"
                      placeholder="e.g. 2"
                      value={formValues.present_weather}
                      onChange={handleInputChange}
                      disabled={weatherFieldsDisabled}
                    />
                    {weatherFieldsDisabled && (
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem', fontStyle: 'italic' }}>
                        Disabled — weather not observed
                      </div>
                    )}
                    {formErrors.present_weather && <span className="field-error">{formErrors.present_weather}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Past Weather W1 (0-9 WMO)</label>
                    <input
                      type="number"
                      name="past_weather_1"
                      min="0"
                      max="9"
                      className="input-field"
                      placeholder="e.g. 0"
                      value={formValues.past_weather_1}
                      onChange={handleInputChange}
                      disabled={weatherFieldsDisabled}
                    />
                    {formErrors.past_weather_1 && <span className="field-error">{formErrors.past_weather_1}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Past Weather W2 (0-9 WMO)</label>
                    <input
                      type="number"
                      name="past_weather_2"
                      min="0"
                      max="9"
                      className="input-field"
                      placeholder="e.g. 0"
                      value={formValues.past_weather_2}
                      onChange={handleInputChange}
                      disabled={weatherFieldsDisabled}
                    />
                    {formErrors.past_weather_2 && <span className="field-error">{formErrors.past_weather_2}</span>}
                  </div>
                </div>

                {/* ── Precipitation Indicator (iR) ── */}
                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CloudRain size={18} /> Precipitation Indicator
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.25rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label">Precipitation Indicator (iR)</label>
                    <select
                      name="precipitation_indicator"
                      className="input-field"
                      value={formValues.precipitation_indicator}
                      onChange={handleInputChange}
                      style={{ background: 'rgba(255, 255, 255, 0.05)', color: '#fff' }}
                    >
                      <option value="1" style={{ background: '#0f1524' }}>1 - Included in Section 1</option>
                      <option value="2" style={{ background: '#0f1524' }}>2 - Included in Section 3</option>
                      <option value="3" style={{ background: '#0f1524' }}>3 - Omitted (no precipitation)</option>
                      <option value="4" style={{ background: '#0f1524' }}>4 - Omitted (data unavailable)</option>
                    </select>
                  </div>

                  <div className="input-group">
                    <label className="input-label">Rainfall Amount (mm)</label>
                    <input
                      type="number"
                      name="rainfall"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 2.5"
                      value={formValues.rainfall}
                      onChange={handleInputChange}
                      disabled={rainfallFieldsDisabled}
                    />
                    {rainfallFieldsDisabled && (
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem', fontStyle: 'italic' }}>
                        {formValues.precipitation_indicator === '3' ? 'No precipitation (0.0 mm)' : 'Data not available'}
                      </div>
                    )}
                    {formErrors.rainfall && <span className="field-error">{formErrors.rainfall}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Rainfall Duration (hours)</label>
                    <input
                      type="number"
                      name="rain_duration"
                      className="input-field"
                      placeholder="e.g. 6"
                      value={formValues.rain_duration}
                      onChange={handleInputChange}
                      disabled={rainfallFieldsDisabled}
                    />
                    {formErrors.rain_duration && <span className="field-error">{formErrors.rain_duration}</span>}
                  </div>
                </div>

                <div className="input-group">
                  <label className="input-label" style={{ marginBottom: '0.75rem' }}>Phenomena Checklist</label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
                    {[
                      { name: 'phenomenon_thunder', label: 'Thunderstorm' },
                      { name: 'phenomenon_lightning', label: 'Lightning' },
                      { name: 'phenomenon_hail', label: 'Hail' },
                      { name: 'phenomenon_dust_storm', label: 'Dust Storm' },
                      { name: 'phenomenon_fog', label: 'Fog' },
                      { name: 'phenomenon_mist', label: 'Mist' },
                      { name: 'phenomenon_snow', label: 'Snow' },
                    ].map(p => (
                      <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <input
                          type="checkbox"
                          id={p.name}
                          name={p.name}
                          checked={formValues[p.name]}
                          onChange={handleInputChange}
                          style={{ accentColor: 'var(--color-primary)', cursor: 'pointer' }}
                        />
                        <label htmlFor={p.name} style={{ fontSize: '0.85rem', cursor: 'pointer' }}>{p.label}</label>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

            {/* Section 333 (National Groups) Section */}
            <div style={{ paddingBottom: '2rem', marginBottom: '2rem' }}>
              <h2 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', color: '#fff' }}>Section 333 (National)</h2>
                <h3 style={{ fontSize: '1.05rem', marginBottom: '1rem', color: 'var(--color-primary)' }}>Regional / National Observations</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem', marginBottom: '1.5rem' }}>
                  <div className="input-group">
                    <label className="input-label">24h Max Temp (°C)</label>
                    <input
                      type="number"
                      name="sec333_max_temperature"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 33.4"
                      value={formValues.sec333_max_temperature}
                      onChange={handleInputChange}
                    />
                    {formErrors.sec333_max_temperature && <span className="field-error">{formErrors.sec333_max_temperature}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">24h Min Temp (°C)</label>
                    <input
                      type="number"
                      name="sec333_min_temperature"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 20.8"
                      value={formValues.sec333_min_temperature}
                      onChange={handleInputChange}
                    />
                    {formErrors.sec333_min_temperature && <span className="field-error">{formErrors.sec333_min_temperature}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Ground State (0-9 WMO E)</label>
                    <input
                      type="number"
                      name="ground_state"
                      min="0"
                      max="9"
                      className="input-field"
                      placeholder="e.g. 1"
                      value={formValues.ground_state}
                      onChange={handleInputChange}
                    />
                    {formErrors.ground_state && <span className="field-error">{formErrors.ground_state}</span>}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.25rem' }}>
                  <div className="input-group">
                    <label className="input-label">Sunshine Hours</label>
                    <input
                      type="number"
                      name="sunshine_hours"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 7.5"
                      value={formValues.sunshine_hours}
                      onChange={handleInputChange}
                    />
                    {formErrors.sunshine_hours && <span className="field-error">{formErrors.sunshine_hours}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">Evaporation (mm)</label>
                    <input
                      type="number"
                      name="evaporation"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 4.2"
                      value={formValues.evaporation}
                      onChange={handleInputChange}
                    />
                    {formErrors.evaporation && <span className="field-error">{formErrors.evaporation}</span>}
                  </div>

                  <div className="input-group">
                    <label className="input-label">24h Rainfall (mm)</label>
                    <input
                      type="number"
                      name="rainfall_24h"
                      step="0.1"
                      className="input-field"
                      placeholder="e.g. 1.5"
                      value={formValues.rainfall_24h}
                      onChange={handleInputChange}
                    />
                    {formErrors.rainfall_24h && <span className="field-error">{formErrors.rainfall_24h}</span>}
                  </div>
                </div>
              </div>
          </form>

          {/* Form Actions */}
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '2.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
            <button className="btn btn-secondary" onClick={() => handleSave(false)} disabled={saving} style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
              <Save size={16} /> Save Draft
            </button>
            <button className="btn btn-primary" onClick={() => handleSave(true)} disabled={saving} style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
              <Check size={16} /> Validate & Save
            </button>
          </div>
        </div>

        {/* Right Preview Panel */}
        <div className="live-preview-panel glass-card">
          <div>
            <h3 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Radio size={16} style={{ color: 'var(--color-primary)' }} /> Live SYNOP Preview
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.15rem' }}>Auto-generated FM-12 SYNOP message</p>
          </div>

          {previewError ? (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', color: 'var(--color-warning)', background: 'rgba(245, 158, 11, 0.04)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.15)', fontSize: '0.8rem' }}>
              <HelpCircle size={16} style={{ flexShrink: 0, marginTop: '0.1rem' }} />
              <span>{previewError}</span>
            </div>
          ) : (
            <div>
              <div className="live-preview-code">
                {previewSynop || 'AAXX ...'}
              </div>
              
              {/* Removed IMD Decision Engine Summary */}

              {/* Explanations list */}
              {Object.keys(previewExplanations).length > 0 && (
                <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Group Breakdown</h4>
                  <div style={{ maxHeight: '250px', overflowY: 'auto', paddingRight: '0.25rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {Object.entries(previewExplanations).map(([group, desc]) => (
                      <div key={group} style={{ display: 'flex', gap: '0.5rem', fontSize: '0.8rem', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '0.4rem' }}>
                        <strong style={{ color: 'var(--color-primary)', fontFamily: 'monospace', minWidth: '45px' }}>{group}</strong>
                        <span style={{ color: 'var(--text-muted)' }}>{desc}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
