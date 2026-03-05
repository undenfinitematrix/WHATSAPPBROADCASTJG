import React, { useState, useRef, useEffect, useCallback } from 'react';

// API helper – the front‑end service layer that wraps our FastAPI backend
import { broadcastsApi as api } from '../api-client';

// CSS import (production):
// import './styles/broadcasts.css';

// ============================================
// Icons
// ============================================
const Icons = {
  ArrowRight: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
  ),
  ArrowLeft: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
  ),
  Check: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
  ),
  Info: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
  ),
  Warning: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
  ),
  Bolt: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
  ),
  Clock: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
  ),
  Users: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>
  ),
  Tag: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
  ),
  Upload: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
  ),
  Image: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
  ),
  ChevronDown: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
  ),
  WhatsApp: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg>
  ),
  File: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
  ),
};

// ============================================
// Shared hook: click outside
// ============================================
function useClickOutside(ref, handler) {
  useEffect(() => {
    const listener = (e) => {
      if (ref.current && !ref.current.contains(e.target)) handler();
    };
    document.addEventListener('mousedown', listener);
    return () => document.removeEventListener('mousedown', listener);
  }, [ref, handler]);
}

// ============================================
// Sub-components
// ============================================

/** Callout box — info or warning */
const Callout = ({ type = 'info', children }) => (
  <div className={`callout callout--${type}`}>
    <span className="callout__icon">
      {type === 'warning' ? <Icons.Warning /> : <Icons.Info />}
    </span>
    <div>{children}</div>
  </div>
);

/** Step descriptions */
const STEP_DESCRIPTIONS = {
  1: 'Choose from your approved WhatsApp templates and name your campaign.',
  2: 'Select who should receive this broadcast. Only opted-in contacts will be included.',
  3: 'Choose to send immediately or schedule for a specific date and time.',
  4: 'Double-check everything before sending. This action cannot be undone.',
};

/** Step definitions */
const STEP_DEFS = [
  { num: 1, label: 'Select Template' },
  { num: 2, label: 'Choose Audience' },
  { num: 3, label: 'Schedule' },
  { num: 4, label: 'Review & Send' },
];

// ============================================
// Step 1: Select Template
// ============================================
const StepSelectTemplate = ({ data, setData, templates }) => {
  const selectedTemplate = templates.find((tp) => tp.id === data.template);

  return (
    <>
      <div className="form-group">
        <label className="form-label">Campaign Name</label>
        <input
          type="text"
          className="form-input"
          placeholder="e.g., Valentine's Day Sale"
          value={data.campaignName}
          onChange={(e) => setData({ ...data, campaignName: e.target.value })}
        />
      </div>

      <div className="form-group">
        <label className="form-label">
          Template <span className="form-label__hint">· Approved templates from Meta</span>
        </label>
        <select
          className="form-input"
          value={data.template}
          onChange={(e) => setData({ ...data, template: e.target.value })}
        >
          <option value="">Select a template...</option>
          {templates.map((tp) => (
            <option key={tp.id} value={tp.id}>
              {tp.id} — {tp.cat} · {tp.lang} · {tp.media} · {tp.buttons} button{tp.buttons > 1 ? 's' : ''}
            </option>
          ))}
        </select>
      </div>

      {selectedTemplate && (
        <div className="template-preview">
          <div className="template-preview__meta">
            <span className={`template-preview__category template-preview__category--${selectedTemplate.cat.toLowerCase()}`}>
              {selectedTemplate.cat}
            </span>
            <span className="template-preview__detail">{selectedTemplate.lang}</span>
            <span className="template-preview__detail">
              <Icons.Image /> {selectedTemplate.media} · {selectedTemplate.buttons} button{selectedTemplate.buttons > 1 ? 's' : ''}
            </span>
          </div>
          <div className="template-preview__body">{selectedTemplate.body}</div>
        </div>
      )}

      <Callout type="info">
        Don't see your template? Make sure it's approved in <strong>Meta Business Manager</strong>, then reload this page.
      </Callout>
    </>
  );
};

