# CASCADE Delete Fix Summary

## Problem
The `clear_all_data` endpoint was failing with a Foreign Key violation:
```
classification_jobs_bank_statement_id_fkey: Still has references from ClassificationJob
```

This occurred because:
1. The `ClassificationJob` model had ForeignKey references to `users` and `bank_statements` without `ondelete='CASCADE'`
2. The `clear_all_data` endpoint was deleting `bank_statements` before deleting `classification_jobs`
3. Other models (`LearnedRule`, `Budget`, `Category`) also lacked CASCADE delete protection

## Solution

### 1. Added ON DELETE CASCADE to Model ForeignKeys

Updated all models with user/data ForeignKeys to include `ondelete='CASCADE'`:

#### `backend/app/models/classification_job.py`
```python
# Before
user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
bank_statement_id = Column(Integer, ForeignKey("bank_statements.id"), nullable=True)

# After
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
bank_statement_id = Column(Integer, ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=True)
```

#### `backend/app/models/learned_rule.py`
```python
# Before
user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

# After
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
```

#### `backend/app/models/budget.py`
```python
# Before
user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)

# After
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True)
```

#### `backend/app/models/category.py`
```python
# Before
user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

# After
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
```

### 2. Updated `clear_all_data` Endpoint

Enhanced the endpoint to delete all user-related data in the correct order:

**Deletion Order (respects FK constraints):**
1. ClassificationJob records (references bank_statements and users)
2. LearnedRule records (references users)
3. Budget records (references users and categories)
4. User-created Category records (system categories preserved)
5. Transaction records (references users and bank_statements)
6. BankStatement records (references users)

**Endpoint Changes:**
- Now deletes `classification_jobs`, `learned_rules`, `budgets`, and user-created categories
- Preserves system categories (`is_system=True`)
- Returns detailed counts of deleted records for each entity type

**Response Example:**
```json
{
  "message": "All user data cleared",
  "deleted_classification_jobs": 5,
  "deleted_learned_rules": 12,
  "deleted_budgets": 3,
  "deleted_categories": 2,
  "deleted_transactions": 150,
  "deleted_statements": 3
}
```

### 3. Added Comprehensive Tests

Created `backend/tests/test_clear_all_data.py` with 4 test cases:

1. **test_clear_all_data_with_classification_jobs**
   - Tests FK cascade with classification jobs
   - Verifies no FK violation occurs
   - Validates correct deletion of all related records

2. **test_clear_all_data_with_budgets_and_rules**
   - Tests deletion of learned rules and budgets
   - Verifies budgets attached to categories are deleted
   - Validates correct counts in response

3. **test_clear_all_data_preserves_system_categories**
   - Ensures system categories are NOT deleted
   - Verifies only user-created categories are removed

4. **test_clear_all_data_empty_user**
   - Tests endpoint with user having no data
   - Verifies all counts are 0
   - Confirms no errors with empty state

## Files Modified

1. `backend/app/models/classification_job.py` - Added CASCADE to FKs
2. `backend/app/models/learned_rule.py` - Added CASCADE to user_id FK
3. `backend/app/models/budget.py` - Added CASCADE to FKs
4. `backend/app/models/category.py` - Added CASCADE to user_id FK
5. `backend/app/routers/transactions.py` - Enhanced clear_all_data endpoint
6. `backend/tests/test_clear_all_data.py` - New comprehensive test suite

## Commit
```
Fix clear data FK violation - add CASCADE delete and delete jobs before bank statements
```

## Database Schema Impact

**For new deployments:** CASCADE delete will automatically work with fresh migrations.

**For existing PostgreSQL databases:** The FK constraints were already created without CASCADE. Options:
- **Recommended:** Let the application auto-migration handle it (if configured)
- **Alternative:** Manual migration to drop and recreate FKs with CASCADE
- **Current workaround:** The endpoint deletion order ensures correct deletion even without CASCADE

The application will work correctly with both old and new schema because the endpoint explicitly handles deletion order.

## Verification

The fix has been verified to:
- ✅ Add `ondelete='CASCADE'` to all user-related ForeignKeys
- ✅ Update endpoint to delete all user data in correct order
- ✅ Preserve system categories during clear
- ✅ Return detailed deletion counts
- ✅ Include comprehensive test coverage
- ✅ Compile without syntax errors

## Edge Cases Handled

1. **Users with no data:** All counts are 0, no errors
2. **Mixed system/user categories:** Only user-created ones deleted
3. **Orphaned classification jobs:** Deleted before bank statements
4. **Budgets with deleted categories:** Handled by category cascade + explicit budget delete
5. **Multiple classification jobs per user:** All deleted correctly
