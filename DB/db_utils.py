from ..Discord.api_utils import Game
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, date
import os

load_dotenv()
DATABASE_FILE = os.getenv('DATABASE_FILE')


def add_games_to_db(games_data):
    """
    Adds one or more Game objects to the 'games' table in the SQLite database.

    Args:
        games_data: A single Game object or a list of Game objects to add.
    """
    # Ensure games_data is always iterable (a list) for consistent processing
    if not isinstance(games_data, list):
        games_data = [games_data]

    if not games_data:
        print("No games provided to add.")
        return

    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Enable foreign key constraints if you have any (good practice)
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Prepare the SQL INSERT statement
        # Note: 'id' is AUTOINCREMENT, so we don't include it in the INSERT columns.
        # 'created_at' and 'updated_at' have defaults, so we don't include them either.
        insert_sql = """
        INSERT INTO games (
            game_date, game_time, home_abbrv, away_abbrv,
            home_score, away_score, game_state, tracked,
            period, in_intermission, seconds_remaining, game_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        # Prepare a list of tuples for the executemany method
        data_to_insert = []
        for game in games_data:
            # Format datetime object for SQLite TEXT columns
            game_date = game.start_time.strftime("%Y-%m-%d")
            game_time = game.start_time.strftime("%H:%M:%S")

            # Convert boolean values to integers (0 or 1)
            tracked_int = 1 if game.tracked else 0 if hasattr(
                game, 'tracked') else 0
            in_intermission_int = 1 if game.inIntermission else 0

            data_to_insert.append((
                game_date,
                game_time,
                game.home_team,  # Assuming home_abbrv corresponds to home_team in class
                game.away_team,  # Assuming away_abbrv corresponds to away_team in class
                game.home_score,
                game.away_score,
                game.game_state,
                tracked_int,  # Use the converted integer
                game.period,
                in_intermission_int,  # Use the converted integer
                game.secondsRemaining,
                game.game_type
            ))

        # Use executemany for efficiency if inserting multiple games
        cursor.executemany(insert_sql, data_to_insert)
        conn.commit()
        print(f"Successfully added {len(games_data)} game(s) to the database.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()  # Rollback changes on error
    finally:
        if conn:
            conn.close()  # Always close the connection


def update_games_from_objects(games_objs: list[Game]) -> tuple[int, int]:
    """
    Updates specified fields for a list of Game objects in the 'games' table.
    The updated fields are: home_score, away_score, game_state, period,
    in_intermission, and seconds_remaining.

    Args:
        games_objs (list[Game]): A list of Game objects containing updated status and their IDs.

    Returns:
        tuple[int, int]: A tuple (total_attempted, total_updated) indicating
                         how many updates were attempted and how many were successful.
    """
    if not games_objs:
        print("No Game objects provided for update.")
        return 0, 0

    conn = None
    total_attempted = len(games_objs)
    total_updated = 0

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        update_sql = """
        UPDATE games
        SET
            home_score = ?,
            away_score = ?,
            game_state = ?,
            period = ?,
            in_intermission = ?,
            seconds_remaining = ?
        WHERE id = ?;
        """

        data_to_update = []
        for game_obj in games_objs:
            # Convert Python boolean to SQLite integer (0 or 1)
            in_intermission_int = 1 if game_obj.inIntermission else 0

            # The order of values in this tuple must match the order of '?' in the SQL query
            # (home_score, away_score, game_state, period, in_intermission, seconds_remaining, id)
            data_to_update.append((
                game_obj.home_score,
                game_obj.away_score,
                game_obj.game_state,
                game_obj.period,
                in_intermission_int,
                game_obj.secondsRemaining,
                game_obj.id  # The WHERE clause parameter
            ))

        # Use executemany for efficient batch updates
        cursor.executemany(update_sql, data_to_update)
        conn.commit()

        total_updated = cursor.rowcount
        print(
            f"Attempted to update {total_attempted} games. Successfully updated {total_updated} game(s).")
        return total_attempted, total_updated

    except sqlite3.Error as e:
        print(f"Database error during batch update: {e}")
        if conn:
            conn.rollback()  # Rollback all changes if any error occurs during batch
        return total_attempted, 0  # Indicate that 0 were updated on error
    finally:
        if conn:
            conn.close()  # Always close the connection


def get_games_for_today():
    """
    Retrieves all games scheduled for the current date from the 'games' table.

    Returns:
        A list of Game objects for today's games, or an empty list if none are found.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    print(f"Fetching games for today: {today_str}")

    games = []
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # Enable foreign key constraints (good practice)
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Select all columns to reconstruct the Game object
        # Note: We need to specify all columns in the order they appear in the Game class
        # or map them by name. For simplicity, we'll fetch all.
        select_sql = """
        SELECT
            id, game_date, game_time, home_abbrv, away_abbrv,
            home_score, away_score, game_state, tracked,
            period, in_intermission, seconds_remaining,
            created_at -- We don't use created_at or updated_at in Game object init, but good to know they exist
        FROM games
        WHERE game_date = ?;
        """
        cursor.execute(select_sql, (today_str,))
        rows = cursor.fetchall()

        if not rows:
            print(f"No games found for {today_str}.")
            return []

        for row in rows:
            # Unpack row data into variables based on your table schema
            game_id, game_date_str, game_time_str, game_type, home_abbrv, away_abbrv, \
                home_score, away_score, game_state, tracked_int, \
                period, in_intermission_int, seconds_remaining, created_at = row

            # Reconstruct start_time from game_date and game_time strings
            # Combine date and time strings and parse them into a datetime object
            start_time_str = f"{game_date_str} {game_time_str}"
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")

            # Convert integer booleans back to Python booleans
            tracked_bool = bool(tracked_int)
            in_intermission_bool = bool(in_intermission_int)

            # Create a Game object
            game = Game(
                away_team=away_abbrv,
                home_team=home_abbrv,
                start_time=start_time,
                game_id=game_id,  # Using the database ID here
                home_score=home_score,
                away_score=away_score,
                period=period,
                inIntermission=in_intermission_bool,
                secondsRemaining=seconds_remaining,
                game_state=game_state,
                game_type=game_type
            )
            games.append(game)

        print(f"Retrieved {len(games)} game(s) for {today_str}.")
        return games

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()  # Always close the connection


