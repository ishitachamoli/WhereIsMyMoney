# AI Summary "Last 30 Days" Fix — Summary

## Problem
The AI Summary "Monthly Review" was showing "In the last 30 days, you spent X" but used **today's date** as the reference point. If a user uploaded transactions from 2025 but it's now 2026, the "last 30 days" would find no transactions from the past.

**Example**: 
- User uploads 2025 bank statement (transactions from Dec 2025)
- Today is May 2026
- System queries for transactions since May 2 (30 days ago from today)
- **Result**: No transactions found → Summary shows zeros

## Solution
Changed the system to use the **latest transaction date in the database** as the reference point instead of today's date.

## Files Changed

### Backend: `backend/app/services/ai_summary_service.py`

**Key Changes:**

1. **Main function (`generate_summary`)**:
   - Line 45: Get latest transaction date: `reference_date = all_txns[0].date`
   - Lines 51-54: Calculate date ranges relative to `reference_date`, not `datetime.now()`
   - Keep `now = datetime.now(timezone.utc)` only for `generated_at` timestamp

2. **Return object (lines 213-218)**:
   - Added `reference_date` to the `period` object
   - Added explanatory note: "All 'last 30 days' calculations use the latest transaction date as reference, not today's date"

3. **Updated function signatures** to accept `reference_date` instead of `now`:
   - `_build_monthly_review()` — Line 304
   - `_build_fun_statistics()` — Line 405
   - `_build_detailed_insights()` — Line 610
   - `_build_achievements()` — Line 753
   - `_build_predictions()` — Line 828

4. **Updated labels**:
   - Monthly Review summary sentence now shows: "In the last 30 days (through {ref_date_str}), you spent ₹X..."
   - Line 375: `ref_date_str = reference_date.strftime("%B %d, %Y")`

### Frontend Updates

1. **`frontend/types/index.ts`**:
   - Updated `AISummaryResponse` type to include optional `reference_date` and `note` in the `period` object
   - Line 498: `period: { start: string; end: string; reference_date?: string; note?: string } | null;`

2. **`frontend/app/ai-summary/page.tsx`**:
   - Updated label from "Top Categories (30 days)" to "Top Categories (last 30 days of data)"
   - The summary sentence from backend now displays the reference date automatically

## How It Works

**Before:**
```python
now = datetime.now(timezone.utc)  # May 29, 2026 (today)
thirty_days_ago = now - timedelta(days=30)  # April 29, 2026
last_30_txns = [t for t in all_txns if t.date >= thirty_days_ago]
# Result: No transactions from 2025 are included
```

**After:**
```python
reference_date = all_txns[0].date  # Dec 31, 2025 (latest transaction)
thirty_days_ago = reference_date - timedelta(days=30)  # Dec 1, 2025
last_30_txns = [t for t in all_txns if t.date >= thirty_days_ago]
# Result: Correctly includes 30 days of transactions from 2025
```

## Functions Fixed

All functions now use the `reference_date` for time-based calculations:

1. **`_build_monthly_review()`** — 30-day spending review
2. **`_build_fun_statistics()`** — Food ordering frequency, daily averages
3. **`_build_detailed_insights()`** — Spending trends, income patterns
4. **`_build_achievements()`** — Month tracking calculations
5. **`_build_predictions()`** — Year-end projections based on reference date

## Impact

✅ **Fixed**: AI Summary now works correctly with historical data
✅ **Clarified**: Labels now indicate data is from "last 30 days of data" not calendar days
✅ **Backward Compatible**: Still calculates all metrics correctly, just with proper date reference
✅ **Transparent**: API response includes `reference_date` and explanatory note

## Testing

To verify the fix:
1. Upload a bank statement from 2025 (or earlier)
2. Navigate to AI Summary → Monthly Review
3. **Expected**: Summary shows spending from the last 30 days of that statement
4. **Label shows**: "In the last 30 days (through {latest_date}), you spent ₹X..."

## Related Features

The same fix was applied to:
- Budget suggestions (already uses `max(dates)` as reference)
- All date-based analytics and insights
