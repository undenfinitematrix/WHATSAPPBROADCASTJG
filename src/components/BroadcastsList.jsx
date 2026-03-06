import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useBroadcasts } from '../api-client';

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

const filters = [
  { id: 'all', label: 'All' },
  { id: 'sent', label: 'Sent' },
  { id: 'scheduled', label: 'Scheduled' },
  { id: 'draft', label: 'Draft' },
];

// ============================================
// Hardcoded dashboard rows (5 Sent + 5 Scheduled)
// ============================================
const hardcodedBroadcasts = [
  { id: 'hc-1', campaign_name: "Valentine's Day Sale", template_name: 'valentines_promo_2025', status: 'sent', audience_label: 'All Subscribers', delivered_count: 2341, read_count: 1687, sent_at: '2026-02-12T10:00:00' },
  { id: 'hc-2', campaign_name: 'Abandoned Cart Reminder', template_name: 'cart_reminder_v2', status: 'sent', audience_label: 'Cart Abandoners', delivered_count: 847, read_count: 612, sent_at: '2026-02-08T14:30:00' },
  { id: 'hc-3', campaign_name: 'Loyalty Points Update', template_name: 'loyalty_update_q1', status: 'sent', audience_label: 'Loyalty Members', delivered_count: 1203, read_count: 891, sent_at: '2026-02-01T11:00:00' },
  { id: 'hc-4', campaign_name: 'Winter Clearance Blast', template_name: 'winter_clearance_2026', status: 'sent', audience_label: 'All Subscribers', delivered_count: 3102, read_count: 2280, sent_at: '2026-01-20T09:00:00' },
  { id: 'hc-5', campaign_name: 'Re-engagement Campaign', template_name: 'win_back_inactive', status: 'sent', audience_label: 'Inactive 30d', delivered_count: 564, read_count: 389, sent_at: '2026-01-15T13:00:00' },
  { id: 'hc-6', campaign_name: 'New Arrivals — Spring Collection', template_name: 'new_arrivals_notify', status: 'scheduled', audience_label: 'VIP Customers', delivered_count: null, read_count: null, sent_at: '2026-03-10T09:00:00' },
  { id: 'hc-7', campaign_name: "Women's Day Offer", template_name: 'womens_day_promo', status: 'scheduled', audience_label: 'All Subscribers', delivered_count: null, read_count: null, sent_at: '2026-03-08T08:00:00' },
  { id: 'hc-8', campaign_name: 'Flash Sale Weekend', template_name: 'flash_sale_announce', status: 'scheduled', audience_label: 'Cart Abandoners', delivered_count: null, read_count: null, sent_at: '2026-03-15T10:00:00' },
  { id: 'hc-9', campaign_name: 'Membership Renewal Notice', template_name: 'membership_renew_v1', status: 'scheduled', audience_label: 'Loyalty Members', delivered_count: null, read_count: null, sent_at: '2026-03-20T11:00:00' },
  { id: 'hc-10', campaign_name: 'Easter Early Access', template_name: 'easter_early_bird', status: 'scheduled', audience_label: 'VIP Customers', delivered_count: null, read_count: null, sent_at: '2026-04-01T09:00:00' },
];

// ============================================
// Helpers
// ============================================

/** Format an ISO date string to "Feb 12, 10:00 AM" */
function formatDate(isoString) {
  if (!isoString) return null;
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
      ', ' +
      d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
  } catch {
    return isoString;
  }
}

/** Debounce hook — delays value updates by `delay` ms */
function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

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
  const [page, setPage] = useState(1);

  // Debounce search so we don't hit the API on every keystroke
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Reset to page 1 when filter or search changes
  useEffect(() => { setPage(1); }, [activeFilter, debouncedSearch, rowsPerPage]);

  // Fetch broadcasts from Supabase via API
  const apiParams = useMemo(() => ({
    status: activeFilter,
    search: debouncedSearch,
    page,
    pageSize: rowsPerPage,
  }), [activeFilter, debouncedSearch, page, rowsPerPage]);

  const { data, loading, error } = useBroadcasts(apiParams);

  const apiBroadcasts = data?.broadcasts || [];
  const apiTotal = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  // Filter hardcoded rows by active filter and search (same logic as API)
  const filteredHardcoded = hardcodedBroadcasts.filter(b => {
    if (activeFilter !== 'all' && b.status !== activeFilter) return false;
    if (debouncedSearch) {
      const q = debouncedSearch.toLowerCase();
      if (!b.campaign_name.toLowerCase().includes(q) && !b.template_name.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // Hardcoded rows first, then API rows
  const broadcasts = [...filteredHardcoded, ...apiBroadcasts];
  const total = filteredHardcoded.length + apiTotal;
  const hasBroadcasts = !loading && (total > 0 || activeFilter !== 'all' || debouncedSearch);

  const handleRowClick = (broadcast) => {
    if (broadcast.status === 'sent') {
      onNavigate('detail', broadcast);
    }
  };

  // Build page buttons
  const pageButtons = [];
  for (let i = 1; i <= totalPages && i <= 5; i++) {
    pageButtons.push(i);
  }

  return (
    <div id="page-broadcasts">
      {/* Education Banner */}
      {hasBroadcasts && showBanner && (
        <EducationBanner onDismiss={() => setShowBanner(false)} />
      )}

      {/* Empty State or Content */}
      {!loading && !hasBroadcasts && !error ? (
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

            {/* Loading / Error states */}
            {loading && (
              <div style={{ padding: '40px 24px', textAlign: 'center', color: '#6b7280' }}>
                Loading broadcasts...
              </div>
            )}

            {error && (
              <div style={{ padding: '40px 24px', textAlign: 'center', color: '#ef4444' }}>
                Failed to load broadcasts: {error}
              </div>
            )}

            {/* Table */}
            {!loading && !error && (
              <>
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
                    {broadcasts.length === 0 ? (
                      <tr>
                        <td colSpan={8} style={{ textAlign: 'center', padding: '32px 0', color: '#9ca3af' }}>
                          No broadcasts found
                        </td>
                      </tr>
                    ) : broadcasts.map(b => (
                      <tr key={b.id} onClick={() => handleRowClick(b)}>
                        <td><div className="broadcast-name">{b.campaign_name}</div></td>
                        <td><span className="broadcast-template">{b.template_name || '—'}</span></td>
                        <td><StatusPill status={b.status} /></td>
                        <td className="cell--muted">{b.audience_label || '—'}</td>
                        <MetricCell value={b.delivered_count || null} pct={b.delivered_pct} />
                        <MetricCell value={b.read_count || null} pct={b.read_pct} />
                        <td className="cell--muted">{formatDate(b.sent_at) || (b.status === 'draft' ? 'Draft saved' : '—')}</td>
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
                    <span>Showing {broadcasts.length} of {total} broadcasts</span>
                    <span className="table-footer__rows-label">Rows:</span>
                    <RowsDropdown value={rowsPerPage} onChange={setRowsPerPage} />
                  </div>
                  <div className="table-footer__pagination">
                    <button className="page-btn" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}><Icons.ChevronLeft /></button>
                    {pageButtons.map(p => (
                      <button key={p} className={`page-btn ${page === p ? 'page-btn--active' : ''}`} onClick={() => setPage(p)}>{p}</button>
                    ))}
                    <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}><Icons.ChevronRight /></button>
                  </div>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default BroadcastsList;
