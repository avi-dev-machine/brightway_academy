-- Default settings and ID-card template. Idempotent: existing values are never overwritten.

insert into app_settings (key, value) values
    ('academy', '{"name": "Brightway Computer Academy", "address": "", "phone": "", "email": "", "student_id_prefix": "BCA", "receipt_prefix": "BCA"}'),
    ('fees', '{"reminder_offsets_days": [-3, 0, 3, 7]}'),
    ('notifications', '{"channels": ["WHATSAPP", "SMS"], "fee_reminders_enabled": true, "payment_confirmations_enabled": true}'),
    ('setup', '{"completed": false, "completed_at": null}')
on conflict (key) do nothing;

insert into id_card_templates (name, is_default, layout) values (
    'Standard CR80',
    true,
    '{
        "width_mm": 85.6,
        "height_mm": 54,
        "background_color": "#FFFFFF",
        "elements": [
            {"type": "rect", "x": 0, "y": 0, "w": 85.6, "h": 11, "fill": "#1E3A8A"},
            {"type": "text", "x": 3, "y": 2, "w": 79.6, "h": 7, "text": "{{academy_name}}", "font_size": 11, "bold": true, "color": "#FFFFFF", "align": "C"},
            {"type": "image", "x": 3, "y": 14, "w": 21, "h": 26, "source": "{{photo}}"},
            {"type": "text", "x": 27, "y": 14, "w": 55.6, "h": 5, "text": "ID No: {{student_id}}", "font_size": 8, "bold": true},
            {"type": "text", "x": 27, "y": 19.5, "w": 55.6, "h": 5, "text": "{{name}}", "font_size": 9, "bold": true},
            {"type": "text", "x": 27, "y": 25, "w": 55.6, "h": 4, "text": "Guardian: {{guardian_name}}", "font_size": 7},
            {"type": "text", "x": 27, "y": 29.5, "w": 55.6, "h": 4, "text": "Course: {{course}}", "font_size": 7},
            {"type": "text", "x": 27, "y": 34, "w": 55.6, "h": 4, "text": "Contact: {{contact}}", "font_size": 7},
            {"type": "text", "x": 3, "y": 42, "w": 79.6, "h": 8, "text": "{{address}}", "font_size": 6, "multiline": true},
            {"type": "rect", "x": 0, "y": 51, "w": 85.6, "h": 3, "fill": "#1E3A8A"}
        ]
    }'
)
on conflict (name) do nothing;
