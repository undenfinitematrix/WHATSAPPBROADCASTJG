# Broadcasts List — Implementation Notes

## Files

| File | Purpose |
|------|---------|
| `BroadcastsList.jsx` | Production React component — list view with empty state |
| `broadcasts.css` | Modular CSS scoped under `#page-broadcasts` |
| `BroadcastsList-preview.jsx` | Self-contained artifact preview (inline styles, includes simplified admin shell) |

## Required: New CSS tokens in `variables.css`

Add these to the `:root` block:

```css
--color-whatsapp: #25D366;
--color-whatsapp-light: #dcf8e8;
--color-whatsapp-dark: #128C7E;
--color-bg-warm: #fefcfa;
```

## Required: AdminApp.jsx changes

### 1. Navigation — Add MARKETING section

Insert between "Main" and "Connect" in the `navItems` array:

```js
{
  section: 'Marketing',
  items: [
    { id: 'contacts', label: 'Contacts', icon: 'Contacts' },
    { id: 'broadcasts', label: 'Broadcasts', icon: 'Broadcasts' },
  ]
}
```

### 2. Page config — Add broadcasts entry

```js
broadcasts: { title: 'WhatsApp Broadcasts' }
```

### 3. Page rendering — Add conditional in `<main>`

```jsx
{activePage === 'broadcasts' && <BroadcastsList onNavigate={handleBroadcastsNavigate} />}
```

### 4. Content background

The main content area for broadcasts should use `var(--color-bg-warm)` (#fefcfa) instead of the default gray.

## Component API

```jsx
<BroadcastsList onNavigate={(view, data?) => {}} />
```

**`onNavigate(view, data?)`**
- `'wizard'` — opens the Create Broadcast wizard (no data)
- `'detail', broadcast` — opens analytics detail for a sent broadcast

## Architecture decisions

1. **No in-page header** — Title "WhatsApp Broadcasts" is rendered by the global header bar, not repeated inside the page content.

2. **No Sync Templates button** — Template syncing happens automatically in the background or is managed in Settings. Not surfaced on the list page.

3. **Template as separate column** — Keeps table rows tight. Campaign column shows only the name; template identifier is its own column.

4. **No campaign row icons** — Every row would have the same icon, adding visual noise without information.

5. **Status pills without dots** — The pill color already differentiates statuses. Dot inside is redundant.

6. **All row actions in 3-dot menu** — Single consistent entry point per row. Actions vary by status:
   - Sent: View Analytics, Duplicate
   - Scheduled: Edit, Cancel
   - Draft: Edit, Delete

7. **Custom rows-per-page dropdown** — Native `<select>` replaced with styled dropdown matching the design system. Options: 25, 50, 100. Default: 25.

8. **Read Rate tooltip** — Small info icon next to the stat label noting that read receipts may undercount since users can disable them in WhatsApp settings.

9. **Education banner** — Dismissible 3-step guide explaining the Meta template workflow. "Learn more" link has hover state (underline + color shift to WhatsApp green).

## Stats row — Data source notes

| Metric | Source | Reliability |
|--------|--------|-------------|
| Total Sent | API dispatch count | Solid |
| Avg. Delivery Rate | Meta delivery receipt webhooks | Solid |
| Avg. Read Rate | Meta read receipt webhooks | Directional — users can disable read receipts |
| Avg. Reply Rate | Custom attribution (inbound messages matched to broadcast recipients within time window) | Requires backend logic |

## Future enhancements (post-staging)

- Search input focus state styling
- Empty filtered state message (e.g., "No scheduled broadcasts")
- Column sort indicators (Sent At as default sort)
- localStorage persistence for banner dismissal
- Bulk selection / batch actions
