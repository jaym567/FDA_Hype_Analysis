# FDA API Troubleshooting Guide

## Common Issues and Solutions

### 400 Bad Request Errors

The FDA API has limitations that can cause 400 errors:

1. **Skip Parameter Limits**: The API may not support very large `skip` values
   - **Solution**: The script now limits `skip` to 5000 maximum
   - **Solution**: Uses actual number of results returned instead of fixed LIMIT for pagination

2. **Sort + Skip Combination**: Some API endpoints don't support `sort` and `skip` together
   - **Solution**: Removed `sort` parameter when using `skip` for pagination

3. **Large Limit Values**: Very large `limit` values may be rejected
   - **Solution**: Reduced default `LIMIT` from 1000 to 100

### Best Practices

1. **Use Smaller Limits**: Start with `limit=100` or smaller
2. **Avoid Sort with Skip**: Don't combine `sort` and `skip` parameters
3. **Respect Rate Limits**: Use delays between requests (1+ seconds)
4. **Handle 400 Errors Gracefully**: Stop pagination on 400 errors rather than retrying

### Current Script Settings

- **LIMIT**: 100 (reduced from 1000)
- **MAX_SKIP**: 5000 (prevents excessive skip values)
- **Request Delay**: 1.0 seconds between requests
- **Max Requests**: 50 per session (safety limit)

### Alternative Approaches

If you continue to get 400 errors, try:

1. **Use existing data files**: The script will use existing data if available
2. **Fetch in smaller batches**: Manually fetch with smaller limits
3. **Use date-based queries**: Instead of skip, use date ranges
4. **Check FDA API status**: The API may be experiencing issues

### Testing the API

Test basic connectivity:
```python
import requests
r = requests.get('https://api.fda.gov/device/pma.json', params={'limit': 10})
print(f'Status: {r.status_code}')
```

If this works but your script doesn't, the issue is likely with specific parameters.

