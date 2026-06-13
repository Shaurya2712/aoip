-- Default niches — run after schema.sql
INSERT INTO niches (name, priority, enabled) VALUES
  ('Finance', 10, true),
  ('Students', 9, true),
  ('Productivity', 9, true),
  ('Health', 8, true),
  ('Fitness', 8, true),
  ('Business', 7, true),
  ('Education', 7, true),
  ('AI', 8, true),
  ('Real Estate', 6, true),
  ('Construction', 5, true),
  ('Agriculture', 5, true)
ON CONFLICT (name) DO NOTHING;
