# Registered collections, including ones holding no items — those never show up in
# COLLECTION_STATS below, so they are merged in afterwards with a zero count.
ALL_COLLECTIONS = "SELECT id FROM pgstac.collections ORDER BY 1"

# One scan covers item counts and date ranges for every collection; the events/hazards/impacts
# totals are summed from it rather than run as three more full-table scans.
COLLECTION_STATS = """
    SELECT collection,
           count(*) AS item_count,
           min(datetime) AS earliest,
           max(datetime) AS latest
    FROM pgstac.items
    GROUP BY 1
    ORDER BY 1
"""

EVENTS_BY_HAZARD_TYPE = """
    SELECT hazard_code, count(*) AS event_count
    FROM pgstac.items,
         jsonb_array_elements_text(content->'properties'->'monty:hazard_codes') AS hazard_code
    WHERE collection LIKE '%-events'
    GROUP BY 1
    ORDER BY 2 DESC
"""

ITEMS_BY_YEAR = """
    SELECT collection, extract(year FROM datetime)::int AS year, count(*) AS item_count
    FROM pgstac.items
    GROUP BY 1, 2
    ORDER BY 1, 2
"""
