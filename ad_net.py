import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")


import os, enum, json, time
from requests import get
from bs4 import BeautifulSoup as BS4


CURRENT_YEAR = time.strftime("%Y")


class LinksEnum(enum.Enum):
    base = "https://www.auto-data.net"
    entry = "https://www.auto-data.net/en/allbrands"


class AD_NET:
    def __init__(self):
        if 'data.json' in os.listdir():
            with open('data.json', 'r') as f:
                self.indexed = json.load(f)
        else:
            self.indexed = {}

        self._current_make = None
        self._current_model = None
        self._current_generation = None
        self._current_variant = None

        self._break = None


    def scrape(self, ):
        soup = BS4(get(LinksEnum.entry.value).text, 'html.parser')

        _el_cars = soup.find_all(class_='marki_blok')
        cars = [(
                    c.find('strong').text,
                    c.get('href'),
                ) for c in _el_cars]

        for i, car in enumerate(cars):
            self._current_make = car[0]

            self.indexed[self._current_make] = {}
            logging.info(f'Scraping [{i+1}/{len(cars)}] {self._current_make}')

            self._scrape_make(LinksEnum.base.value+car[1])

            self._write_json()


    def _scrape_make(self, link: str):
        soup = BS4(get(link).text, 'html.parser')

        _el_models = soup.find_all(class_='modeli')
        models = [(
                    m.find('strong').text,
                    m.get('href'),
                ) for m in _el_models]

        for i, model in enumerate(models):
            self._current_model = model[0]

            self.indexed[self._current_make][self._current_model] = {}
            logging.info(f'   [{i+1}/{len(models)}] {self._current_model}')

            self._scrape_model(LinksEnum.base.value+model[1])


    def _scrape_model(self, link: str):
        soup = BS4(get(link).text, 'html.parser')

        table = soup.find(class_='generr')
        _el_generations = table.find_all(class_=lambda c: c and any(x in c for x in ['lgreen', 'lred']))
        _el_generations = [g for g in _el_generations if g.find(class_=lambda c: c and any(x in c for x in ['cur', 'end'])) is not None]
        generations = [(
                        g.find('strong').text,
                        g.find(class_=lambda c: c and any(x in c for x in ['cur', 'end'])).text,
                        g.find('a').get('href'),
                    ) for g in _el_generations]

        for i, generation in enumerate(generations):
            self._current_generation = generation[0]

            self.indexed[self._current_make][self._current_model][self._current_generation] = {}

            fromto = generation[1].split(' - ')
            self.indexed[self._current_make][self._current_model][self._current_generation]['from'] = int(fromto[0])
            self.indexed[self._current_make][self._current_model][self._current_generation]['to'] = int(fromto[1]) if fromto[1] else CURRENT_YEAR

            logging.info(f'      [{i+1}/{len(generations)}] {self._current_generation}')

            self._scrape_generation(LinksEnum.base.value+generation[2])


    def _scrape_generation(self, link: str):
        soup = BS4(get(link).text, 'html.parser')

        table = soup.find(class_='carlist')
        _el_variants = table.find_all(class_=lambda c: c and any(x in c for x in ['lgreen', 'lred']))
        variants = [(
                        g.find(class_='tit').text,
                        g.find(class_=lambda c: c and any(x in c for x in ['cur', 'end'])).text,
                        g.find('a').get('href'),
                    ) for g in _el_variants]

        for i, variant in enumerate(variants):
            self._current_variant = variant[0]

            self.indexed[self._current_make][self._current_model][self._current_generation][self._current_variant] = {}

            fromto = variant[1].split(' - ')
            self.indexed[self._current_make][self._current_model][self._current_generation][self._current_variant]['from'] = int(fromto[0])
            self.indexed[self._current_make][self._current_model][self._current_generation][self._current_variant]['to'] = int(fromto[1]) if fromto[1] else CURRENT_YEAR

            logging.info(f'         [{i+1}/{len(variants)}] {self._current_variant}')

            # self._scrape_variant(LinksEnum.base.value+variant[2])


    def _scrape_variant(self, link: str):
        pass


    def _write_json(self, ):
        with open('data.json', 'w') as f:
            json.dump(self.indexed, f, indent=2)
