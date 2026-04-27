"""CineMatch: a movie recommendation system."""

# JSON is used for the movie database + saving progress.
import json

# Importing this separately keeps error handling readable.
from json import JSONDecodeError

# We use Path so file locations work cross-platform.
from pathlib import Path


# Base folder for files shipped with this script.
BASE_DIR = Path(__file__).resolve().parent

# The built-in movie database file.
MOVIES_FILE = BASE_DIR / "movies.json"

# Where we store the user's saved profile / watched list / ratings.
USER_DATA_FILE = BASE_DIR / "user_data.json"

# Starting weights for explicit preferences.
GENRE_LIKE_WEIGHT = 3
GENRE_DISLIKE_WEIGHT = -3
MOOD_PREFERENCE_WEIGHT = 2

# Extra weight changes based on a 1–5 user rating.
RATING_ADJUSTMENTS = {1: -2, 2: -1, 3: 0, 4: 1, 5: 2}

# How many recommendations we show by default.
DEFAULT_RECOMMENDATION_COUNT = 5

# Common “special inputs” in menus.
CLEAR_TOKENS = {"clear", "none"}

LIST_TOKENS = {"list", "show"}

DONE_TOKENS = {"done", "finish", "back"}


# Custom error so we can exit cleanly on Ctrl+C / Ctrl+D.
class UserExit(Exception):
    """Raised when the user exits interactive input unexpectedly."""


# Fresh blank user data structure for a brand new user.
def create_default_user_data():
    return {
        "profile": {
            "name": "",
            "liked_genres": [],
            "disliked_genres": [],
            "preferred_mood": None,
            "max_runtime": None,
        },
        "watched_movies": [],
        "user_ratings": {},
    }


# Small helper: normalize text so comparisons are consistent.
def normalize_text(value):
    return " ".join(value.strip().casefold().split())


# Wrapper around input() so we handle Ctrl+C / Ctrl+D in one place.
def safe_input(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt) as error:
        raise UserExit from error


# Pause so the CLI doesn't fly by too fast.
def pause():
    safe_input("\nPress Enter when you are ready to continue...")


# Simple divider line for readability.
def print_line(character="=", length=72):
    print(character * length)


# Welcome screen at the start of the program.
def print_banner():
    print()

    print_line()

    print("Lights, camera, CineMatch!")

    print_line()

    print("Welcome to your personal movie recommendation space.")
    print("Tell CineMatch what you enjoy, what you avoid, and what you have already watched.")
    print("Then the program will build a taste profile and suggest unseen movies for you.")
    print()
    print("Helpful tip: in most menus you can type either the number or the name itself.")


# Section title so the output is easier to scan.
def print_heading(title):
    print()

    print(title)

    print("-" * len(title))


# This checks whether the movie database has the correct structure.
def validate_movie_database(movies):
    # The database must be a non-empty list.
    if not isinstance(movies, list) or not movies:
        raise ValueError("The movie database must contain a non-empty list of movies.")

    # We use this set to make sure movie titles are not duplicated.
    seen_titles = set()

    # We go through each movie one by one to check it carefully.
    for index, movie in enumerate(movies, start=1):
        # Every movie should be stored as a dictionary.
        if not isinstance(movie, dict):
            raise ValueError(f"Movie entry {index} is not a valid dictionary.")

        # These are the fields every movie must have.
        required_fields = {"title", "genres", "runtime", "mood", "rating"}

        # This finds any fields that are missing.
        missing_fields = required_fields - movie.keys()

        # If something is missing, we stop with a clear message.
        if missing_fields:
            missing_text = ", ".join(sorted(missing_fields))
            raise ValueError(f"Movie entry {index} is missing fields: {missing_text}.")

        # These variables make the later checks easier to read.
        title = movie["title"]
        genres = movie["genres"]
        runtime = movie["runtime"]
        mood = movie["mood"]
        rating = movie["rating"]

        # The title must be a non-empty string.
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Movie entry {index} has an invalid title.")

        # We normalize the title so duplicate checking is fair.
        normalized_title = normalize_text(title)

        # If the title already exists, the database is inconsistent.
        if normalized_title in seen_titles:
            raise ValueError(f"Duplicate movie title found: {title.strip()}.")

        # We remember this title so we can catch duplicates later.
        seen_titles.add(normalized_title)

        # Genres must be a non-empty list of non-empty strings.
        valid_genres = (
            isinstance(genres, list)
            and genres
            and all(isinstance(genre, str) and genre.strip() for genre in genres)
        )
        if not valid_genres:
            raise ValueError(f"Movie '{title}' has an invalid genres list.")

        # Runtime must be a positive whole number.
        if isinstance(runtime, bool) or not isinstance(runtime, int) or runtime <= 0:
            raise ValueError(f"Movie '{title}' has an invalid runtime.")

        # Mood must be a non-empty string.
        if not isinstance(mood, str) or not mood.strip():
            raise ValueError(f"Movie '{title}' has an invalid mood.")

        # Rating must be a number from 0 to 10.
        if isinstance(rating, bool) or not isinstance(rating, (int, float)) or not 0 <= float(rating) <= 10:
            raise ValueError(f"Movie '{title}' has an invalid rating.")

        # These clean-up steps keep the data neat after validation.
        movie["title"] = title.strip()
        movie["genres"] = [genre.strip() for genre in genres]
        movie["mood"] = mood.strip()
        movie["rating"] = round(float(rating), 1)


# This loads the movie database from the JSON file.
def load_movies(file_path):
    # If the file is missing, we stop with a clear message.
    if not file_path.exists():
        raise FileNotFoundError(f"Could not find the movie database: {file_path.name}")

    try:
        # We open the file using UTF-8 so text reads correctly.
        with file_path.open("r", encoding="utf-8") as file:
            # We turn the JSON text into Python data.
            movies = json.load(file)
    except JSONDecodeError as error:
        # If the JSON structure is broken, we explain that clearly.
        raise ValueError(f"The movie database contains invalid JSON: {error}") from error
    except OSError as error:
        raise OSError(f"Could not read the movie database file: {error}") from error

    # We validate the data before using it.
    validate_movie_database(movies)

    # We return the cleaned and validated movie list.
    return movies


