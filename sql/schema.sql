-- Esquema de la base de datos de la trivia.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS questions (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,  -- identificador estable, ej. FQ-001
    text TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Fiestas de Quito'
);

CREATE TABLE IF NOT EXISTS options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
    text        TEXT    NOT NULL,
    is_correct  INTEGER NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    UNIQUE (question_id, text)
);

CREATE INDEX IF NOT EXISTS idx_options_question_id ON options (question_id);

-- Garantiza una sola respuesta correcta por pregunta.
CREATE UNIQUE INDEX IF NOT EXISTS uq_options_one_correct_per_question
    ON options (question_id) WHERE is_correct = 1;