def get_tracked_games_for_today():
    """
    Retrieves all games scheduled for the current date that are marked as 'tracked'.

    Returns:
        A list of Game objects for today's tracked games, or an empty list if none are found.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    print(f"Fetching tracked games for today: {today_str}")

    games = []
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        # Modified SQL query: Added 'AND tracked = 1' to the WHERE clause
        select_sql = """
        SELECT
            id, game_date, game_time, game_type, home_abbrv, away_abbrv,
            home_score, away_score, game_state, tracked,
            period, in_intermission, seconds_remaining,
            created_at
        FROM games
        WHERE game_date = ? AND tracked = 1;
        """
        cursor.execute(select_sql, (today_str,))
        rows = cursor.fetchall()

        if not rows:
            print(f"No tracked games found for {today_str}.")
            return []

        for row in rows:
            # Unpack row data
            game_id, game_date_str, game_time_str, game_type, home_abbrv, away_abbrv, \
                home_score, away_score, game_state, \
                period, in_intermission_int, seconds_remaining, created_at = row

            # Reconstruct start_time
            start_time_str = f"{game_date_str} {game_time_str}"
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")

            # Convert boolean integers back to Python booleans
            in_intermission_bool = bool(in_intermission_int)

            # Create Game object
            game = Game(
                away_team=away_abbrv,
                home_team=home_abbrv,
                start_time=start_time,
                game_id=game_id,
                home_score=home_score,
                away_score=away_score,
                period=period,
                inIntermission=in_intermission_bool,
                secondsRemaining=seconds_remaining,
                game_state=game_state,
                game_type=game_type
            )
            games.append(game)

        print(f"Retrieved {len(games)} tracked game(s) for {today_str}.")
        return games

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if conn:
            conn.close()  # Always close the connectionb