# This cleans up a list of text values like movie titles or genres.
def sanitize_title_list(values):
    # If the value is not a list, we return an empty list.
    if not isinstance(values, list):
        return []

    # This will hold the cleaned result.
    cleaned = []

    # This helps us avoid duplicates.
    seen = set()

    # We go through each item in the list.
    for item in values:
        # We only keep non-empty strings.
        if not isinstance(item, str) or not item.strip():
            continue

        # We normalize the text so duplicate checking is more reliable.
        normalized = normalize_text(item)

        # If we already kept this item before, we skip it.
        if normalized in seen:
            continue

        # We remember the cleaned item.
        seen.add(normalized)

        # We save the stripped version of the text.
        cleaned.append(item.strip())

    # We return the cleaned list.
    return cleaned


# This cleans up saved movie ratings.
def sanitize_ratings(values):
    # If the saved value is not a dictionary, we return an empty one.
    if not isinstance(values, dict):
        return {}

    # This dictionary will hold the valid ratings.
    cleaned = {}

    # We go through each saved title and rating.
    for title, rating in values.items():
        # The title must be a non-empty string.
        if not isinstance(title, str) or not title.strip():
            continue

        # We ignore booleans because True and False are not real ratings here.
        if isinstance(rating, bool):
            continue

        # Ratings must be whole numbers from 1 to 5.
        if not isinstance(rating, int) or not 1 <= rating <= 5:
            continue

        # We keep the cleaned title and rating.
        cleaned[title.strip()] = rating

    # We return the cleaned rating dictionary.
    return cleaned


# This cleans the saved profile data.
def sanitize_profile(profile):
    # This is the fallback profile if the saved data is bad.
    default_profile = create_default_user_data()["profile"]

    # If the saved profile is not a dictionary, we use the blank one.
    if not isinstance(profile, dict):
        return default_profile

    # These lines pull out the saved values.
    name = profile.get("name", "")
    liked_genres = sanitize_title_list(profile.get("liked_genres", []))
    disliked_genres = sanitize_title_list(profile.get("disliked_genres", []))
    preferred_mood = profile.get("preferred_mood")
    max_runtime = profile.get("max_runtime")

    # Name must be a string.
    if not isinstance(name, str):
        name = ""

    # Mood must be a non-empty string or None.
    if not isinstance(preferred_mood, str) or not preferred_mood.strip():
        preferred_mood = None
    else:
        preferred_mood = preferred_mood.strip()

    # Max runtime must be a positive whole number or None.
    if isinstance(max_runtime, bool) or not isinstance(max_runtime, int) or max_runtime <= 0:
        max_runtime = None

    # We do not allow a genre to be both liked and disliked.
    overlap = {normalize_text(genre) for genre in liked_genres} & {
        normalize_text(genre) for genre in disliked_genres
    }

    # If overlap exists, we remove those genres from the disliked list.
    if overlap:
        disliked_genres = [
            genre for genre in disliked_genres if normalize_text(genre) not in overlap
        ]

    # We return the cleaned profile.
    return {
        "name": name.strip(),
        "liked_genres": liked_genres,
        "disliked_genres": disliked_genres,
        "preferred_mood": preferred_mood,
        "max_runtime": max_runtime,
    }


# This loads the saved user data file if it exists.
def load_user_data(file_path):
    # This is the blank starting point if no save file exists.
    default_data = create_default_user_data()

    # If there is no save file yet, we just return blank user data.
    if not file_path.exists():
        return default_data

    try:
        # We open the save file and read the JSON inside it.
        with file_path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (JSONDecodeError, OSError):
        # If something goes wrong, we do not crash the program.
        print("Warning: saved user data could not be read, so a fresh profile will be used.")
        return default_data

    # If the loaded object is not a dictionary, we reset it.
    if not isinstance(loaded, dict):
        return default_data

    # We clean each saved part before using it.
    profile = sanitize_profile(loaded.get("profile", {}))
    watched_movies = sanitize_title_list(loaded.get("watched_movies", []))
    user_ratings = sanitize_ratings(loaded.get("user_ratings", {}))

    # This helps us compare watched titles safely.
    watched_lookup = {normalize_text(title): title for title in watched_movies}

    # If a movie has a rating, it should also count as watched.
    for title in list(user_ratings):
        normalized = normalize_text(title)
        if normalized not in watched_lookup:
            watched_movies.append(title)
            watched_lookup[normalized] = title

    # We return the cleaned saved data.
    return {
        "profile": profile,
        "watched_movies": watched_movies,
        "user_ratings": user_ratings,
    }


# Save the current user data to a JSON file.
def save_user_data(user_data, file_path):
    try:
        # Atomic write so we don't risk half-written JSON if the program stops mid-save.
        tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as file:
            json.dump(user_data, file, indent=2)
            file.flush()
        tmp_path.replace(file_path)
    except OSError as error:
        print(f"Error: your data could not be saved. {error}")
        return False

    return True


# This creates a fast lookup dictionary from movie title to movie data.
def build_movie_lookup(movies):
    # We normalize the title so searching is more reliable.
    return {normalize_text(movie["title"]): movie for movie in movies}


# This finds every unique genre in the database.
def get_available_genres(movies):
    # A set removes duplicates, and sorted puts the result in order.
    return sorted({genre for movie in movies for genre in movie["genres"]})


# This finds every unique mood in the database.
def get_available_moods(movies):
    # A set removes duplicates, and sorted puts the result in order.
    return sorted({movie["mood"] for movie in movies})


