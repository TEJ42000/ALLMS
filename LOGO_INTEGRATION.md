# Logo Integration

Replaces emoji (⚖️) with SVG logo for consistent branding.

## Changes

- `templates/course_selection.html` - Logo in nav & footer
- `app/static/css/homepage.css` - Styling & responsive design
- `tests/test_homepage_logo.py` - 18 automated tests (all passing)

## Technical Details

**Logo:** `app/static/images/favicon.svg` (Scales of Justice, navy/gold theme)  
**Sizes:** 40px (nav), 48px (footer), 32px/40px (mobile)  
**Effects:** Gold drop-shadow, hover scale, smooth transitions

## Testing

```bash
pytest tests/test_homepage_logo.py -v
# 18 tests covering: HTML structure, CSS classes, accessibility, responsive design
```
