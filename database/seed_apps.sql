INSERT INTO apps (app_id, app_name, country, source, enabled)
VALUES
    ('my.com.tngdigital.ewallet', 'Touch ''n Go eWallet', 'my', 'google_play', TRUE),
    ('com.shopee.my', 'Shopee Malaysia', 'my', 'google_play', TRUE)
ON CONFLICT (app_id) DO UPDATE
SET
    app_name = EXCLUDED.app_name,
    country = EXCLUDED.country,
    source = EXCLUDED.source,
    enabled = EXCLUDED.enabled;