# This lines up old saved data with the current movie database.
def align_user_data_to_database(user_data, movies):
    # This lets us find database movies quickly by title.
    movie_lookup = build_movie_lookup(movies)

    # These are the valid genres and moods that really exist in the database.
    valid_genres = set(get_available_genres(movies))
    valid_moods = set(get_available_moods(movies))

    # We work directly with the saved profile here.
    profile = user_data["profile"]

    # We keep only genres that still exist in the database.
    profile["liked_genres"] = [
        genre for genre in profile["liked_genres"] if genre in valid_genres
    ]

    # We keep only disliked genres that still exist in the database.
    profile["disliked_genres"] = [
        genre for genre in profile["disliked_genres"] if genre in valid_genres
    ]

    # If the old mood no longer exists, we clear it.
    if profile["preferred_mood"] not in valid_moods:
        profile["preferred_mood"] = None

    # This will hold watched titles that still exist in the database.
    watched_movies = []

    # This helps us avoid duplicate watched titles.
    seen_titles = set()

    # We rebuild the watched list using database titles.
    for title in user_data["watched_movies"]:
        movie = movie_lookup.get(normalize_text(title))
        if movie is None:
            continue

        normalized_title = normalize_text(movie["title"])
        if normalized_title in seen_titles:
            continue

        seen_titles.add(normalized_title)
        watched_movies.append(movie["title"])

    # This will hold cleaned ratings that still match the database.
    user_ratings = {}

    # We rebuild the rating dictionary using database titles.
    for title, rating in user_data["user_ratings"].items():
        movie = movie_lookup.get(normalize_text(title))
        if movie is None:
            continue

        user_ratings[movie["title"]] = rating
        normalized_title = normalize_text(movie["title"])

        # Any rated movie should also appear in the watched list.
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            watched_movies.append(movie["title"])

    # We store the cleaned watched list back into user data.
    user_data["watched_movies"] = watched_movies

    # We store the cleaned ratings back into user data.
    user_data["user_ratings"] = user_ratings

    # We return the updated user data.
    return user_data


# This gives us a set of watched titles in normalized form.
def get_watched_titles_set(user_data):
    # A set is fast when we want to check if a movie is already watched.
    return {normalize_text(title) for title in user_data["watched_movies"]}


# This builds a short status line for a movie.
def format_status(movie, user_data):
    # We normalize the movie title before comparing it.
    normalized_title = normalize_text(movie["title"])

    # This gives us the user's watched movies in a fast lookup form.
    watched_titles = get_watched_titles_set(user_data)

    # If the movie is not watched yet, we say that clearly.
    if normalized_title not in watched_titles:
        return "Not watched yet"

    # We try to find the user's rating for this movie.
    rating = user_data["user_ratings"].get(movie["title"])

    # If no rating exists yet, we show that.
    if rating is None:
        return "Watched | Not rated yet"

    # If a rating exists, we show it.
    return f"Watched | Your rating: {rating}/5"


# This prints movie information in a clean list.
def display_movies(movies, user_data):
    # If the list is empty, we tell the user.
    if not movies:
        print("No movies were found for this view.")
        return

    # We print one movie at a time.
    for index, movie in enumerate(movies, start=1):
        print(f"\n{index}. {movie['title']}")
        print(f"   Genres : {', '.join(movie['genres'])}")
        print(f"   Mood   : {movie['mood']}")
        print(f"   Runtime: {movie['runtime']} minutes")
        print(f"   Rating : {movie['rating']}/10")
        print(f"   Status : {format_status(movie, user_data)}")


# This asks the user for a whole number and validates it.
def prompt_for_int(prompt, min_value, max_value, allow_blank=False, default=None, allow_clear=False):
    while True:
        # We ask the question and store the answer.
        raw_value = safe_input(prompt)

        # If the user presses Enter and blank input is allowed, we keep the default.
        if not raw_value:
            if allow_blank:
                return default
            print("Please enter a number.")
            continue

        # If the user types clear, we return None.
        if allow_clear and raw_value.casefold() in CLEAR_TOKENS:
            return None

        try:
            # We try to turn the answer into a whole number.
            number = int(raw_value)
        except ValueError:
            # If that fails, we ask again.
            print("Please enter a valid whole number.")
            continue

        # The number must stay inside the allowed range.
        if not min_value <= number <= max_value:
            print(f"Please enter a number from {min_value} to {max_value}.")
            continue

        # If everything is fine, we return the number.
        return number


# This asks for text and makes sure required text is not empty.
def prompt_for_text(prompt, default=None):
    while True:
        # This shows the old value in the prompt if one exists.
        suffix = f" [{default}]" if default else ""

        # We ask the user for text.
        value = safe_input(f"{prompt}{suffix}: ")

        # If the user typed something, we return it.
        if value:
            return value

        # If the user typed nothing but a default exists, we keep the default.
        if default is not None:
            return default

        # If blank text is not allowed, we ask again.
        print("Please type something here.")


# Print numbered options for the user.
def print_select_options(options):
    for index, option in enumerate(options, start=1):
        print(f"{index}. {option}")


# Let the user choose one option from a list.
def prompt_for_single_select(options, prompt, allow_blank=False, default=None, allow_clear=False):
    # People usually type either the number or the name.
    num_to_option = {str(index): option for index, option in enumerate(options, start=1)}
    name_to_option = {normalize_text(option): option for option in options}

    while True:
        raw_value = safe_input(prompt)

        if not raw_value:
            if allow_blank:
                return default
            print("Please choose one of the listed options.")
            continue

        if allow_clear and raw_value.casefold() in CLEAR_TOKENS:
            return None

        if raw_value in num_to_option:
            return num_to_option[raw_value]

        selected_option = name_to_option.get(normalize_text(raw_value))
        if selected_option:
            return selected_option

        print("Please choose a valid option by name or number.")


# Let the user choose multiple options from a list.
def prompt_for_multi_select(options, prompt, allow_blank=False, default=None, allow_clear=False):
    num_to_option = {str(index): option for index, option in enumerate(options, start=1)}
    name_to_option = {normalize_text(option): option for option in options}

    while True:
        raw_value = safe_input(prompt)

        if not raw_value:
            if allow_blank:
                return list(default or [])
            print("Please choose at least one option or press Enter if keeping the current value is allowed.")
            continue

        if allow_clear and raw_value.casefold() in CLEAR_TOKENS:
            return []

        values = [part.strip() for part in raw_value.split(",") if part.strip()]

        if not values:
            if allow_blank:
                return list(default or [])
            print("Please enter your choices separated by commas.")
            continue

        selected = []

        seen = set()

        invalid = []

        for value in values:
            option = num_to_option.get(value)
            if option is None:
                option = name_to_option.get(normalize_text(value))

            if option is None:
                invalid.append(value)
                continue

            normalized_option = normalize_text(option)
            if normalized_option in seen:
                continue

            seen.add(normalized_option)
            selected.append(option)

        if invalid:
            print(f"Invalid choice(s): {', '.join(invalid)}.")
            print("Use the exact option names or the numbers shown in the list.")
            continue

        return selected


