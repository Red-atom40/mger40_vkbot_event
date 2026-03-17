BEGIN;

CREATE TABLE IF NOT EXISTS applications (
    vk_id BIGINT PRIMARY KEY,
    fio TEXT NOT NULL,
    birth_date TEXT NOT NULL,
    region TEXT NOT NULL,
    city TEXT NOT NULL,
    phone TEXT NOT NULL,
    contact_info TEXT NOT NULL,
    education_level TEXT NOT NULL,
    is_member TEXT NOT NULL,
    previous_organizations TEXT NOT NULL,
    study_or_work_place TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admins (
    vk_id BIGINT PRIMARY KEY,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    message_text TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rsvp (
    vk_id BIGINT NOT NULL,
    event_id TEXT NOT NULL,
    answer TEXT,
    answered_at TIMESTAMPTZ,
    PRIMARY KEY (vk_id, event_id),
    CONSTRAINT rsvp_answer_check CHECK (answer IN ('да', 'нет') OR answer IS NULL),
    CONSTRAINT rsvp_event_fk FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE CASCADE,
    CONSTRAINT rsvp_application_fk FOREIGN KEY (vk_id) REFERENCES applications (vk_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rsvp_messages (
    vk_id BIGINT NOT NULL,
    event_id TEXT NOT NULL,
    message_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (vk_id, event_id),
    CONSTRAINT rsvp_messages_event_fk FOREIGN KEY (event_id) REFERENCES events (event_id) ON DELETE CASCADE,
    CONSTRAINT rsvp_messages_application_fk FOREIGN KEY (vk_id) REFERENCES applications (vk_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rsvp_vk_id_answer ON rsvp (vk_id, answer);
CREATE INDEX IF NOT EXISTS idx_rsvp_event_id_answer ON rsvp (event_id, answer);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events (created_at DESC);

COMMIT;
