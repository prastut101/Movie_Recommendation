from flask import Flask, render_template, request
import pickle
import os
import math
import requests


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)


# =========================================================
# LOAD ML MODEL DATA
# =========================================================

with open("movies.pkl", "rb") as file:
    movies = pickle.load(file)

with open("similarity.pkl", "rb") as file:
    similarity = pickle.load(file)


# =========================================================
# TMDB CONFIGURATION
# =========================================================

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB_BASE_URL = "https://api.themoviedb.org/3"

TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

TMDB_BACKDROP_URL = "https://image.tmdb.org/t/p/original"


# =========================================================
# TMDB REQUEST FUNCTION
# =========================================================

def tmdb_request(endpoint, params=None):

    if not TMDB_API_KEY:
        print("ERROR: TMDB_API_KEY is not set.")
        return {}

    if params is None:
        params = {}

    params["api_key"] = TMDB_API_KEY

    try:

        response = requests.get(
            TMDB_BASE_URL + endpoint,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        print("TMDB API Error:", error)

        return {}


# =========================================================
# GET MOVIE FROM TMDB
# =========================================================

def get_tmdb_movie(title):

    data = tmdb_request(
        "/search/movie",
        {
            "query": title,
            "language": "en-US",
            "include_adult": False
        }
    )

    results = data.get("results", [])

    if not results:
        return None

    title_lower = title.strip().lower()

    # First try exact title match
    for movie in results:

        tmdb_title = movie.get("title", "").strip().lower()

        if tmdb_title == title_lower:
            return movie

    # Otherwise use first result
    return results[0]


# =========================================================
# FORMAT TMDB MOVIE
# =========================================================

def format_tmdb_movie(movie):

    if not movie:
        return None

    poster_path = movie.get("poster_path")

    backdrop_path = movie.get("backdrop_path")

    release_date = movie.get("release_date", "")

    # IMPORTANT:
    # These are plain URLs, NOT Markdown links.

    if poster_path:

        poster_url = TMDB_IMAGE_URL + poster_path

    else:

        poster_url = "/static/no-poster.png"


    if backdrop_path:

        backdrop_url = TMDB_BACKDROP_URL + backdrop_path

    else:

        backdrop_url = None


    return {
        "id": movie.get("id"),

        "title": movie.get(
            "title",
            "Unknown"
        ),

        "overview": movie.get(
            "overview",
            "No description available."
        ),

        "rating": round(
            movie.get("vote_average", 0),
            1
        ),

        "release_date": release_date,

        "year": (
            release_date[:4]
            if release_date
            else ""
        ),

        "poster": poster_url,

        "backdrop": backdrop_url
    }


# =========================================================
# ENRICH MOVIES WITH TMDB DATA
# =========================================================

def enrich_movies(movie_titles):

    results = []

    for title in movie_titles:

        movie = get_tmdb_movie(title)

        if movie:

            formatted_movie = format_tmdb_movie(movie)

            if formatted_movie:

                results.append(formatted_movie)

        else:

            # Fallback if TMDB cannot find the movie

            results.append(
                {
                    "id": None,

                    "title": title,

                    "overview":
                        "No description available.",

                    "rating": 0,

                    "release_date": "",

                    "year": "",

                    "poster":
                        "/static/no-poster.png",

                    "backdrop": None
                }
            )

    return results


# =========================================================
# ML RECOMMENDATION FUNCTION
# =========================================================

def recommend(movie, limit=50):

    movie = movie.strip()

    if not movie:

        return []


    # Convert title column to string
    # and perform case-insensitive matching

    title_column = movies["title"].astype(str)

    matches = movies[
        title_column.str.strip().str.lower()
        == movie.lower()
    ]


    # Movie doesn't exist in our ML dataset

    if matches.empty:

        return []


    # Get index of selected movie

    movie_index = matches.index[0]


    # Get similarity scores

    distances = similarity[movie_index]


    # Sort movies by similarity

    movies_list = sorted(
        list(enumerate(distances)),
        reverse=True,
        key=lambda x: x[1]
    )


    # Remove the movie itself
    # and take the requested number

    movies_list = movies_list[
        1:limit + 1
    ]


    recommended_titles = []


    for index, score in movies_list:

        title = movies.iloc[index]["title"]

        if title not in recommended_titles:

            recommended_titles.append(title)


    # Get TMDB information for posters, ratings etc.

    return enrich_movies(recommended_titles)


# =========================================================
# SEARCH MOVIES DIRECTLY ON TMDB
# =========================================================

def search_tmdb(query):

    data = tmdb_request(
        "/search/movie",
        {
            "query": query,
            "language": "en-US",
            "include_adult": False,
            "page": 1
        }
    )

    results = data.get("results", [])


    formatted_results = []


    for movie in results[:20]:

        formatted_movie = format_tmdb_movie(movie)

        if formatted_movie:

            formatted_results.append(
                formatted_movie
            )


    return formatted_results


# =========================================================
# TMDB GENRES
# =========================================================

GENRES = {

    "action": 28,

    "adventure": 12,

    "animation": 16,

    "comedy": 35,

    "crime": 80,

    "documentary": 99,

    "drama": 18,

    "family": 10751,

    "fantasy": 14,

    "history": 36,

    "horror": 27,

    "music": 10402,

    "mystery": 9648,

    "romance": 10749,

    "science fiction": 878,

    "thriller": 53,

    "war": 10752,

    "western": 37
}


# =========================================================
# DISCOVER MOVIES BY GENRE
# =========================================================

def discover_genre(genre_name):

    genre_id = GENRES.get(
        genre_name.lower().strip()
    )

    if not genre_id:

        return []


    data = tmdb_request(
        "/discover/movie",
        {
            "with_genres": genre_id,

            "sort_by":
                "popularity.desc",

            "language":
                "en-US",

            "include_adult":
                False,

            "page":
                1
        }
    )


    results = data.get(
        "results",
        []
    )


    formatted_results = []


    for movie in results:

        formatted_movie = format_tmdb_movie(
            movie
        )

        if formatted_movie:

            formatted_results.append(
                formatted_movie
            )


    return formatted_results


# =========================================================
# GET MOVIE COLLECTION / PARTS
# =========================================================

def get_collection(movie_id):

    if not movie_id:

        return []


    data = tmdb_request(
        f"/movie/{movie_id}",
        {
            "language": "en-US",

            "append_to_response":
                "belongs_to_collection"
        }
    )


    collection = data.get(
        "belongs_to_collection"
    )


    if not collection:

        return []


    collection_id = collection.get(
        "id"
    )


    if not collection_id:

        return []


    collection_data = tmdb_request(
        f"/collection/{collection_id}",
        {
            "language": "en-US"
        }
    )


    parts = collection_data.get(
        "parts",
        []
    )


    # Sort by release date

    parts = sorted(
        parts,
        key=lambda x:
            x.get("release_date", "")
    )


    formatted_parts = []


    for movie in parts:

        formatted_movie = format_tmdb_movie(
            movie
        )

        if formatted_movie:

            formatted_parts.append(
                formatted_movie
            )


    return formatted_parts


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/", methods=["GET", "POST"])
def home():

    recommendations = []

    search_results = []

    parts = []

    hero = None

    query = ""


    # -----------------------------------------------------
    # GET PAGE NUMBER
    # -----------------------------------------------------

    page = request.args.get(
        "page",
        1,
        type=int
    )


    # -----------------------------------------------------
    # GET SEARCH QUERY
    # -----------------------------------------------------

    if request.method == "POST":

        query = request.form.get(
            "movie",
            ""
        ).strip()

    else:

        query = request.args.get(
            "query",
            ""
        ).strip()


    # -----------------------------------------------------
    # PROCESS SEARCH
    # -----------------------------------------------------

    if query:

        # First try our ML recommender

        recommendations = recommend(
            query,
            limit=50
        )


        # -------------------------------------------------
        # IF MOVIE EXISTS IN ML DATASET
        # -------------------------------------------------

        if recommendations:

            original_movie = get_tmdb_movie(
                query
            )


            if original_movie:

                hero = format_tmdb_movie(
                    original_movie
                )


                # Get Part 1 / Part 2 / Part 3 etc.

                parts = get_collection(
                    original_movie.get("id")
                )


        # -------------------------------------------------
        # IF MOVIE DOES NOT EXIST IN ML DATASET
        # -------------------------------------------------

        else:

            query_lower = query.lower().strip()


            # Check if user searched for a genre

            if query_lower in GENRES:

                search_results = discover_genre(
                    query_lower
                )


                if search_results:

                    hero = search_results[0]


            # Otherwise search TMDB directly

            else:

                search_results = search_tmdb(
                    query
                )


                if search_results:

                    hero = search_results[0]


                    # Check whether TMDB result exists
                    # in our ML dataset

                    hero_title = hero["title"]


                    local_match = movies[
                        movies["title"]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        ==
                        hero_title.lower()
                    ]


                    if not local_match.empty:

                        recommendations = recommend(
                            hero_title,
                            limit=50
                        )


                    # Get movie collection

                    parts = get_collection(
                        hero["id"]
                    )


    # =====================================================
    # PAGINATION
    # =====================================================

    movies_per_page = 10


    total_movies = len(
        recommendations
    )


    total_pages = max(
        1,
        math.ceil(
            total_movies /
            movies_per_page
        )
    )


    # Prevent invalid pages

    page = max(
        1,
        min(
            page,
            total_pages
        )
    )


    start = (
        page - 1
    ) * movies_per_page


    end = (
        start +
        movies_per_page
    )


    paginated_recommendations = (
        recommendations[start:end]
    )


    # =====================================================
    # RENDER HTML
    # =====================================================

    return render_template(

        "index.html",

        recommendations=
            paginated_recommendations,

        search_results=
            search_results,

        hero=
            hero,

        parts=
            parts,

        query=
            query,

        page=
            page,

        total_pages=
            total_pages
    )


# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
