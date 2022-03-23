from aevs import AEVS


if __name__ == "__main__":
    scraper = AEVS()

    scraper.scrape()

    scraper._dispose()
