from themoviedb import aioTMDb
import asyncio

async def get_actor_filmography(tmdb, actor_name):
    actors = await tmdb.search().people(actor_name)
    if actors:
        actor_id = actors[0].id
        filmography = await tmdb.person(actor_id).movie_credits()
        # Filter out uncredited and archive footage
        filmography.cast = [movie for movie in filmography.cast if "(uncredited)" not in movie.character and "(archive footage)" not in movie.character]
        return actor_id, filmography.cast
    return None, []

async def find_connection(tmdb, actor1_name, actor2_name):
    # Get filmographies
    actor1_id, actor1_films = await get_actor_filmography(tmdb, actor1_name)
    actor2_id, actor2_films = await get_actor_filmography(tmdb, actor2_name)

    if not actor1_id or not actor2_id:
        print("One or both actors not found.")
        return

    # Find direct connection
    actor1_movies = {movie.id: movie for movie in actor1_films}
    actor2_movies = {movie.id: movie for movie in actor2_films}

    common_movies = set(actor1_movies.keys()) & set(actor2_movies.keys())
    if common_movies:
        for movie_id in common_movies:
            movies = await tmdb.search().movies(actor1_movies[movie_id].title)
            movie_id = movies[0].id  # get first result
            movie = await tmdb.movie(movie_id).details(append_to_response="credits,external_ids,images,videos")
            if movie.runtime > 60:
                print(f"Direct connection found: {actor1_name} and {actor2_name} both starred in {actor1_movies[movie_id].title}")
                # print(actor1_movies[movie_id].vote_count)
        return

    # Find connection through co-stars
    actor1_co_stars = {}
    for movie in actor1_films:
        details = await tmdb.movie(movie.id).details(append_to_response="credits")
        for person in details.credits.cast:
            if person.id != actor1_id and "(uncredited)" not in person.character and "(archive footage)" not in person.character:
                if person.id not in actor1_co_stars:
                    actor1_co_stars[person.id] = []
                actor1_co_stars[person.id].append(details.title)

    actor2_co_stars = {}
    for movie in actor2_films:
        details = await tmdb.movie(movie.id).details(append_to_response="credits")
        for person in details.credits.cast:
            if person.id != actor2_id and "(uncredited)" not in person.character and "(archive footage)" not in person.character:
                if person.id not in actor2_co_stars:
                    actor2_co_stars[person.id] = []
                actor2_co_stars[person.id].append(details.title)

    common_co_stars = set(actor1_co_stars.keys()) & set(actor2_co_stars.keys())
    if common_co_stars:
        for co_star_id in common_co_stars:
            co_star_name = (await tmdb.person(co_star_id)).name
            print(f"Indirect connection found: {actor1_name} and {actor2_name} are both connected through {co_star_name}")
            print(f"{actor1_name} movies with {co_star_name}: {', '.join(actor1_co_stars[co_star_id])}")
            print(f"{actor2_name} movies with {co_star_name}: {', '.join(actor2_co_stars[co_star_id])}")
        return

    print("No connection found between the two actors.")

async def main():
    tmdb = aioTMDb(key="18851387da455b4f46805f27237a82db")
    actor1_name = "Leonardo DiCaprio"
    actor2_name = "Machine Gun Kelly"
    await find_connection(tmdb, actor1_name, actor2_name)

asyncio.run(main())