# This asks a yes or no question.
def prompt_for_yes_no(prompt, default=None):
    # This small text shows the default answer in the prompt.
    default_text = ""
    if default is True:
        default_text = " [Y/n]"
    elif default is False:
        default_text = " [y/N]"

    while True:
        # We ask the user and clean the answer.
        answer = safe_input(f"{prompt}{default_text}: ").casefold()

        # If the user presses Enter, we use the default when possible.
        if not answer and default is not None:
            return default

        # These answers mean yes.
        if answer in {"y", "yes"}:
            return True

        # These answers mean no.
        if answer in {"n", "no"}:
            return False

        # If the answer is unclear, we ask again.
        print("Please enter yes or no.")


# This prints the current user profile.
def show_profile(user_data):
    # We shorten the code by storing profile in a local variable.
    profile = user_data["profile"]

    # This prints a clear heading.
    print_heading("Your Taste Profile")

    # If nothing has been filled in yet, we explain that kindly.
    if not any(
        [
            profile["name"],
            profile["liked_genres"],
            profile["disliked_genres"],
            profile["preferred_mood"],
            profile["max_runtime"],
        ]
    ):
        print("You have not built a profile yet, but that is totally okay.")
        print("Choose 'Build or update my profile' from the main menu when you are ready.")
        return

    # These lines show the saved profile details.
    print(f"Name            : {profile['name'] or 'Not set'}")
    print("Liked genres    : " + (", ".join(profile["liked_genres"]) if profile["liked_genres"] else "None"))
    print("Disliked genres : " + (", ".join(profile["disliked_genres"]) if profile["disliked_genres"] else "None"))
    print(f"Preferred mood  : {profile['preferred_mood'] or 'None'}")
    print("Max runtime     : " + (f"{profile['max_runtime']} minutes" if profile["max_runtime"] else "No limit"))
    print(f"Watched movies  : {len(user_data['watched_movies'])}")
    print(f"Rated movies    : {len(user_data['user_ratings'])}")


# This lets the user create or change the profile.
def create_or_update_profile(user_data, available_genres, available_moods):
    # We store the old profile in a shorter variable name.
    profile = user_data["profile"]

    # This heading tells the user what section they are in.
    print_heading("Build or Update Your Taste Profile")

    # These friendly lines guide the user.
    print("Let us shape your movie taste profile.")
    print("You can type option numbers, option names, or type 'clear' to remove an old choice.")

    # We ask for the user's name in a friendly way.
    name = prompt_for_text("What should CineMatch call you", default=profile["name"] or None)

    # We show all genres before asking for liked ones.
    print("\nPick from these genres:")
    print_select_options(available_genres)

    # We ask for liked genres.
    liked_genres = prompt_for_multi_select(
        available_genres,
        "\nWhich genres feel most like you? (comma-separated, Enter to keep current, or type 'clear'): ",
        allow_blank=True,
        default=profile["liked_genres"],
        allow_clear=True,
    )

    # We ask for disliked genres and make sure they do not overlap with liked genres.
    while True:
        disliked_genres = prompt_for_multi_select(
            available_genres,
            "Which genres do you usually avoid? (comma-separated, Enter to keep current, or type 'clear'): ",
            allow_blank=True,
            default=profile["disliked_genres"],
            allow_clear=True,
        )

        overlap = {normalize_text(genre) for genre in liked_genres} & {
            normalize_text(genre) for genre in disliked_genres
        }

        if overlap:
            print("A genre cannot be both liked and disliked at the same time.")
            print("Please choose the disliked genres again without overlaps.")
            continue

        break

    # We show all moods before asking for one.
    print("\nThese are the moods in the movie database:")
    print_select_options(available_moods)

    # We ask for a preferred mood.
    preferred_mood = prompt_for_single_select(
        available_moods,
        "\nWhich mood fits what you want most? (single choice, Enter to keep current, or type 'clear'): ",
        allow_blank=True,
        default=profile["preferred_mood"],
        allow_clear=True,
    )

    # We build a friendly runtime prompt based on whether a value already exists.
    if profile["max_runtime"]:
        runtime_prompt = (
            f"What is your ideal maximum runtime in minutes? (60-240, Enter to keep {profile['max_runtime']}, or type 'clear'): "
        )
    else:
        runtime_prompt = "What is your ideal maximum runtime in minutes? (60-240, Enter for no limit): "

    # We ask for the runtime preference.
    max_runtime = prompt_for_int(
        runtime_prompt,
        60,
        240,
        allow_blank=True,
        default=profile["max_runtime"],
        allow_clear=True,
    )

    # We save the updated profile back into user data.
    user_data["profile"] = {
        "name": name,
        "liked_genres": liked_genres,
        "disliked_genres": disliked_genres,
        "preferred_mood": preferred_mood,
        "max_runtime": max_runtime,
    }

    # We save the file and confirm success.
    if save_user_data(user_data, USER_DATA_FILE):
        print("\nNice. Your taste profile has been saved.")


# This searches movies by title text.
def search_by_title(movies, query):
    # We normalize the query so the search is case-insensitive.
    normalized_query = normalize_text(query)

    # We keep any movie whose title contains the search text.
    return [movie for movie in movies if normalized_query in normalize_text(movie["title"])]


# This searches movies by exact genre.
def search_by_genre(movies, genre):
    # We keep movies where the chosen genre appears in the genre list.
    return [movie for movie in movies if genre in movie["genres"]]


