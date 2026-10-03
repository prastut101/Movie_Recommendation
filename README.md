# 🎬 Movie Recommendation System

A web-based **Movie Recommendation System** built with **Python, Flask, Machine Learning, and the TMDB API**.

The system uses a **content-based recommendation approach** to recommend movies based on their similarity to a selected movie. Movie information such as posters, backdrops, ratings, release dates, and descriptions is retrieved from **The Movie Database (TMDB) API**.

The application provides a modern, Netflix-inspired interface with movie search, genre browsing, collections, pagination, and personalized recommendations.

---

## 🚀 Features

- 🎬 Content-based movie recommendation system
- 🔎 Movie search
- 🎭 Genre-based movie browsing
- 📚 Movie collections
- ⭐ TMDB ratings
- 📅 Movie release dates
- 📝 Movie descriptions
- 🖼️ Dynamic movie posters and backdrops
- 🎞️ Recommended movies
- 📄 Pagination
- 🌙 Netflix-inspired dark user interface
- 📱 Responsive web design
- ⚡ Optimized similarity data for faster deployment
- ☁️ Vercel deployment support
- 🔐 Environment-variable based TMDB API configuration

---

## 🧠 How the Recommendation System Works

This project uses **Content-Based Filtering**.

Movies are represented using information such as:

- Genres
- Keywords
- Cast
- Director
- Movie overview

These features are combined into a single text representation called **tags**.

The text data is then converted into numerical vectors using:

```python
CountVectorizer(
    max_features=5000,
    stop_words="english"
)
