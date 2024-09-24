from themoviedb import TMDb
from themoviedb import aioTMDb
import asyncio

tmdb = TMDb(key="18851387da455b4f46805f27237a82db")
# or: tmdb = aioTMDb(key="18851387da455b4f46805f27237a82db", language="pt-BR", region="BR")

# movies = tmdb.movies().top_rated()
# for movie in movies:
#     print(movie)

async def main():
    tmdb = aioTMDb(key="18851387da455b4f46805f27237a82db")
    # movies = await tmdb.search().movies("bird box")
    # movie_id = movies[0].id  # get first result
    # movie = await tmdb.movie(movie_id).details(append_to_response="credits,external_ids,images,videos")
    # print(movie.title, movie.year)
    # print(movie.popularity)
    # print(movie.runtime)
    # print(movie.release_date)
    # print(movie.images)
    # # print()
    # # print(movie.poster_url)
    # print()
    # print(movie.external_ids)
    # print()
    # print(movie.external_ids.imdb_url) # type: ignore
    # for person in movie.credits.cast: # type: ignore
    #     print(person.name, person.character)
    # print()
    # print()

    image_url = "https://image.tmdb.org/t/p/w300_and_h450_bestv2"

    actors = await tmdb.search().people("Machine Gun Kelly")
    actor_id = actors[0].id
    filmography = await tmdb.person(actor_id).movie_credits()
    print(actor_id)
    details = await tmdb.person(actor_id).details()
    print(details)
    print(details.popularity)
    print(details.profile_path)
    for movie in filmography.cast:
        print(movie)
        print()
    # Filter out uncredited and archive footage
    filmography.cast = [movie for movie in filmography.cast if "(uncredited)" not in movie.character and "(archive footage)" not in movie.character]

asyncio.run(main())