# This searches movies by exact mood.
def search_by_mood(movies, mood):
    # We keep movies where the mood matches exactly.
    return [movie for movie in movies if movie["mood"] == mood]


# This runs the search submenu.
def search_movies_menu(movies, user_data, available_genres, available_moods):
    while True:
        # This heading shows the user where they are.
        print_heading("Search the Movie Shelf")

        # These are the search options.
        print("1. Search by title")
        print("2. Search by genre")
        print("3. Search by mood")
        print("4. Go back to the main menu")

        # We ask which search type the user wants.
        choice = prompt_for_int("\nChoose an option (1-4): ", 1, 4)

        # This branch handles title search.
        if choice == 1:
            query = prompt_for_text("Type part or all of the movie title")
            results = search_by_title(movies, query)
            print_heading(f"Search Results for '{query}'")
            display_movies(results, user_data)
            pause()
            continue

        # This branch handles genre search.
        if choice == 2:
            print("\nAvailable genres:")
            print_select_options(available_genres)
            genre = prompt_for_single_select(available_genres, "\nChoose a genre: ")
            results = search_by_genre(movies, genre)
            print_heading(f"Movies in Genre: {genre}")
            display_movies(results, user_data)
            pause()
            continue

        # This branch handles mood search.
        if choice == 3:
            print("\nAvailable moods:")
            print_select_options(available_moods)
            mood = prompt_for_single_select(available_moods, "\nChoose a mood: ")
            results = search_by_mood(movies, mood)
            print_heading(f"Movies with Mood: {mood}")
            display_movies(results, user_data)
            pause()
            continue

        # Choice 4 exits the search menu.
        return


# This helps the user choose one movie when many partial matches are found.
def choose_movie_from_matches(matches):
    # If nothing matched, we return None.
    if not matches:
        return None

    # If only one movie matched, there is nothing extra to choose.
    if len(matches) == 1:
        return matches[0]

    # We show the matching options so the user can pick the correct one.
    print("\nI found more than one match. Please choose the correct movie:")
    for index, movie in enumerate(matches, start=1):
        print(f"{index}. {movie['title']} ({movie['runtime']} min, {movie['mood']})")

    # We ask the user which matched movie they meant.
    choice = prompt_for_int("Choose the correct movie number: ", 1, len(matches))

    # We return the chosen movie.
    return matches[choice - 1]


# This lets the user select a movie by number, full title, or partial title.
def prompt_for_movie_selection(movies, prompt, allow_blank=False, user_data=None, allow_done=False):
    # Sorting makes the list easier for the user to scan.
    sorted_movies = sorted(movies, key=lambda movie: movie["title"])

    while True:
        # We ask for the movie input.
        user_entry = safe_input(prompt)

        # Blank input only works if blank input is allowed here.
        if not user_entry:
            if allow_blank:
                return None
            print("Please enter a movie title or a movie number.")
            continue

        # We normalize the entry for safer comparison.
        normalized_entry = normalize_text(user_entry)

        # These words let the user leave a repeated flow.
        if allow_done and normalized_entry in DONE_TOKENS:
            return None

        # These words let the user ask for a full list only when needed.
        if user_data is not None and normalized_entry in LIST_TOKENS:
            print("\nHere is the current list:")
            display_movies(sorted_movies, user_data)
            continue

        # If the user typed a number, we treat it like a list number.
        if user_entry.isdigit():
            choice = int(user_entry)
            if 1 <= choice <= len(sorted_movies):
                return sorted_movies[choice - 1]
            print("That movie number is not in the list.")
            continue

        # We check for exact title matches first.
        exact_matches = [
            movie for movie in sorted_movies if normalize_text(movie["title"]) == normalized_entry
        ]
        if exact_matches:
            return exact_matches[0]

        # If there is no exact match, we look for partial title matches.
        partial_matches = [
            movie for movie in sorted_movies if normalized_entry in normalize_text(movie["title"])
        ]
        if partial_matches:
            return choose_movie_from_matches(partial_matches)

        # If nothing matched, we ask again.
        print("No movie matched that input. Please try again.")


# This marks movies as watched.
def mark_movie_as_watched(movies, user_data):
    # This heading explains the current task.
    print_heading("Mark a Movie as Watched")

    # These lines explain the faster flow.
    print("You do not need to scroll through the whole movie database each time.")
    print("Type a movie title or part of a title to search quickly.")
    print("Type 'list' if you want to see all unwatched movies.")
    print("Type 'done' if you want to stop adding watched movies.")

    # This counts how many new movies were added in this visit.
    added_count = 0

    while True:
        # We rebuild the unwatched list each loop so it stays up to date.
        unwatched_movies = [
            movie
            for movie in movies
            if normalize_text(movie["title"]) not in get_watched_titles_set(user_data)
        ]

        # If nothing is left, we explain that and stop.
        if not unwatched_movies:
            print("\nEvery movie in the database is already marked as watched.")
            return

        # We ask the user which movie they have seen.
        movie = prompt_for_movie_selection(
            unwatched_movies,
            "\nWhich movie have you already seen? ",
            user_data=user_data,
            allow_done=True,
        )

        # If the user typed done, we stop politely.
        if movie is None:
            if added_count:
                print(f"\nFinished. {added_count} movie(s) were added to your watched list.")
            else:
                print("\nNo new watched movies were added this time.")
            return

        # We normalize the movie title for safe comparison.
        normalized_title = normalize_text(movie["title"])

        # We get the watched set so we can check duplicates quickly.
        watched_titles = get_watched_titles_set(user_data)

        # If the movie is already watched, we do not add it again.
        if normalized_title in watched_titles:
            print(f"\n'{movie['title']}' is already in your watched list.")
        else:
            user_data["watched_movies"].append(movie["title"])
            added_count += 1
            if save_user_data(user_data, USER_DATA_FILE):
                print(f"\nGreat. '{movie['title']}' has been added to your watched list.")

        # We offer to rate the movie right away.
        if prompt_for_yes_no("Do you want to rate this movie now so CineMatch learns faster", default=True):
            rate_specific_movie(movie, user_data)

        # This lets the user add several watched movies in one go.
        if not prompt_for_yes_no("Do you want to add another watched movie", default=True):
            if added_count:
                print(f"\nFinished. {added_count} movie(s) were added to your watched list.")
            else:
                print("\nNo new watched movies were added this time.")
            return


