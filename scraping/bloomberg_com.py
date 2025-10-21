from scraping.utils import  get_soup_from_url


def bloomberg_com():

    #soup = get_soup_from_file("bloomberg")

    soup = get_soup_from_url("https://www.reuters.com/business/finance/")

    articles = []

    # Find all elements with class that starts with 'story-collection-module__list-item'
    cards = soup.select('[class^="story-collection-module__list-item"]')

    for card in cards:
        # Find the headline link within each story item
        headline_link = card.find('a', attrs={'data-testid': 'Heading'})
        if headline_link:
            articles.append(dict(
                headline=headline_link.text,
                link="https://www.reuters.com" + headline_link['href']
            ))
    return articles
