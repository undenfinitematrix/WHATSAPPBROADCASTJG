# Broadcast Detail — Implementation Notes

## Files

| File | Purpose |
|------|---------|
| `BroadcastDetail.jsx` | Production React component — analytics view |
| `broadcasts.css` | Updated — detail styles appended under `#page-broadcasts-detail` |
| `BroadcastDetail-preview.jsx` | Self-contained artifact preview (inline styles) |

## Component API

```jsx
<BroadcastDetail
  broadcast={{
    name: "Valentine's Day Sale",
    metrics: [...],
    funnel: [...],
    details: {...},
    messagePreview: {...},
  }}
  onNavigate={(view) => {}}
/>
```

### Props

| Prop | Type | Description |
|------|------|-------------|
| `onNavigate` | `(view) => void` | `'list'` returns to broadcasts list |
| `broadcast` | `Object` | Full broadcast data (see shapes below) |

### Data shapes

**metrics** — Array of 5 objects:
```js
{ label: "Total Sent", value: "2,434", pct: null, color: "var(--color-info)", tooltip: null }
{ label: "Delivered", value: "2,341", pct: "96.2%", color: "#25D366", tooltip: null }
{ label: "Read", value: "1,687", pct: "72.1%", color: "var(--color-primary)", tooltip: "May undercount..." }
{ label: "Replied", value: "203", pct: "8.7%", color: "#059669", tooltip: null }
{ label: "Failed", value: "93", pct: "3.8%", color: "var(--color-danger)", tooltip: null }
```

**funnel** — Array of stage objects for the horizontal bar:
```js
{ label: "Sent", count: 2434, color: "var(--color-info)", flex: 100 }
// flex values are proportional (sent = 100, others relative)
```

**details** — Campaign metadata:
```js
{ template, category, audience, audienceCount, sentAt, actualCost }
```

**messagePreview** — WhatsApp bubble content:
```js
{ hasImage: true, body: "...", time: "10:00 AM", buttons: ["💝 Shop Gift Bundles", "📦 Track My Order"] }
```

## Integration with AdminApp

Add alongside existing broadcast views:

```jsx
{activePage === 'broadcasts' && broadcastView === 'detail' && (
  <BroadcastDetail
    broadcast={selectedBroadcast}
    onNavigate={(view) => setBroadcastView(view)}
  />
)}
```

The `BroadcastsList` already passes broadcast data via `onNavigate('detail', broadcast)`.

## Design decisions

1. **No back button** — Subtle "← Back to list" gray text link sits inline after the status pill. Underlines on hover. Unobtrusive.

2. **Colored top borders on analytics cards** — Each card has a 3px top border matching its metric color (blue for sent, green for delivered, etc.). Provides visual differentiation without heavy decoration.

3. **Read metric tooltip** — Info icon with hover tooltip noting read receipts may undercount.

4. **Delivery funnel bar** — Horizontal stacked bar with proportional segments. Labels only show on segments wide enough (>12% of total). Legend below with colored dots and counts.

5. **WhatsApp preview** — Cream background, reuses same bubble pattern as wizard Step 4.

6. **Duplicate / Export buttons** — Top-right secondary buttons for common actions.

## Analytics data source notes

| Metric | Source | Reliability |
|--------|--------|-------------|
| Total Sent | API dispatch count | Exact |
| Delivered | Meta delivery receipt webhooks | Exact |
| Read | Meta read receipt webhooks | Directional (users can disable) |
| Replied | Custom attribution logic | Requires backend matching |
| Failed | Meta error callbacks | Exact |
| Actual Cost | Meta billing API or calculated from sent × rate | Depends on integration |

## Future enhancements

- Time-series chart (deliveries over time)
- Recipient list with individual delivery status
- A/B test comparison view
- Export to CSV/PDF
- Failed message retry functionality
- Real-time updates for in-progress sends