# This rates one specific movie.
def rate_specific_movie(movie, user_data):
    # We normalize the title so watched checking is reliable.
    normalized_title = normalize_text(movie["title"])

    # If the movie is not already marked as watched, we add it first.
    if normalized_title not in get_watched_titles_set(user_data):
        user_data["watched_movies"].append(movie["title"])

    # We look for an old rating so the user knows what is currently saved.
    current_rating = user_data["user_ratings"].get(movie["title"])

    # If an old rating exists, we show it.
    if current_rating:
        print(f"\nCurrent rating for '{movie['title']}': {current_rating}/5")

    # We ask the user for a rating from 1 to 5.
    rating = prompt_for_int("How many stars would you give it? (1-5): ", 1, 5)

    # We save that rating.
    user_data["user_ratings"][movie["title"]] = rating

    # We save the updated file.
    if save_user_data(user_data, USER_DATA_FILE):
        print(f"Saved rating: '{movie['title']}' -> {rating}/5")


# This lets the user rate a movie from the watched list.
def rate_watched_movie(movies, user_data):
    # This heading explains the current section.
    print_heading("Rate a Watched Movie")

    # We grab the saved watched titles.
    watched_titles = user_data["watched_movies"]

    # If there are no watched movies yet, we stop here.
    if not watched_titles:
        print("You have not marked any movies as watched yet.")
        return

    # This lookup helps us connect watched titles back to the database movies.
    watched_lookup = {normalize_text(movie["title"]): movie for movie in movies}

    # This rebuilds the watched movie list using the database order and data.
    watched_movies = [
        watched_lookup[normalize_text(title)]
        for title in watched_titles
        if normalize_text(title) in watched_lookup
    ]

    # If nothing matches the database anymore, we explain that.
    if not watched_movies:
        print("Your watched list does not match the current movie database.")
        return

    # These lines explain the faster search-based flow.
    print("Type a watched movie title or part of a title to find it quickly.")
    print("Type 'list' if you want to see your full watched list first.")

    # We ask which watched movie the user wants to rate.
    movie = prompt_for_movie_selection(
        watched_movies,
        "\nWhich watched movie would you like to rate? ",
        user_data=user_data,
    )

    # We send that movie to the rating function.
    rate_specific_movie(movie, user_data)


# This shows the watched movie list.
def view_watched_movies(movies, user_data):
    # This heading explains the section.
    print_heading("Your Watched Movies")

    # We grab the saved watched titles.
    watched_titles = user_data["watched_movies"]

    # If no watched movies exist yet, we say so.
    if not watched_titles:
        print("You have not marked any movies as watched yet.")
        return

    # This lookup helps us find full movie data from a title.
    movie_lookup = build_movie_lookup(movies)

    # This rebuilds the watched movie list from the current database.
    watched_movies = [
        movie_lookup[normalize_text(title)]
        for title in watched_titles
        if normalize_text(title) in movie_lookup
    ]

    # If none of the saved watched titles match the database, we explain that.
    if not watched_movies:
        print("Your watched list does not match the current movie database.")
        return

    # We display the watched movies.
    display_movies(watched_movies, user_data)


# This clears only the watched history and ratings.
def clear_watched_data(user_data):
    # The watched list becomes empty again.
    user_data["watched_movies"] = []

    # The rating dictionary also becomes empty again.
    user_data["user_ratings"] = {}


# This clears only the profile details.
def clear_profile_data(user_data):
    # We replace the old profile with a brand new blank one.
    user_data["profile"] = create_default_user_data()["profile"]


# This resets the whole save file back to the starting state.
def reset_all_user_data(user_data):
    # We make a fresh blank data structure.
    fresh_data = create_default_user_data()

    # We replace each section one by one.
    user_data["profile"] = fresh_data["profile"]
    user_data["watched_movies"] = fresh_data["watched_movies"]
    user_data["user_ratings"] = fresh_data["user_ratings"]


# This gives the user a safe menu for deleting saved data.
def manage_saved_data(user_data):
    while True:
        # This heading shows the purpose of the menu.
        print_heading("Manage Saved Data")

        # These are the reset options.
        print("1. Clear watched movies and ratings")
        print("2. Clear profile only")
        print("3. Reset everything and start over")
        print("4. Go back to the main menu")

        # We ask which reset action the user wants.
        choice = prompt_for_int("\nChoose an option (1-4): ", 1, 4)

        # This option clears watched movies and ratings only.
        if choice == 1:
            if not user_data["watched_movies"] and not user_data["user_ratings"]:
                print("\nThere is no watched history or rating data to clear.")
                pause()
                continue

            if prompt_for_yes_no(
                "Are you sure you want to delete all watched movies and ratings",
                default=False,
            ):
                clear_watched_data(user_data)
                if save_user_data(user_data, USER_DATA_FILE):
                    print("\nYour watched movies and ratings have been cleared.")
                else:
                    print("\nYour watched movies and ratings could not be cleared because saving failed.")
            else:
                print("\nNothing was deleted.")
            pause()
            continue

        # This option clears the profile only.
        if choice == 2:
            profile = user_data["profile"]
            if not any(
                [
                    profile["name"],
                    profile["liked_genres"],
                    profile["disliked_genres"],
                    profile["preferred_mood"],
                    profile["max_runtime"],
                ]
            ):
                print("\nYour profile is already empty.")
                pause()
                continue

            if prompt_for_yes_no(
                "Are you sure you want to clear your profile details",
                default=False,
            ):
                clear_profile_data(user_data)
                if save_user_data(user_data, USER_DATA_FILE):
                    print("\nYour profile has been cleared.")
                else:
                    print("\nYour profile could not be cleared because saving failed.")
            else:
                print("\nNothing was deleted.")
            pause()
            continue

        # This option resets everything.
        if choice == 3:
            if prompt_for_yes_no(
                "Are you sure you want to delete all saved data and start over",
                default=False,
            ):
                reset_all_user_data(user_data)
                if save_user_data(user_data, USER_DATA_FILE):
                    print("\nEverything has been reset. You can start fresh now.")
                else:
                    print("\nYour data could not be reset because saving failed.")
            else:
                print("\nNothing was deleted.")
            pause()
            continue

        # Option 4 returns to the main menu.
        return


