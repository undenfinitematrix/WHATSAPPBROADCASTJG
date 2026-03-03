import React, { useState, useRef, useEffect, useCallback } from 'react';

// CSS import (production):
// import './styles/broadcasts.css';

// ============================================
// Icons
// ============================================
const Icons = {
  Search: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
  ),
  Plus: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
  ),
  Info: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
  ),
  InfoSmall: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
  ),
  Close: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
  ),
  ExternalLink: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3"/></svg>
  ),
  MoreVertical: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
  ),
  Bolt: () => (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"/></svg>
  ),
  ChevronLeft: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
  ),
  ChevronRight: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
  ),
  ChevronDown: () => (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9"/></svg>
  ),
};

// ============================================
// Sample Data
// ============================================
const sampleBroadcasts = [
  { id: 1, name: "Valentine's Day Sale", template: 'valentines_promo_2025', status: 'sent', audience: 'All Subscribers', delivered: 2341, deliveredPct: 96.2, read: 1687, readPct: 72.1, sentAt: 'Feb 12, 10:00 AM' },
  { id: 2, name: 'New Arrivals — Spring Collection', template: 'new_arrivals_notify', status: 'scheduled', audience: 'VIP Customers', delivered: null, deliveredPct: null, read: null, readPct: null, sentAt: 'Feb 25, 9:00 AM' },
  { id: 3, name: 'Abandoned Cart Reminder', template: 'cart_reminder_v2', status: 'sent', audience: 'Cart Abandoners', delivered: 847, deliveredPct: 93.8, read: 612, readPct: 72.3, sentAt: 'Feb 8, 2:30 PM' },
  { id: 4, name: 'Weekend Flash Sale', template: 'flash_sale_announce', status: 'draft', audience: null, delivered: null, deliveredPct: null, read: null, readPct: null, sentAt: null },
  { id: 5, name: 'Loyalty Points Update', template: 'loyalty_update_q1', status: 'sent', audience: 'Loyalty Members', delivered: 1203, deliveredPct: 95.1, read: 891, readPct: 74.1, sentAt: 'Feb 1, 11:00 AM' },
];

const filters = [
  { id: 'all', label: 'All' },
  { id: 'sent', label: 'Sent' },
  { id: 'scheduled', label: 'Scheduled' },
  { id: 'draft', label: 'Draft' },
];

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

/** Status pill — colored background, no dot */
const StatusPill = ({ status }) => {
  const labels = { sent: 'Sent', scheduled: 'Scheduled', draft: 'Draft', sending: 'Sending' };
  return (
    <span className={`status-pill status-pill--${status}`}>
      {labels[status] || status}
    </span>
  );
};

/** Metric cell — value + percentage */
const MetricCell = ({ value, pct }) => (
  <td className="metric-cell">
    <div className="metric-cell__value">{value != null ? value.toLocaleString() : '—'}</div>
    {pct != null && <div className="metric-cell__pct">{pct}%</div>}
  </td>
);

