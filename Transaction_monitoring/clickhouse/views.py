from django.http import JsonResponse
from django.core.cache import cache
from rest_framework.decorators import api_view
from .clickhouse_client import query_clickhouse

@api_view(['GET'])
async def get_analytics(request):
    user_id = request.GET.get('user_id')

    if not user_id:
        return JsonResponse({'error': 'user_id is required'}, status=400)

    cache_key = f'analytics_{user_id}'
    cached_data = cache.get(cache_key)

    if cached_data:
        return JsonResponse(cached_data)

    query = """
    SELECT
        COUNT(*) AS transaction_count,
        SUM(amount) AS total_amount,
        AVG(amount) AS average_amount,
        MIN(amount) AS min_amount,
        MAX(amount) AS max_amount
    FROM transactions
    WHERE sender_account = %(user_id)s
    """
    result = await query_clickhouse(query, {'user_id': str(user_id)})

    columns = ['transaction_count', 'total_amount', 'average_amount', 'min_amount', 'max_amount']
    if result:
        data = dict(zip(columns, result[0]))
    else:
        data = {}

    cache.set(cache_key, data, timeout=3600)

    return JsonResponse(data)