# This builds the internal taste profile that the scoring system uses.
def build_taste_profile(user_data, movie_lookup):
    # We use a short variable name for the user's profile.
    profile = user_data["profile"]

    # This dictionary stores genre scores like Thriller +5 or Romance -3.
    genre_weights = {}

    # This dictionary stores mood scores like Dark +4.
    mood_weights = {}

    # First we add the explicit liked genres.
    for genre in profile["liked_genres"]:
        genre_weights[genre] = genre_weights.get(genre, 0) + GENRE_LIKE_WEIGHT

    # Then we add the explicit disliked genres.
    for genre in profile["disliked_genres"]:
        genre_weights[genre] = genre_weights.get(genre, 0) + GENRE_DISLIKE_WEIGHT

    # If the user chose a preferred mood, we give it a positive weight.
    if profile["preferred_mood"]:
        mood = profile["preferred_mood"]
        mood_weights[mood] = mood_weights.get(mood, 0) + MOOD_PREFERENCE_WEIGHT

    # Next we fine-tune the profile using the user's movie ratings.
    for title, rating in user_data["user_ratings"].items():
        movie = movie_lookup.get(normalize_text(title))
        if movie is None:
            continue

        # This changes the weight based on the 1 to 5 rating.
        adjustment = RATING_ADJUSTMENTS[rating]

        # Each genre in that watched movie gets adjusted.
        for genre in movie["genres"]:
            genre_weights[genre] = genre_weights.get(genre, 0) + adjustment

        # The movie's mood also gets adjusted.
        mood = movie["mood"]
        mood_weights[mood] = mood_weights.get(mood, 0) + adjustment

    # We return the full taste profile.
    return {
        "genre_weights": genre_weights,
        "mood_weights": mood_weights,
        "max_runtime": profile["max_runtime"],
    }


# This scores runtime based on the user's preferred maximum runtime.
def calculate_runtime_score(runtime, max_runtime):
    # If the user did not set a runtime preference, runtime adds nothing.
    if not max_runtime:
        return 0

    # Movies within the preferred limit get a bonus.
    if runtime <= max_runtime:
        return 1

    # Movies only slightly above the limit are neutral.
    if runtime <= max_runtime + 20:
        return 0

    # Movies far above the limit get a small penalty.
    return -1


# This gives a small bonus to higher-rated movies from the database.
def calculate_rating_bonus(movie_rating):
    # Excellent films get the biggest bonus.
    if movie_rating >= 8.5:
        return 2

    # Strong films get a smaller bonus.
    if movie_rating >= 7.5:
        return 1

    # Lower-rated films get no bonus.
    return 0


# This scores one candidate movie using the taste profile.
def score_movie(movie, taste_profile):
    # These are the two weight dictionaries inside the taste profile.
    genre_weights = taste_profile["genre_weights"]
    mood_weights = taste_profile["mood_weights"]

    # We keep a list of genre matches so we can explain the result later.
    genre_matches = []

    # This starts the genre score at zero.
    genre_score = 0

    # We add up the weight for every genre in the movie.
    for genre in movie["genres"]:
        weight = genre_weights.get(genre, 0)
        genre_score += weight
        if weight:
            genre_matches.append((genre, weight))

    # We add the mood score if the movie mood exists in the taste profile.
    mood_score = mood_weights.get(movie["mood"], 0)

    # We work out the runtime score.
    runtime_score = calculate_runtime_score(movie["runtime"], taste_profile["max_runtime"])

    # We work out the quality bonus from the movie's own database rating.
    rating_bonus = calculate_rating_bonus(movie["rating"])

    # This is the total final score.
    total_score = genre_score + mood_score + runtime_score + rating_bonus

    # We return both the total and the parts that created it.
    return {
        "genre_score": genre_score,
        "mood_score": mood_score,
        "runtime_score": runtime_score,
        "rating_bonus": rating_bonus,
        "total_score": total_score,
        "genre_matches": genre_matches,
    }


# This turns a weight dictionary into a short readable summary.
def summarize_weights(weights, empty_message):
    # We only keep weights that are not zero.
    active_weights = [(name, value) for name, value in weights.items() if value != 0]

    # If no active weights exist, we return the fallback message.
    if not active_weights:
        return empty_message

    # We sort by strongest weight first.
    active_weights.sort(key=lambda item: (-abs(item[1]), -item[1], item[0]))

    # We build a short top-five summary.
    summary = [f"{name} ({value:+d})" for name, value in active_weights[:5]]

    # We join the summary items into one line.
    return ", ".join(summary)


# This finds the best unseen movies for the user.
def get_recommendations(movies, user_data, recommendation_count=DEFAULT_RECOMMENDATION_COUNT):
    # We build a fast movie lookup dictionary.
    movie_lookup = build_movie_lookup(movies)

    # We build the user's taste profile from preferences and ratings.
    taste_profile = build_taste_profile(user_data, movie_lookup)

    # We get watched titles so we can skip them.
    watched_titles = get_watched_titles_set(user_data)

    # This list will hold every recommendation candidate plus its score.
    recommendations = []

    # We score each movie in the database.
    for movie in movies:
        # Already watched movies should not be recommended again.
        if normalize_text(movie["title"]) in watched_titles:
            continue

        # We score the movie using the recommendation rules.
        score = score_movie(movie, taste_profile)

        # We store the movie and its score together.
        recommendations.append({"movie": movie, "score": score})

    # We sort from best score to worst score.
    recommendations.sort(
        key=lambda item: (
            -item["score"]["total_score"],
            -item["movie"]["rating"],
            item["movie"]["title"],
        )
    )

    # We return only the top recommendations plus the taste profile used.
    return recommendations[:recommendation_count], taste_profile


