-- Esquema de la trivia: tres bancos y un historial independiente por categoría.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS questions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    code       TEXT NOT NULL UNIQUE,
    text       TEXT NOT NULL,
    category   TEXT NOT NULL DEFAULT 'Fiestas de Quito',
    difficulty INTEGER NOT NULL DEFAULT 1 CHECK (difficulty BETWEEN 1 AND 3)
);

CREATE TABLE IF NOT EXISTS options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    is_correct  INTEGER NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    UNIQUE (question_id, text)
);

-- Un registro por pregunta mostrada. Se borra solo al completar el ciclo
-- de SU categoría; se conserva al reiniciar la aplicación.
CREATE TABLE IF NOT EXISTS used_questions (
    category    TEXT NOT NULL,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    PRIMARY KEY (category, question_id)
);

CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
CREATE INDEX IF NOT EXISTS idx_options_question_id ON options(question_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_options_one_correct_per_question
    ON options(question_id) WHERE is_correct = 1;
