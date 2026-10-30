CREATE TABLE sense_translations (
    sense_id TEXT NOT NULL,
    language TEXT NOT NULL,
    translation TEXT NOT NULL,
    source TEXT NOT NULL,

    PRIMARY KEY (sense_id, language)
);

CREATE TABLE sense_clozes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sense_id TEXT NOT NULL,
    sentence TEXT NOT NULL,
    answer TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE sense_reviews (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sense_id TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    rating SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 4),
    review_type TEXT NOT NULL
);
