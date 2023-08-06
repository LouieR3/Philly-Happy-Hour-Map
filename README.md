# Philly Happy Hours Deals (Mappy Hour) Version 0.4

## ABOUT
Mappy Hour is the creation of Louie and Ava to give people a better way to find the best bars near them for happy hour, with information and analysis on the bars and their deals, and displaying all of that information on a clean map.

## Center City Sips Map
This map displays all bars participating in Center City Sips for 2023, lists the bar, the bar's website, the link to the bar on Center City District's website, and the bar's specific Sips deal offerings. You can also see what we consider to be the best deals offered across the city, based on the difference between the price of the items on a bar's Sips menu, compared to the price of that item on their normal menu. This lets you know where you can find where you can get the best bang for your buck this summer.

## How it is done
To do this, I used Python and Beautiful Soup to scrape the Center City District Sips website with the list of bars, their links to the CCD Sips specific page on that bar, and their addresses. (Version 0.1)
I then used geopy and Nominatim to geocode each address so I could plot their latitude and longitudes and created the map with folium. (Version 0.2)
I then used selenium's web driver to go through the list of links of the bars on the CCD Sips page to retrieve the specific bar information found in the pop up that comes up when you open up the page for a specific bar. This allowed me to retrieve the bar's own website and the listed deals they were offering for cocktails, wine, beer, and appetizers. (Version 0.3)
With that information, I used the yelpapi to get the information from each bar from yelp, including the menu prices they had listed. (Version 0.4)

## Happy Hour Map
UNDER CONSTRUCTION