// ============================================
// Step 2: Choose Audience
// ============================================
const AUDIENCE_OPTIONS = [
  { id: 'all', icon: <Icons.Users />, iconClass: 'primary', title: 'All Subscribers', desc: 'Send to everyone who has opted in to receive WhatsApp messages', count: '2,431 contacts' },
  { id: 'segment', icon: <Icons.Tag />, iconClass: 'purple', title: 'By Segment', desc: 'Target specific customer segments like VIP, new customers, or repeat buyers', count: '6 segments' },
  { id: 'csv', icon: <Icons.Upload />, iconClass: 'info', title: 'Upload CSV', desc: 'Upload a list of phone numbers in international format (+country code)', count: null },
];

const StepChooseAudience = ({ data, setData, segments, csvUploadState, onCSVUpload, onCSVRemove, csvInputRef }) => (
  <>
    <div className="audience-options">
      {AUDIENCE_OPTIONS.map((o) => (
        <button
          key={o.id}
          className={`audience-option ${data.audience === o.id ? 'audience-option--selected' : ''}`}
          onClick={() => {
            setData({ ...data, audience: o.id });
            if (o.id !== 'csv' && onCSVRemove) onCSVRemove();
          }}
        >
          <div className={`audience-option__icon audience-option__icon--${o.iconClass}`}>
            {o.icon}
          </div>
          <div style={{ flex: 1 }}>
            <div className="audience-option__title">{o.title}</div>
            <div className="audience-option__desc">{o.desc}</div>
          </div>
          {o.count && <div className="audience-option__count">{o.count}</div>}
        </button>
      ))}
    </div>

    {data.audience === 'segment' && (
      <div className="audience-segment-picker">
        <label className="form-label">Select Segment</label>
        <select
          className="form-input"
          value={data.segment || ''}
          onChange={(e) => setData({ ...data, segment: e.target.value })}
        >
          <option value="">Choose a segment...</option>
          {segments.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label} ({s.count.toLocaleString()})
            </option>
          ))}
        </select>
      </div>
    )}

    {data.audience === 'csv' && (
      <>
        <input
          type="file"
          accept=".csv"
          ref={csvInputRef}
          style={{ display: 'none' }}
          onChange={(e) => onCSVUpload(e.target.files[0])}
        />

        {/* State: No file uploaded yet */}
        {!csvUploadState.uploading && !csvUploadState.result && !csvUploadState.error && (
          <div className="csv-upload" onClick={() => csvInputRef.current?.click()} style={{ cursor: 'pointer' }}>
            <div style={{ color: 'var(--color-gray-400)', marginBottom: 8, display: 'flex', justifyContent: 'center' }}>
              <Icons.File />
            </div>
            <div className="csv-upload__title">Click to browse and upload a CSV file</div>
            <div className="csv-upload__desc">CSV must contain a column with phone numbers in international format (+country code)</div>
          </div>
        )}

        {/* State: Uploading */}
        {csvUploadState.uploading && (
          <div className="csv-upload" style={{ pointerEvents: 'none', opacity: 0.7 }}>
            <div style={{ color: 'var(--color-gray-400)', marginBottom: 8, display: 'flex', justifyContent: 'center' }}>
              <Icons.File />
            </div>
            <div className="csv-upload__title">Uploading {csvUploadState.fileName}...</div>
            <div className="csv-upload__desc">Validating phone numbers, please wait</div>
          </div>
        )}

        {/* State: Upload success */}
        {csvUploadState.result && (
          <div className="csv-upload" style={{ borderStyle: 'solid', borderColor: 'var(--color-accent, #e91e8c)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Icons.File />
                <span style={{ fontWeight: 600 }}>{csvUploadState.fileName}</span>
              </div>
              <button
                type="button"
                onClick={onCSVRemove}
                style={{ background: 'none', border: 'none', color: 'var(--color-gray-400)', cursor: 'pointer', fontSize: 14, textDecoration: 'underline' }}
              >
                Remove
              </button>
            </div>
            <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginBottom: 8 }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700 }}>{csvUploadState.result.valid_phones}</div>
                <div className="csv-upload__desc">Valid</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: csvUploadState.result.invalid_phones > 0 ? '#e67e22' : 'var(--color-gray-400)' }}>
                  {csvUploadState.result.invalid_phones}
                </div>
                <div className="csv-upload__desc">Invalid</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-gray-400)' }}>{csvUploadState.result.duplicate_phones}</div>
                <div className="csv-upload__desc">Duplicates</div>
              </div>
            </div>
            {csvUploadState.result.errors.length > 0 && (
              <div style={{ marginTop: 8, textAlign: 'left', fontSize: 13, color: '#e67e22' }}>
                {csvUploadState.result.errors.map((err, i) => (
                  <div key={i}>{err}</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* State: Upload error */}
        {csvUploadState.error && !csvUploadState.uploading && (
          <div className="csv-upload" onClick={() => csvInputRef.current?.click()} style={{ cursor: 'pointer', borderColor: '#e67e22' }}>
            <div style={{ color: '#e67e22', marginBottom: 8, display: 'flex', justifyContent: 'center' }}>
              <Icons.Warning />
            </div>
            <div className="csv-upload__title" style={{ color: '#e67e22' }}>{csvUploadState.error}</div>
            <div className="csv-upload__desc">Click to try again</div>
          </div>
        )}
      </>
    )}

    <Callout type="warning">
      <strong>Opt-in required.</strong> Only contacts who have explicitly opted in to WhatsApp marketing messages will receive this broadcast. Non-opted-in contacts will be automatically excluded.
    </Callout>
  </>
);

// ============================================
// Step 3: Schedule
// ============================================
const StepSchedule = ({ data, setData, timezones }) => (
  <>
    <div className="schedule-options">
      {[
        { id: 'now', icon: <Icons.Bolt />, label: 'Send Now', desc: 'Broadcast will be sent immediately' },
        { id: 'schedule', icon: <Icons.Clock />, label: 'Schedule', desc: 'Pick a date and time' },
      ].map((o) => (
        <button
          key={o.id}
          className={`schedule-option ${data.scheduleType === o.id ? 'schedule-option--selected' : ''}`}
          onClick={() => setData({ ...data, scheduleType: o.id })}
        >
          <div className="schedule-option__icon">{o.icon}</div>
          <div className="schedule-option__label">{o.label}</div>
          <div className="schedule-option__desc">{o.desc}</div>
        </button>
      ))}
    </div>

    {data.scheduleType === 'schedule' && (
      <div className="schedule-datetime">
        <div>
          <label className="form-label">Date</label>
          <input
            type="date"
            className="form-input"
            value={data.scheduleDate || ''}
            onChange={(e) => setData({ ...data, scheduleDate: e.target.value })}
          />
        </div>
        <div>
          <label className="form-label">Time</label>
          <input
            type="time"
            className="form-input"
            value={data.scheduleTime || ''}
            onChange={(e) => setData({ ...data, scheduleTime: e.target.value })}
          />
        </div>
        <div>
          <label className="form-label">Timezone</label>
          <select
            className="form-input"
            value={data.timezone || ''}
            onChange={(e) => setData({ ...data, timezone: e.target.value })}
          >
            {timezones.map((tz) => (
              <option key={tz} value={tz}>{tz}</option>
            ))}
          </select>
        </div>
      </div>
    )}

    <Callout type="info">
      <strong>Tip:</strong> WhatsApp messages have highest open rates between 9–11 AM and 5–7 PM in your audience's local time.
    </Callout>
  </>
);

// ============================================
// Step 4: Review & Send
// ============================================
const StepReview = ({ data, templates, segments, csvUploadState }) => {
  const tpl = templates.find((tp) => tp.id === data.template);
  const audLabel =
    data.audience === 'all'
      ? 'All Subscribers · 2,431 contacts'
      : data.audience === 'segment'
        ? `By Segment · ${segments.find((s) => s.id === data.segment)?.label || 'None selected'}`
        : data.audience === 'csv' && csvUploadState?.result
          ? `Upload CSV · ${csvUploadState.result.valid_phones} valid contacts`
          : 'Upload CSV';
  const schedLabel =
    data.scheduleType === 'now'
      ? 'Send immediately'
      : `${data.scheduleDate || '—'} at ${data.scheduleTime || '—'} ${(data.timezone || '').split('(')[1]?.replace(')', '') || ''}`;

  return (
    <div className="review-layout">
      <div>
        {/* Summary table */}
        <div className="review-summary">
          <div className="review-row">
            <div className="review-row__label">Campaign</div>
            <div className="review-row__value">{data.campaignName || 'Untitled'}</div>
          </div>
          <div className="review-row">
            <div className="review-row__label">Template</div>
            <div className="review-row__value">
              <span style={{ color: 'var(--color-whatsapp)' }}><Icons.WhatsApp /></span>
              {data.template || 'None'}
            </div>
          </div>
          <div className="review-row">
            <div className="review-row__label">Audience</div>
            <div className="review-row__value">{audLabel}</div>
          </div>
          <div className="review-row">
            <div className="review-row__label">Schedule</div>
            <div className="review-row__value">{schedLabel}</div>
          </div>
        </div>

        {/* Cost estimate */}
        <div className="cost-estimate">
          <div>
            <div className="cost-estimate__label">Estimated cost</div>
            <div className="cost-estimate__note">Based on Meta per-message pricing (marketing category)</div>
          </div>
          <div className="cost-estimate__value">~$121.55</div>
        </div>

        <Callout type="warning">
          Charges are billed directly by Meta to your WhatsApp Business account. AeroChat does not add any markup.
        </Callout>
      </div>

      {/* WhatsApp preview */}
      <div>
        <div className="wa-preview__label">Message Preview</div>
        <div className="wa-preview">
          <div className="wa-preview__bubble">
            {tpl?.media?.includes('Image') && (
              <div className="wa-preview__bubble-image">
                <Icons.Image /> Header Image
              </div>
            )}
            <div className="wa-preview__bubble-body">
              {tpl
                ? tpl.body.replace(/\{\{(\d+)\}\}/g, (_, n) => {
                    const vars = ['customer_name', 'collection_name', 'discount_code'];
                    return `{{${vars[parseInt(n) - 1] || `var${n}`}}}`;
                  })
                : 'Select a template to preview'}
              <div className="wa-preview__bubble-time">9:00 AM ✓✓</div>
            </div>
            {tpl && (
              <div className="wa-preview__bubble-btn">🛍️ Shop Now</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// Main Component
// ============================================

/**
 * BroadcastWizard — 4-step wizard for creating WhatsApp broadcasts.
 *
 * Props:
 *   onNavigate(view, data?) — routes back to 'list' or forward to 'detail'.
 *   templates — array of approved Meta templates (fetched via API).
 *   segments — array of audience segments.
 *   timezones — array of timezone strings.
 *   defaultTimezone — pre-populated from store settings.
 *
 * Steps:
 *   1. Select Template — campaign name + template dropdown + preview
 *   2. Choose Audience — All / By Segment / Upload CSV (no radio buttons)
 *   3. Schedule — Send Now or Schedule with date/time/timezone
 *   4. Review & Send — summary, cost estimate, WhatsApp message preview
 *
 * Features:
 *   - "Save as Draft" button persistent top-right on all steps
 *   - Clickable sidebar steps (completed + active, not future)
 *   - "Back to list" link at bottom of sidebar
 *   - No Cancel button (redundant with Back to list)
 *   - Pink accent for all selection states
 *   - Cream (#fefcfa) background for template preview + WhatsApp preview
 */
const BroadcastWizard = ({ onNavigate, templates = [], segments = [], timezones = [], defaultTimezone = '' }) => {
  const [step, setStep] = useState(1);
  const [data, setData] = useState({
    campaignName: '',
    template: '',
    audience: 'all',
    segment: '',
    scheduleType: 'now',
    scheduleDate: '',
    scheduleTime: '',
    timezone: defaultTimezone || timezones[0] || '',
  });
  const [csvUploadState, setCsvUploadState] = useState({
    uploading: false, result: null, error: null, fileName: null,
  });
  const csvInputRef = useRef(null);

  const handleSaveDraft = async () => {
    // save current data state as draft via API
    try {
      // convert state to API payload shape if needed
      const payload = {
        campaign_name: data.campaignName,
        template_name: data.template,
        template_language: 'en',
        schedule_type: data.scheduleType,
        scheduled_at:
          data.scheduleType === 'scheduled'
            ? `${data.scheduleDate}T${data.scheduleTime}`
            : null,
        timezone: data.timezone,
        audience_type: data.audience,
        segment_id: data.segment || null,
        csv_file_id: csvUploadState.result?.file_id || null,
      };
      console.log('sending payload', payload);
      const result = await api.createBroadcast(payload);
      console.log('draft saved', result);
    } catch (err) {
      console.error('failed to save draft', err, 'detail:', err.detail);
    }
    onNavigate('list');
  };

  const handleCSVUpload = async (file) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setCsvUploadState({ uploading: false, result: null, error: 'Please select a CSV file.', fileName: null });
      return;
    }
    setCsvUploadState({ uploading: true, result: null, error: null, fileName: file.name });
    try {
      const result = await api.uploadCSV(file);
      setCsvUploadState({ uploading: false, result, error: null, fileName: file.name });
    } catch (err) {
      setCsvUploadState({ uploading: false, result: null, error: err.detail || err.message || 'Failed to upload CSV.', fileName: file.name });
    }
  };

  const handleCSVRemove = () => {
    setCsvUploadState({ uploading: false, result: null, error: null, fileName: null });
    if (csvInputRef.current) csvInputRef.current.value = '';
  };

  const handleSubmit = () => {
    // In production: dispatch broadcast via API
    onNavigate('list');
  };

  return (
    <div id="page-broadcasts-wizard">
      <div className="wizard-layout">
        {/* Sidebar step indicator */}
        <div className="wizard-sidebar">
          <div className="wizard-sidebar__inner">
            {STEP_DEFS.map((s, i) => {
              const done = step > s.num;
              const active = step === s.num;
              const clickable = done || active;

              return (
                <div
                  key={s.num}
                  className={`wizard-step ${done ? 'wizard-step--done' : ''} ${active ? 'wizard-step--active' : ''} ${clickable ? 'wizard-step--clickable' : ''}`}
                  onClick={() => { if (clickable) setStep(s.num); }}
                >
                  <div className="wizard-step__indicator">
                    <div className="wizard-step__circle">
                      {done ? <Icons.Check /> : s.num}
                    </div>
                    {i < STEP_DEFS.length - 1 && <div className="wizard-step__line" />}
                  </div>
                  <div className="wizard-step__label">{s.label}</div>
                </div>
              );
            })}

            <div className="wizard-sidebar__back">
              <button className="wizard-sidebar__back-link" onClick={() => onNavigate('list')}>
                <Icons.ArrowLeft /> Back to list
              </button>
            </div>
          </div>
        </div>

        {/* Content area */}
        <div className="wizard-content">
          {/* Header: title + Save as Draft */}
          <div className="wizard-content__header">
            <h2 className="wizard-content__title">{STEP_DEFS[step - 1].label}</h2>
            <button className="wizard-content__draft-btn" onClick={handleSaveDraft}>
              Save as Draft
            </button>
          </div>

          {/* Card */}
          <div className="wizard-card">
            <div className="wizard-card__desc">{STEP_DESCRIPTIONS[step]}</div>

            {step === 1 && <StepSelectTemplate data={data} setData={setData} templates={templates} />}
            {step === 2 && <StepChooseAudience data={data} setData={setData} segments={segments} csvUploadState={csvUploadState} onCSVUpload={handleCSVUpload} onCSVRemove={handleCSVRemove} csvInputRef={csvInputRef} />}
            {step === 3 && <StepSchedule data={data} setData={setData} timezones={timezones} />}
            {step === 4 && <StepReview data={data} templates={templates} segments={segments} csvUploadState={csvUploadState} />}
          </div>

          {/* Footer navigation */}
          <div className="wizard-footer">
            {step > 1 && (
              <button className="btn btn-secondary" onClick={() => setStep(step - 1)}>
                <Icons.ArrowLeft /> Back
              </button>
            )}
            {step < 4 && (
              <button className="btn btn-accent" onClick={() => setStep(step + 1)}>
                Continue <Icons.ArrowRight />
              </button>
            )}
            {step === 4 && (
              <button className="btn btn-accent" onClick={handleSubmit}>
                <Icons.Clock /> {data.scheduleType === 'now' ? 'Send Broadcast' : 'Schedule Broadcast'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BroadcastWizard;
