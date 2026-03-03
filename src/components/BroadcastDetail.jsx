import React from 'react';

// CSS import (production):
// import './styles/broadcasts.css';

// ============================================
// Icons
// ============================================
const Icons = {
  ArrowLeft: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
  ),
  Copy: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
  ),
  Download: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
  ),
  Image: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>
  ),
  WhatsApp: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg>
  ),
  InfoSmall: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
  ),
};

// ============================================
// Funnel stage colors (used for border-top on cards and funnel bar)
// ============================================
const METRIC_COLORS = {
  sent: 'var(--color-info)',
  delivered: '#25D366',
  read: 'var(--color-primary)',
  replied: '#059669',
  failed: 'var(--color-danger)',
};

/**
 * BroadcastDetail — Analytics page for a sent broadcast.
 *
 * Props:
 *   broadcast — the broadcast data object
 *   onNavigate(view) — routes back to 'list'
 *
 * Renders:
 *   - Header with campaign name, status pill, subtle "Back to list" link, Duplicate/Export buttons
 *   - 5 analytics cards with colored top borders
 *   - Delivery funnel horizontal bar with legend
 *   - Two-column: campaign details table + WhatsApp message preview
 *
 * Note: Analytics data will come from Meta webhook aggregations in production.
 *       Read metric includes tooltip about potential undercounting.
 */
const BroadcastDetail = ({ broadcast, onNavigate }) => {
  // In production, these come from broadcast prop + API
  const metrics = broadcast?.metrics || [];
  const funnel = broadcast?.funnel || [];
  const details = broadcast?.details || {};
  const messagePreview = broadcast?.messagePreview || {};

  return (
    <div id="page-broadcasts-detail">
      {/* Header */}
      <div className="detail-header">
        <div>
          <div className="detail-header__title-row">
            <h1 className="detail-header__name">{broadcast?.name || 'Broadcast'}</h1>
            <span className="status-pill status-pill--sent">Sent</span>
            <button className="detail-header__back" onClick={() => onNavigate('list')}>
              <Icons.ArrowLeft /> Back to list
            </button>
          </div>
          <div className="detail-header__meta">
            Template: {details.template} · Sent {details.sentAt} · Audience: {details.audience}
          </div>
        </div>
        <div className="detail-header__actions">
          <button className="btn btn-secondary btn-sm">
            <Icons.Copy /> Duplicate
          </button>
          <button className="btn btn-secondary btn-sm">
            <Icons.Download /> Export
          </button>
        </div>
      </div>

      {/* Analytics cards */}
      <div className="analytics-grid">
        {metrics.map((m, i) => (
          <div
            key={i}
            className="analytics-card"
            style={{ borderTopColor: m.color }}
          >
            <div className="analytics-card__label">
              {m.label}
              {m.tooltip && (
                <span className="analytics-card__info" title={m.tooltip}>
                  <Icons.InfoSmall />
                </span>
              )}
            </div>
            <div className="analytics-card__value">{m.value}</div>
            {m.pct && (
              <div className="analytics-card__pct" style={{ color: m.color }}>
                {m.pct}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Delivery funnel */}
      <div className="funnel-card">
        <div className="funnel-card__title">Delivery Funnel</div>
        <div className="funnel-bar">
          {funnel.map((s, i) => (
            <div
              key={i}
              className="funnel-bar__segment"
              style={{ flex: s.flex, background: s.color, minWidth: s.flex > 5 ? 0 : 20 }}
            >
              {s.flex > 12 && s.label}
            </div>
          ))}
        </div>
        <div className="funnel-legend">
          {funnel.map((s, i) => (
            <div key={i} className="funnel-legend__item">
              <div className="funnel-legend__dot" style={{ background: s.color }} />
              <span className="funnel-legend__label">{s.label}</span>
              <span className="funnel-legend__count">({s.count.toLocaleString()})</span>
            </div>
          ))}
        </div>
      </div>

      {/* Two-column detail */}
      <div className="detail-columns">
        {/* Campaign details */}
        <div className="detail-section">
          <div className="detail-section__title">Campaign Details</div>
          <div className="detail-table">
            <div className="detail-table__row">
              <div className="detail-table__label">Template</div>
              <div className="detail-table__value">
                <span style={{ color: 'var(--color-whatsapp)' }}><Icons.WhatsApp /></span>
                {details.template}
              </div>
            </div>
            <div className="detail-table__row">
              <div className="detail-table__label">Category</div>
              <div className="detail-table__value">
                <span className={`template-preview__category template-preview__category--${(details.category || '').toLowerCase()}`}>
                  {details.category}
                </span>
              </div>
            </div>
            <div className="detail-table__row">
              <div className="detail-table__label">Audience</div>
              <div className="detail-table__value">
                {details.audience} ({details.audienceCount?.toLocaleString()} contacts)
              </div>
            </div>
            <div className="detail-table__row">
              <div className="detail-table__label">Sent At</div>
              <div className="detail-table__value">{details.sentAt}</div>
            </div>
            <div className="detail-table__row">
              <div className="detail-table__label">Actual Cost</div>
              <div className="detail-table__value detail-table__value--bold">{details.actualCost}</div>
            </div>
          </div>
        </div>

        {/* WhatsApp preview */}
        <div className="detail-section">
          <div className="detail-section__title">Message Preview</div>
          <div className="wa-preview">
            <div className="wa-preview__bubble">
              {messagePreview.hasImage && (
                <div className="wa-preview__bubble-image">
                  <Icons.Image /> Header Image
                </div>
              )}
              <div className="wa-preview__bubble-body">
                {messagePreview.body || 'No preview available'}
                <div className="wa-preview__bubble-time">
                  {messagePreview.time || '—'} ✓✓
                </div>
              </div>
              {messagePreview.buttons?.map((btn, i) => (
                <div key={i} className="wa-preview__bubble-btn">{btn}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BroadcastDetail;
