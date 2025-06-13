-- Create "games" table
CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    game_date DATE NOT NULL,
    game_time TIME NOT NULL,
    home_abbrv CHAR(3) NOT NULL,
    away_abbrv CHAR(3) NOT NULL,
    home_score INT DEFAULT 0,
    away_score INT DEFAULT 0,
    game_state VARCHAR(5) DEFAULT 'FUT',
    tracked BOOLEAN DEFAULT 0,
    period INT DEFAULT 0,
    in_intermission BOOLEAN DEFAULT 0,
    seconds_remaining INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
)

-- Trigger to update 'updated_at' column on row changes
CREATE TRIGGER IF NOT EXISTS update_games_updated_at
AFTER UPDATE ON games
FOR EACH ROW
BEGIN
    UPDATE games SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;