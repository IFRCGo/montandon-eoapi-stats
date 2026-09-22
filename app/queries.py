TOTAL_COLLECTIONS = "SELECT count(*) FROM pgstac.collections"

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

EVENTS_BY_YEAR = """
    SELECT extract(year FROM datetime)::int AS year, count(*) AS event_count
    FROM pgstac.items
    WHERE collection LIKE '%-events'
    GROUP BY 1
    ORDER BY 1
"""
