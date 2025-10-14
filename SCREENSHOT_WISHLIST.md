# Screenshot Wishlist for Documentation

**DO NOT COMMIT THIS FILE** - This is a working document for screenshot collection.

## Priority Screenshots Needed

### Home Page / Hero Section
1. **Main merchant aggregation view**
   - Show merchants grouped with counts and totals
   - Highlight sort indicators (↓ arrows)
   - Show stats bar at top
   - Caption: "Aggregate view showing merchants with transaction counts and totals"

2. **Demo mode welcome screen**
   - Clean screenshot of `moneyflow --demo` startup
   - Shows "moneyflow [DEMO MODE]" title
   - Caption: "Try it instantly with demo mode - no account needed"

### Getting Started
3. **Credential unlock screen**
   - Shows the password unlock dialog
   - Caption: "Encrypted credential unlock - your credentials never leave your machine"

4. **Data loading progress**
   - Shows progress indicator with percentage
   - Caption: "One-time data download with progress indicator"

### User Guide - Views & Navigation
5. **Category view**
   - Show categories aggregated
   - Different from merchant view
   - Caption: "Category aggregation with drill-down navigation"

6. **Drill-down to transaction details**
   - Show transaction list after clicking a category
   - Show breadcrumb navigation
   - Caption: "Drill down from aggregate to transaction details"

7. **All Transactions view**
   - Press 'u' to show ungrouped
   - Show sorted by date descending
   - Caption: "All transactions view sorted by date (newest first)"

### User Guide - Editing
8. **Edit merchant modal**
   - Show the edit merchant dialog with suggestions
   - Highlight autocomplete
   - Caption: "Edit merchant name with autocomplete suggestions"

9. **Category selection modal**
   - Show type-to-search category picker
   - Caption: "Type-to-search category selection with 88 categories"

10. **Bulk edit in action**
    - Show merchant view with 'm' hint visible
    - Or show "Queued 15 edits" notification
    - Caption: "Bulk edit all transactions for a merchant at once"

11. **Review changes screen**
    - Show the commit review table
    - Multiple pending edits visible
    - Caption: "Review all pending changes before committing to backend"

12. **Transaction with flags**
    - Show transaction with ✓ (selected), H (hidden), * (pending edit) flags
    - Caption: "Visual indicators: ✓=selected H=hidden *=pending edit"

### User Guide - Time Navigation
13. **Time period breadcrumb**
    - Show "Merchants > October 2025" breadcrumb
    - Caption: "Navigate between time periods with arrow keys"

14. **Monthly view**
    - Show stats for just one month
    - Caption: "View specific month with accurate monthly stats"

### User Guide - Keyboard
15. **Filter modal with keyboard hints**
    - Show "h=Toggle hidden | t=Toggle transfers"
    - Caption: "Fully keyboard-driven - no mouse needed"

16. **Search modal**
    - Show search input with instructions
    - Caption: "Search merchant or category names - Press Enter with empty to clear"

### Features Showcase
17. **Multi-select with Space**
    - Show several transactions with ✓ checkmarks
    - Caption: "Multi-select with Space key for bulk operations"

18. **Stats showing filtered data**
    - Show different stats when viewing Oct vs. All Time
    - Side-by-side if possible
    - Caption: "Stats reflect current filtered view, not entire dataset"

### Advanced Features
19. **Bulk recategorize from Category view**
    - Show Category view with 'r' hint
    - Caption: "NEW: Bulk recategorize all transactions in a category"

20. **--mtd flag in action**
    - Terminal showing `moneyflow --mtd` startup
    - Caption: "Fast startup with --mtd (month-to-date) flag"

## Screenshot Specifications

**General Guidelines:**
- Terminal size: 120x40 (or larger for readability)
- Font: Monospace, size 14-16
- Theme: Dark theme (matches docs site)
- Clean terminal (no other tabs/windows visible)
- High DPI/Retina quality

**What to Highlight:**
- Keyboard shortcuts in hints
- Visual indicators (arrows, flags)
- Stats bar showing context
- Breadcrumb navigation
- Modal dialogs

**File Naming:**
```
screenshots/
├── home-merchant-view.png
├── demo-mode.png
├── credential-unlock.png
├── category-view.png
├── drill-down.png
├── all-transactions.png
├── edit-merchant.png
├── category-picker.png
├── bulk-edit.png
├── review-changes.png
├── transaction-flags.png
├── monthly-navigation.png
├── monthly-stats.png
├── filter-modal.png
├── search-modal.png
├── multi-select.png
├── filtered-stats.png
├── bulk-recategorize.png
└── mtd-flag.png
```

## Ideal Scenarios for Screenshots

### For merchant-view.png:
```
# Load demo with good data
moneyflow --demo

# Should show:
- Multiple merchants
- Varying transaction counts
- Sort arrows visible
- Stats at top showing totals
```

### For edit-merchant.png:
```
# In demo mode
# Press 'm' on a merchant
# Type a few letters to show autocomplete

# Should show:
- Current merchant name
- Input field with suggestions
- List of matching merchants
- Transaction count context
```

### For review-changes.png:
```
# Make several edits (merchant, category)
# Press 'w' to review

# Should show:
- Table with all pending changes
- Old value → New value columns
- Transaction context
- "Commit Changes" button
```

## Documentation Sections Needing Updates

### README.md
- [ ] Update Quick Start to mention --mtd
- [ ] Add screenshot to hero section
- [ ] Update keyboard shortcuts list
- [ ] Mention bulk recategorize feature
- [ ] Update search clearing instructions

### docs/index.md
- [ ] Add hero screenshot
- [ ] Update feature list (bulk recategorize, --mtd)
- [ ] Add screenshots section

### docs/getting-started/*.md
- [ ] Update with actual screenshots
- [ ] Verify CLI flags are current
- [ ] Add troubleshooting for session issues

### docs/guide/*.md
- [ ] Add screenshots for each workflow
- [ ] Update keyboard shortcuts (Esc behavior, filter shortcuts)
- [ ] Document bulk recategorize
- [ ] Update search clearing method

### docs/reference/cli.md
- [ ] Add --mtd flag documentation
- [ ] Update all flag descriptions
- [ ] Add examples

### docs/reference/troubleshooting.md
- [ ] Add section on session expiration
- [ ] Add section on checking log files (~/.moneyflow/moneyflow.log)
- [ ] Update error messages users might see

## Next Steps

1. **You capture screenshots** following wishlist above
2. **I will:**
   - Update all docs with current features
   - Add screenshots to appropriate sections
   - Ensure consistency across docs
   - Update README with latest
   - Create missing stub docs with proper content

3. **Together we'll:**
   - Review final docs site
   - Publish to moneyflow.dev
   - Celebrate! 🎉