/** 3-dot action menu — context-specific actions per status */
const ActionMenu = ({ status }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const close = useCallback(() => setOpen(false), []);
  useClickOutside(ref, close);

  const items = [];
  if (status === 'sent') {
    items.push({ label: 'View Analytics' }, { label: 'Duplicate' });
  }
  if (status === 'scheduled') {
    items.push({ label: 'Edit' }, { label: 'Cancel', danger: true });
  }
  if (status === 'draft') {
    items.push({ label: 'Edit' }, { label: 'Delete', danger: true });
  }

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        className={`action-trigger ${open ? 'action-trigger--open' : ''}`}
        onClick={(e) => { e.stopPropagation(); setOpen(!open); }}
      >
        <Icons.MoreVertical />
      </button>
      {open && (
        <div className="action-dropdown">
          {items.map((it, i) => (
            <button
              key={i}
              className={`action-dropdown__item ${it.danger ? 'action-dropdown__item--danger' : ''}`}
              onClick={(e) => { e.stopPropagation(); setOpen(false); }}
            >
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

/** Custom rows-per-page dropdown */
const RowsDropdown = ({ value, onChange }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const close = useCallback(() => setOpen(false), []);
  useClickOutside(ref, close);
  const opts = [25, 50, 100];

  return (
    <div ref={ref} className="rows-dropdown">
      <button className="rows-dropdown__trigger" onClick={() => setOpen(!open)}>
        {value} <Icons.ChevronDown />
      </button>
      {open && (
        <div className="rows-dropdown__menu">
          {opts.map(o => (
            <button
              key={o}
              className={`rows-dropdown__option ${value === o ? 'rows-dropdown__option--active' : ''}`}
              onClick={() => { onChange(o); setOpen(false); }}
            >
              {o}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================
// Education Banner
// ============================================
const EducationBanner = ({ onDismiss }) => (
  <div className="edu-banner">
    <div className="edu-banner__icon"><Icons.Info /></div>
    <div className="edu-banner__content">
      <div className="edu-banner__title">How WhatsApp Broadcasts work</div>
      <div className="edu-banner__text">
        WhatsApp requires message templates to be pre-approved by Meta before they can be used in broadcasts.
      </div>
      <div className="edu-banner__steps">
        <div className="edu-step">
          <div className="edu-step__num">1</div>
          <div className="edu-step__text"><strong>Create templates</strong> in Meta Business Manager</div>
        </div>
        <div className="edu-step">
          <div className="edu-step__num">2</div>
          <div className="edu-step__text"><strong>Wait for approval</strong> ~24 hour review by Meta</div>
        </div>
        <div className="edu-step">
          <div className="edu-step__num">3</div>
          <div className="edu-step__text"><strong>Sync &amp; send</strong> templates appear here automatically</div>
        </div>
      </div>
      <div className="edu-banner__actions">
        <button className="btn btn-secondary btn-sm">
          <Icons.ExternalLink /> Open Meta Business Manager
        </button>
        <span className="edu-banner__learn-more">Learn more about templates</span>
      </div>
    </div>
    <button className="dismiss-btn" title="Dismiss" onClick={onDismiss}>
      <Icons.Close />
    </button>
  </div>
);

// ============================================
// Empty State
// ============================================
const EmptyState = ({ onCreateBroadcast }) => (
  <div className="broadcasts-card">
    <div className="empty-state">
      <div className="empty-state__icon"><Icons.Bolt /></div>
      <div className="empty-state__title">Send your first broadcast</div>
      <div className="empty-state__desc">
        Reach your WhatsApp subscribers with marketing campaigns. You'll need at least one approved template from Meta Business Manager to get started.
      </div>
      <div className="empty-state__actions">
        <button className="btn btn-secondary">
          <Icons.ExternalLink /> Create Templates in Meta
        </button>
        <button className="btn btn-accent" onClick={onCreateBroadcast}>
          <Icons.Plus /> New Broadcast
        </button>
      </div>
    </div>
  </div>
);

// ============================================
// Stats Row
// ============================================
const StatsRow = () => (
  <div className="stats-row">
    <div className="stat-card">
      <div className="stat-card__label">Total Sent</div>
      <div className="stat-card__value">12,847</div>
      <span className="stat-card__change stat-card__change--up">↑ 23% vs last month</span>
    </div>
    <div className="stat-card">
      <div className="stat-card__label">Avg. Delivery Rate</div>
      <div className="stat-card__value">94.2%</div>
      <span className="stat-card__change stat-card__change--up">↑ 1.8%</span>
    </div>
    <div className="stat-card">
      <div className="stat-card__label">
        Avg. Read Rate
        <span className="stat-card__info-icon" title="May undercount — users can disable read receipts in WhatsApp">
          <Icons.InfoSmall />
        </span>
      </div>
      <div className="stat-card__value">67.8%</div>
      <span className="stat-card__change stat-card__change--down">↓ 2.1%</span>
    </div>
    <div className="stat-card">
      <div className="stat-card__label">Avg. Reply Rate</div>
      <div className="stat-card__value">8.4%</div>
      <span className="stat-card__change stat-card__change--up">↑ 0.6%</span>
    </div>
  </div>
);

// ============================================
// Main Component
// ============================================

/**
 * BroadcastsList — Landing page for the WhatsApp Broadcasts section.
 *
 * Props:
 *   onNavigate(view, data?) — routes to 'wizard' or 'detail' views.
 *
 * Renders:
 *   - Dismissible education banner (3-step guide)
 *   - Stats row (4 cards)
 *   - Broadcasts table with search, filter chips, template column,
 *     metric columns, 3-dot action menu, pagination with rows-per-page
 *   - Empty state (when no broadcasts exist)
 *
 * Note: Page title "WhatsApp Broadcasts" is rendered by the global header.
 *       This component does NOT render its own page heading.
 */
const BroadcastsList = ({ onNavigate }) => {
  const [showBanner, setShowBanner] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // In production, broadcasts come from props/context/API
  const broadcasts = sampleBroadcasts;
  const hasBroadcasts = broadcasts.length > 0;

  // Filter + search
  const filtered = broadcasts.filter(b => {
    if (activeFilter !== 'all' && b.status !== activeFilter) return false;
    if (searchQuery && !b.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleRowClick = (broadcast) => {
    if (broadcast.status === 'sent') {
      onNavigate('detail', broadcast);
    }
  };

  return (
    <div id="page-broadcasts">
      {/* Education Banner */}
      {hasBroadcasts && showBanner && (
        <EducationBanner onDismiss={() => setShowBanner(false)} />
      )}

      {/* Empty State or Content */}
      {!hasBroadcasts ? (
        <EmptyState onCreateBroadcast={() => onNavigate('wizard')} />
      ) : (
        <>
          <StatsRow />

          <div className="broadcasts-card">
            {/* Toolbar */}
            <div className="broadcasts-toolbar">
              <div className="broadcasts-toolbar__left">
                <div className="broadcasts-toolbar__search">
                  <Icons.Search />
                  <input
                    type="text"
                    placeholder="Search broadcasts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
                <div className="broadcasts-toolbar__filters">
                  {filters.map(f => (
                    <button
                      key={f.id}
                      className={`filter-chip ${activeFilter === f.id ? 'filter-chip--active' : ''}`}
                      onClick={() => setActiveFilter(f.id)}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>
              <button className="btn btn-accent" onClick={() => onNavigate('wizard')}>
                <Icons.Plus /> New Broadcast
              </button>
            </div>

            {/* Table */}
            <table>
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Template</th>
                  <th>Status</th>
                  <th>Audience</th>
                  <th className="th--right">Delivered</th>
                  <th className="th--right">Read</th>
                  <th>Sent At</th>
                  <th style={{ width: 48 }}></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(b => (
                  <tr key={b.id} onClick={() => handleRowClick(b)}>
                    <td><div className="broadcast-name">{b.name}</div></td>
                    <td><span className="broadcast-template">{b.template}</span></td>
                    <td><StatusPill status={b.status} /></td>
                    <td className="cell--muted">{b.audience || '—'}</td>
                    <MetricCell value={b.delivered} pct={b.deliveredPct} />
                    <MetricCell value={b.read} pct={b.readPct} />
                    <td className="cell--muted">{b.sentAt || (b.status === 'draft' ? 'Draft saved' : '—')}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <ActionMenu status={b.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination Footer */}
            <div className="table-footer">
              <div className="table-footer__left">
                <span>Showing {filtered.length} of {broadcasts.length} broadcasts</span>
                <span className="table-footer__rows-label">Rows:</span>
                <RowsDropdown value={rowsPerPage} onChange={setRowsPerPage} />
              </div>
              <div className="table-footer__pagination">
                <button className="page-btn"><Icons.ChevronLeft /></button>
                <button className="page-btn page-btn--active">1</button>
                <button className="page-btn">2</button>
                <button className="page-btn"><Icons.ChevronRight /></button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default BroadcastsList;
