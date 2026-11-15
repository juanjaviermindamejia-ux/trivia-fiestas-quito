-- Preguntas iniciales. Es idempotente: se puede ejecutar varias veces.
-- Para agregar una pregunta nueva: un código nuevo (FQ-009...) en la primera
-- sentencia y sus 4 opciones en la segunda (solo una con is_correct = 1).
-- IMPORTANTE: verifiquen cada dato antes de entregar y agreguen más preguntas.

INSERT OR IGNORE INTO questions (code, text) VALUES
    ('FQ-001', '¿En qué mes se celebran las Fiestas de Quito?'),
    ('FQ-002', '¿Qué día se conmemora la fundación española de Quito?'),
    ('FQ-003', '¿En qué año fue la fundación española de Quito?'),
    ('FQ-004', '¿Quién fundó San Francisco de Quito en 1534?'),
    ('FQ-005', '¿Cómo se llaman los buses abiertos decorados donde se baila en las fiestas?'),
    ('FQ-006', '¿Qué apodo recibe la ciudad de Quito?'),
    ('FQ-007', '¿En qué año Quito fue declarada Patrimonio Cultural de la Humanidad por la UNESCO?'),
    ('FQ-008', '¿Cómo se llama de forma popular a una persona de Quito?');

WITH new_options (question_code, text, is_correct) AS (
    VALUES
        ('FQ-001', 'Agosto', 0),
        ('FQ-001', 'Diciembre', 1),
        ('FQ-001', 'Mayo', 0),
        ('FQ-001', 'Octubre', 0),

        ('FQ-002', '10 de agosto', 0),
        ('FQ-002', '24 de mayo', 0),
        ('FQ-002', '6 de diciembre', 1),
        ('FQ-002', '9 de octubre', 0),

        ('FQ-003', '1492', 0),
        ('FQ-003', '1534', 1),
        ('FQ-003', '1809', 0),
        ('FQ-003', '1822', 0),

        ('FQ-004', 'Sebastián de Benalcázar', 1),
        ('FQ-004', 'Simón Bolívar', 0),
        ('FQ-004', 'Antonio José de Sucre', 0),
        ('FQ-004', 'Francisco de Orellana', 0),

        ('FQ-005', 'Chivas', 1),
        ('FQ-005', 'Trolebuses', 0),
        ('FQ-005', 'Ecovías', 0),
        ('FQ-005', 'Carretas', 0),

        ('FQ-006', 'La Perla del Pacífico', 0),
        ('FQ-006', 'Carita de Dios', 1),
        ('FQ-006', 'La Sultana de los Andes', 0),
        ('FQ-006', 'La Ciudad Eterna', 0),

        ('FQ-007', '1978', 1),
        ('FQ-007', '1950', 0),
        ('FQ-007', '1999', 0),
        ('FQ-007', '2005', 0),

        ('FQ-008', 'Chulla quiteño', 1),
        ('FQ-008', 'Cuencano', 0),
        ('FQ-008', 'Guayaco', 0),
        ('FQ-008', 'Lojano', 0)
)
INSERT OR IGNORE INTO options (question_id, text, is_correct)
SELECT q.id, n.text, n.is_correct
FROM new_options AS n
JOIN questions AS q ON q.code = n.question_code;
