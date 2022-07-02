# Rich Json ORM #

Just another JSON ORM but with caching and some useful operators like in Django. Requires the same structure for all dictionaries in list. Put your file in the root directory and name it as "source.json" and ORM will pick it up. Just be careful with the cache when modifying the data, in which case you will need to change and remove the key in the query cache dictionary.

## Available functions ##
- 'exact', 'ne', 'gte', 'gt', 'lte', 'lt', 'in', 'nin', 'isnull'
- 'or', 'ora'(or and)
- filter, exclude, count, first, values_list

## Examples ##
```python
qs = QuerySet().filter(id__in=[1, 3])
assert qs.count() == 2
qs = qs.filter(id=1, d__isnull=True)
assert qs.count() == 1
qs = QuerySet().filter(a__gt__or=1, b__or='c')
qs = QuerySet().filter(a__ora=1, c__ora=False, b__or='h')
assert qs.count() == 2
qs = QuerySet().filter().order_by('-a')
qs = qs.exclude(a=2)
assert qs.count() == 2
```
