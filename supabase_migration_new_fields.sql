-- Run once in Supabase SQL Editor BEFORE deploying the updated app.
-- Preserve existing records and legacy type_of_engagement data.
ALTER TABLE public.staff_records ADD COLUMN IF NOT EXISTS sector text NOT NULL DEFAULT '';
ALTER TABLE public.staff_records ADD COLUMN IF NOT EXISTS experience text NOT NULL DEFAULT '';
CREATE INDEX IF NOT EXISTS staff_records_sector_idx ON public.staff_records(sector);
-- Optional normalization of existing labels; no other evaluation records are deleted.
UPDATE public.staff_records SET evaluation = 'Exceptional'
WHERE lower(trim(evaluation)) = 'excellent';
