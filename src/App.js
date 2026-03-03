import React, { useState } from 'react';
import './base.css';
import './components/broadcasts.css';
import BroadcastsList from './components/BroadcastsList';
import BroadcastWizard from './components/BroadcastWizard';
import BroadcastDetail from './components/BroadcastDetail';

// Sample templates — wizard uses: tp.id, tp.cat, tp.lang, tp.media, tp.buttons, tp.body
const sampleTemplates = [
  { id: 'valentines_promo_2025', cat: 'Marketing', lang: 'en', media: 'IMAGE', buttons: 1, body: "Hi {{1}}! \u2764\ufe0f Our Valentine's Day sale is here! Get {{2}}% off everything. Shop now before it ends!" },
  { id: 'new_arrivals_notify', cat: 'Marketing', lang: 'en', media: 'TEXT', buttons: 0, body: 'Hey {{1}}, check out our latest Spring Collection! Fresh styles just dropped.' },
  { id: 'cart_reminder_v2', cat: 'Utility', lang: 'en', media: 'IMAGE', buttons: 1, body: 'Hi {{1}}, you left items in your cart! Complete your purchase and enjoy free shipping.' },
  { id: 'flash_sale_announce', cat: 'Marketing', lang: 'en', media: 'IMAGE', buttons: 2, body: 'Flash Sale! {{1}}% off everything this weekend only. Hurry, offer ends Sunday!' },
  { id: 'loyalty_update_q1', cat: 'Utility', lang: 'en', media: 'TEXT', buttons: 1, body: 'Hi {{1}}, you have {{2}} loyalty points! Redeem them before they expire on {{3}}.' },
];

// Sample segments — wizard uses: s.id, s.label, s.count
const sampleSegments = [
  { id: '1', label: 'All Subscribers', count: 2435 },
  { id: '2', label: 'VIP Customers', count: 312 },
  { id: '3', label: 'Cart Abandoners', count: 903 },
  { id: '4', label: 'Loyalty Members', count: 1265 },
];

// Sample timezones
const sampleTimezones = [
  'Asia/Kolkata',
  'Asia/Singapore',
  'America/New_York',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Australia/Sydney',
  'Pacific/Auckland',
];

// Sample broadcast detail data — matches preview exactly
const sampleBroadcastDetail = {
  name: "Valentine's Day Sale",
  metrics: [
    { label: 'Total Sent', value: '2,434', pct: null, color: '#3b82f6' },
    { label: 'Delivered', value: '2,341', pct: '96.2%', color: '#25D366' },
    { label: 'Read', value: '1,687', pct: '72.1%', color: '#10b981', tooltip: 'May undercount — users can disable read receipts' },
    { label: 'Replied', value: '203', pct: '8.7%', color: '#059669' },
    { label: 'Failed', value: '93', pct: '3.8%', color: '#ef4444' },
  ],
  funnel: [
    { label: 'Sent', count: 2434, color: '#3b82f6', flex: 100 },
    { label: 'Delivered', count: 2341, color: '#25D366', flex: 96 },
    { label: 'Read', count: 1687, color: '#10b981', flex: 69 },
    { label: 'Replied', count: 203, color: '#059669', flex: 8 },
    { label: 'Failed', count: 93, color: '#ef4444', flex: 4 },
  ],
  details: {
    template: 'valentines_promo_2025',
    category: 'Marketing',
    audience: 'All Subscribers',
    audienceCount: 2434,
    sentAt: 'February 12, 2026 · 10:00 AM SGT',
    actualCost: '$117.24',
  },
  messagePreview: {
    hasImage: true,
    body: "\ud83d\udc8c Sarah, Valentine\u2019s Day is almost here! Surprise your special someone with our curated gift bundles. Shop now before Feb 14.",
    time: '10:00 AM',
    buttons: ['\ud83d\udecd\ufe0f Shop Gift Bundles', '\ud83d\udce6 Track My Order'],
  },
};

function App() {
  const [view, setView] = useState('list');
  const [selectedBroadcast, setSelectedBroadcast] = useState(null);

  const handleNavigate = (newView, data) => {
    if (newView === 'detail' && data) {
      setSelectedBroadcast({ ...sampleBroadcastDetail, name: data.name || sampleBroadcastDetail.name });
    }
    setView(newView);
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", fontSize: 14, color: '#1f2937' }}>
      {/* Global Sidebar */}
      <aside style={{ width: 240, background: '#e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 100 }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Global Sidebar</span>
      </aside>

      <div style={{ flex: 1, marginLeft: 240, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        {/* Global Header */}
        <header style={{ height: 60, background: 'white', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', position: 'sticky', top: 0, zIndex: 70 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#111827' }}>WhatsApp Broadcasts</div>
          <span style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic' }}>Per global header</span>
        </header>

        {/* Page Content */}
        <main style={{ flex: 1, background: '#fefcfa' }}>
          {view === 'list' && (
            <BroadcastsList onNavigate={handleNavigate} />
          )}
          {view === 'wizard' && (
            <BroadcastWizard
              onNavigate={handleNavigate}
              templates={sampleTemplates}
              segments={sampleSegments}
              timezones={sampleTimezones}
              defaultTimezone="Asia/Kolkata"
            />
          )}
          {view === 'detail' && (
            <BroadcastDetail
              broadcast={selectedBroadcast || sampleBroadcastDetail}
              onNavigate={handleNavigate}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
