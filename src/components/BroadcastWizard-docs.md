# Broadcast Wizard — Implementation Notes

## Files

| File | Purpose |
|------|---------|
| `BroadcastWizard.jsx` | Production React component — 4-step create wizard |
| `broadcasts.css` | Updated — wizard styles appended under `#page-broadcasts-wizard` |
| `BroadcastWizard-preview.jsx` | Self-contained artifact preview (inline styles) |

## Required: New CSS token in `variables.css`

Add alongside existing WhatsApp tokens:

```css
--color-accent-subtle: #fdf2f4;
```

This is used for selected state backgrounds on audience options, schedule toggles, and CSV upload hover. The WhatsApp tokens (`--color-whatsapp`, `--color-whatsapp-light`, `--color-whatsapp-dark`, `--color-bg-warm`) should already be added per the BroadcastsList implementation notes.

## Component API

```jsx
<BroadcastWizard
  onNavigate={(view, data?) => {}}
  templates={[...]}
  segments={[...]}
  timezones={[...]}
  defaultTimezone="Asia/Singapore (SGT, UTC+8)"
/>
```

### Props

| Prop | Type | Description |
|------|------|-------------|
| `onNavigate` | `(view, data?) => void` | `'list'` returns to broadcasts list |
| `templates` | `Array` | Approved Meta templates fetched via API. Each: `{ id, cat, lang, body, media, buttons }` |
| `segments` | `Array` | Audience segments from Contacts. Each: `{ id, label, count }` |
| `timezones` | `Array<string>` | Available timezone strings |
| `defaultTimezone` | `string` | Pre-populated from store settings |

### Template data shape

```js
{
  id: "new_arrivals_notify",    // Template identifier from Meta
  cat: "Marketing",              // "Marketing" or "Utility"
  lang: "EN",                    // Language code
  body: "Hey {{1}}! ...",        // Template body with variables
  media: "Image header",         // "Image header", "Text only", etc.
  buttons: 1                     // Number of action buttons
}
```

Templates are fetched live from Meta API when the wizard loads. No sync UI needed.

## Integration with AdminApp

The `BroadcastsList` component already calls `onNavigate('wizard')`. In AdminApp, this should render `BroadcastWizard` in place of the list:

```jsx
const [broadcastView, setBroadcastView] = useState('list');

// In render:
{activePage === 'broadcasts' && broadcastView === 'list' && (
  <BroadcastsList onNavigate={(view, data) => setBroadcastView(view)} />
)}
{activePage === 'broadcasts' && broadcastView === 'wizard' && (
  <BroadcastWizard
    onNavigate={(view) => setBroadcastView(view)}
    templates={approvedTemplates}
    segments={contactSegments}
    timezones={availableTimezones}
    defaultTimezone={storeTimezone}
  />
)}
```

## Design decisions (changes from original prototype)

### Removed from prototype
1. **No sync bar** — Templates pulled live from Meta API. No manual sync needed.
2. **No template card grid** — Replaced with simple dropdown. Template details shown in preview panel after selection.
3. **No back button at top** — Replaced with "← Back to list" text link at bottom of wizard sidebar.
4. **No Cancel button** — Redundant with Back to list link.
5. **No radio buttons on audience options** — Border highlight + background color is sufficient selection indicator.

### Added / changed
1. **Save as Draft** — Persistent top-right button on all 4 steps. Text only, no icon.
2. **Clickable sidebar steps** — Completed and active steps are clickable for non-linear navigation. Future steps remain grayed out. Completed step labels show pink accent on hover.
3. **Pink accent for selections** — All interactive selection states (audience, schedule, wizard steps) use `--color-accent` border and `--color-accent-subtle` background. WhatsApp green reserved for branding elements only.
4. **Cream backgrounds** — Template preview panel and WhatsApp message preview use `--color-bg-warm` (#fefcfa) instead of gray.
5. **Matching titles** — Sidebar step labels and content area titles are identical text.
6. **Segment selector** — Appears when "By Segment" is selected. Dropdown populated from Contacts segments.
7. **CSV upload area** — Visual placeholder with dashed border appears when "Upload CSV" is selected. Actual file handling is backend work.

### Step 4 footer buttons
- **Back** — returns to Step 3
- **Schedule Broadcast / Send Broadcast** — pink accent, label changes based on Step 3 choice

## CSS architecture

All wizard styles scoped under `#page-broadcasts-wizard` in `broadcasts.css`. Key class prefixes:
- `.wizard-` — layout, sidebar, steps
- `.audience-` — Step 2 options
- `.schedule-` — Step 3 options
- `.review-` — Step 4 summary
- `.template-preview` — Step 1 template detail
- `.wa-preview` — WhatsApp message bubble
- `.callout` — Info/warning callout boxes
- `.csv-upload` — Upload area
- `.cost-estimate` — Pricing display

Reuses global `.btn`, `.btn-accent`, `.btn-secondary`, `.form-input`, `.form-label` from global.css.

## Future enhancements (post-staging)

- Form validation (require campaign name + template before Continue)
- Template variable preview with sample data
- CSV file parsing with column mapping
- Segment multi-select (combine segments)
- Cost estimation based on actual audience count × country rates
- Loading states for template API fetch
- Draft auto-save on step change