# This prints the recommendation results nicely.
def show_recommendations(movies, user_data):
    # This heading introduces the recommendation section.
    print_heading("Tonight's Best Matches")

    # We calculate the best unseen movies.
    recommendations, taste_profile = get_recommendations(movies, user_data)

    # If nothing can be recommended, we explain why.
    if not recommendations:
        print("No recommendations are available because every movie in the database is already watched.")
        return

    # These lines explain the current strongest taste signals.
    print(
        "Top genre weights : "
        + summarize_weights(taste_profile["genre_weights"], "No strong genre weights yet")
    )
    print(
        "Top mood weights  : "
        + summarize_weights(taste_profile["mood_weights"], "No strong mood weights yet")
    )
    print(
        "Runtime preference: "
        + (f"Up to {taste_profile['max_runtime']} minutes" if taste_profile["max_runtime"] else "No runtime limit set")
    )

    # We print each recommendation with its score breakdown.
    for index, item in enumerate(recommendations, start=1):
        movie = item["movie"]
        score = item["score"]

        print(f"\n{index}. {movie['title']} | Total Score: {score['total_score']}")
        print(f"   Genres : {', '.join(movie['genres'])}")
        print(f"   Mood   : {movie['mood']} | Runtime: {movie['runtime']} min | Rating: {movie['rating']}/10")
        print(
            "   Breakdown: "
            f"genres {score['genre_score']:+d}, "
            f"mood {score['mood_score']:+d}, "
            f"runtime {score['runtime_score']:+d}, "
            f"quality {score['rating_bonus']:+d}"
        )

        # If genre matches exist, we show them.
        if score["genre_matches"]:
            match_text = ", ".join(
                f"{genre} ({weight:+d})" for genre, weight in score["genre_matches"]
            )
            print(f"   Strong matches: {match_text}")
            continue

        # If there are no genre matches but mood helped, we explain that.
        if score["mood_score"]:
            print(f"   Strong matches: mood {movie['mood']} ({score['mood_score']:+d})")
            continue

        # If nothing personal matched strongly, we still explain the ranking.
        print("   Strong matches: mainly ranked by runtime and overall quality.")


# This prints the main menu.
def show_main_menu():
    # The heading gives the menu a friendly feel.
    print_heading("Your Movie Desk")

    # These are the main actions the user can choose.
    print("1. Browse all movies")
    print("2. Search the collection")
    print("3. Build or update my profile")
    print("4. View my profile")
    print("5. Mark watched movies")
    print("6. Rate a watched movie")
    print("7. View watched movies")
    print("8. Get recommendations")
    print("9. Manage saved data")
    print("10. Save and exit")


# This prints a friendly message after data loading.
def print_startup_message(user_data, movies):
    # We read the saved name from the profile.
    profile_name = user_data["profile"]["name"]

    # If the user has a saved name, we greet them personally.
    if profile_name:
        print(f"\nWelcome back, {profile_name}. Your movie desk is ready.")
    else:
        print("\nWelcome, movie explorer. You can build your taste profile from the menu whenever you are ready.")

    # These lines summarize the current saved state.
    print(f"The database is loaded with {len(movies)} movies.")
    print(
        f"You currently have {len(user_data['watched_movies'])} watched movie(s) and "
        f"{len(user_data['user_ratings'])} saved rating(s)."
    )


# This is the main function that runs the full program.
def main():
    # We show the welcome banner first.
    print_banner()

    try:
        # We load the movie database.
        movies = load_movies(MOVIES_FILE)
    except (FileNotFoundError, ValueError) as error:
        # If loading fails, we explain the problem and stop.
        print(f"\nError: {error}")
        return

    # We load any saved user data.
    user_data = load_user_data(USER_DATA_FILE)

    # We clean that user data against the current movie database.
    user_data = align_user_data_to_database(user_data, movies)

    # These lists are used in menus for genre and mood choices.
    available_genres = get_available_genres(movies)
    available_moods = get_available_moods(movies)

    # We show a short startup summary.
    print_startup_message(user_data, movies)

    try:
        while True:
            # We show the main menu each loop.
            show_main_menu()

            # We ask what the user wants to do.
            choice = prompt_for_int("\nChoose an option (1-10): ", 1, 10)

            # This option shows every movie.
            if choice == 1:
                print_heading("All Movies in the Database")
                display_movies(sorted(movies, key=lambda movie: movie["title"]), user_data)
                pause()
                continue

            # This option opens the search menu.
            if choice == 2:
                search_movies_menu(movies, user_data, available_genres, available_moods)
                continue

            # This option builds or updates the user's profile.
            if choice == 3:
                create_or_update_profile(user_data, available_genres, available_moods)
                pause()
                continue

            # This option shows the current profile.
            if choice == 4:
                show_profile(user_data)
                pause()
                continue

            # This option marks watched movies.
            if choice == 5:
                mark_movie_as_watched(movies, user_data)
                pause()
                continue

            # This option lets the user rate a watched movie.
            if choice == 6:
                rate_watched_movie(movies, user_data)
                pause()
                continue

            # This option shows the watched list.
            if choice == 7:
                view_watched_movies(movies, user_data)
                pause()
                continue

            # This option shows recommendations.
            if choice == 8:
                show_recommendations(movies, user_data)
                pause()
                continue

            # This option opens the saved-data management menu.
            if choice == 9:
                manage_saved_data(user_data)
                continue

            # Option 10 saves data and exits.
            if save_user_data(user_data, USER_DATA_FILE):
                print("\nYour data has been saved.")
            print("Thanks for spending time with CineMatch. See you next time.")
            return
    except UserExit:
        # If the user closes input suddenly, we still try to save before leaving.
        print("\n\nSession closed. Saving your data before exit...")
        if save_user_data(user_data, USER_DATA_FILE):
            print("Saved. Goodbye.")
        else:
            print("Could not save. Goodbye.")


# This line runs main() only when the file is started directly.
if __name__ == "__main__":
    main()
