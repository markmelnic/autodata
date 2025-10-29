import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")


import os, enum, json, time
from requests import get
from bs4 import BeautifulSoup as BS4


CURRENT_YEAR = int(time.strftime("%Y"))


class LinksEnum(enum.Enum):
    base = "https://www.auto-data.net"
    entry = "https://www.auto-data.net/en/allbrands"


class ADNET:
    def __init__(
            self,
            output_file: str = 'output.json',
            skip_existing: bool = False,
            only_include_makes: list = [],
        ):

        self._current_make = None
        self._current_model = None
        self._current_generation = None
        self._current_variant = None

        self.skip_existing = skip_existing
        self._only_include_makes = only_include_makes
        self._output_file = output_file
        self._break = None

        if self._output_file in os.listdir():
            with open(self._output_file, 'r') as f:
                self.indexed = json.load(f)
        else:
            self.indexed = {}


    def scrape(self, ):
        soup = BS4(get(LinksEnum.entry.value).text, 'html.parser')

        _el_cars = soup.find_all(class_='marki_blok')
        cars = [(
                    c.find('strong').text,
                    c.get('href'),
                ) for c in _el_cars]

        for i, car in enumerate(cars):
            self._current_make = car[0]

            if self.skip_existing and self._current_make in self.indexed:
                continue
            elif self._only_include_makes and self._current_make not in self._only_include_makes:
                continue
            else:
                logging.info(f'Scraping [{i+1}/{len(cars)}] {self._current_make}')
                self.indexed[self._current_make] = {}

                self._scrape_make(LinksEnum.base.value+car[1])

                self._write_json()


    def _get_soup(self, link: str):
        try:
            soup = BS4(get(link).text, 'html.parser')
            return soup
        except Exception as e:
            logging.error(f'Error while fetching {link}: {e}')
            return None

    def _scrape_make(self, link: str):
        soup = self._get_soup(link)
        if not soup:
            return

        _el_models = soup.find_all(class_='modeli')
        models = [(
                    m.find('strong').text,
                    m.get('href'),
                ) for m in _el_models]

        for i, model in enumerate(models):
            self._current_model = model[0]
            logging.info(f'   [{i+1}/{len(models)}] {self._current_model}')

            self.indexed[self._current_make][self._current_model] = {}

            self._scrape_model(LinksEnum.base.value+model[1])


    def _scrape_model(self, link: str):
        soup = self._get_soup(link)
        if not soup:
            return

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
            logging.info(f'      [{i+1}/{len(generations)}] {self._current_generation}')

            self.indexed[self._current_make][self._current_model][self._current_generation] = {}

            fromto = generation[1].split(' - ')
            self.indexed[self._current_make][self._current_model][self._current_generation]['from'] = int(fromto[0])
            self.indexed[self._current_make][self._current_model][self._current_generation]['to'] = int(fromto[1]) if fromto[1] else CURRENT_YEAR


            self._scrape_generation(LinksEnum.base.value+generation[2])


    def _scrape_generation(self, link: str):
        soup = self._get_soup(link)
        if not soup:
            return

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
            self.indexed[self._current_make][self._current_model][self._current_generation][self._current_variant]['specs'] = {}

            logging.info(f'         [{i+1}/{len(variants)}] {self._current_variant}')

            self._scrape_variant(LinksEnum.base.value+variant[2])


    def _scrape_variant(self, link: str):
        soup = self._get_soup(link)
        if not soup:
            return

        # phase 1
        table = soup.find(class_='cardetailsout')
        specs = {}
        power_no_system = 0
        for row in table.find_all('tr'):
            key = row.find('th').text.lower()
            value = row.find('td', recursive=False)
            if value:
                value = value.text
            else:
                continue

            if 'body type' in key:
                specs['body_type'] = value

            elif 'seats' in key:
                specs['seats_count'] = int(value.split('-')[0].split('/')[0].strip(' '))

            elif 'doors' in key:
                specs['doors_count'] = int(value.split('-')[0].split('/')[0].strip('<').strip('>'))

            elif 'powertrain architecture' in key:
                specs['powertrain_architecture'] = value

            elif 'fuel type' in key:
                if 'gasoline' in value.lower() or 'petrol' in value.lower():
                    specs['fuel_type'] = 'gasoline'
                elif 'diesel' in value.lower():
                    specs['fuel_type'] = 'diesel'

            elif 'fuel consumption' in key:
                if not 'kg/100 km' in value:
                    if not 'fuel_consumption' in specs:
                        specs['fuel_consumption'] = {}
                    consumption = value.split(' l/100')[0].split('-')[0].replace('..', '.')
                    if len(consumption) >= 3:
                        consumption = consumption[:3]
                    if 'combined' in key:
                        specs['fuel_consumption']['combined'] = float(consumption)
                    elif 'extra urban' in key:
                        specs['fuel_consumption']['extra_urban'] = float(consumption)
                    elif 'urban' in key:
                        specs['fuel_consumption']['urban'] = float(consumption)

            elif 'acceleration 0 - 100 km/h' in key:
                acceleration = value[:-5].strip('<').strip('>').split('-')[0].replace('..', '.').split(',')[0]
                if acceleration[-1] == '.':
                    acceleration = acceleration[:-1]
                if len(acceleration) >= 3:
                    acceleration = acceleration[:3]
                specs['acceleration'] = float(acceleration)

            elif 'maximum speed' in key:
                specs['max_speed'] = int(value.split(' km/h')[0].split('-')[0].split('/')[-1].split(' ')[0])

            elif 'fuel tank capacity' in key:
                fuel_tank_capacity = value.split(' l')[0].split(' (optional')[0].split(' ')[0].split('-')[0]
                if '+' in fuel_tank_capacity:
                    fuel_tank_capacity = sum([float(f) for f in fuel_tank_capacity.split('+')])
                specs['fuel_tank_capacity'] = float(fuel_tank_capacity)

            elif 'gross battery capacity' in key:
                specs['battery_capacity'] = float(value[:-4].split('-')[0])

            elif 'battery technology' in key:
                specs['battery_tech'] = value

            elif 'average energy consumption' in key:
                specs['electric_consumption'] = float(value.split(' kWh')[0].split('-')[0])

            elif 'electric range' in key:
                specs['electric_range'] = float(value.split(' km')[0].split('-')[0].strip('<').strip('>'))

            elif 'system power' in key:
                power = value.split(' Hp')[0]
                if '+' in power:
                    power = sum([int(p) for p in power.split('+')])
                specs['power'] = int(power)

            elif 'system torque' in key:
                specs['torque'] = int(value.split(' ')[0])

            elif 'emission standard' in key:
                specs['emission_standard'] = value[:-1]

            elif 'engine displacement' in key:
                specs['displacement'] = int(value.split(' cm3')[0])

            elif 'power' == key.strip(' '):
                power_no_system = int(value.split(' Hp ')[0])

            elif 'number of gears' in key or 'type of gearbox' in key:
                if 'automatic' in value:
                    specs['transmission'] = 'automatic'
                elif 'manual' in value:
                    specs['transmission'] = 'manual'

                if 'gears' in value:
                    specs['gears'] = value.split(' gears')[0]

            elif 'drive wheel' in key:
                if 'Front' in value:
                    specs['traction'] = 'front'
                elif 'Rear' in value:
                    specs['traction'] = 'rear'
                elif 'All wheel drive' in value:
                    specs['traction'] = '4wd'

            elif 'kerb weight' in key:
                specs['weight'] = int(float(value.split(' kg')[0].split('-')[0].split('/')[-1]))

            elif 'length' == key.strip(' '):
                specs['length'] = int(float(value.split(' mm')[0].split('-')[0].split('/')[-1]))

            elif 'width' == key.strip(' '):
                specs['width'] = int(float(value.split(' mm')[0].split('-')[0].split('/')[-1]))

            elif 'height' == key.strip(' '):
                specs['height'] = int(float(value.split(' mm')[0].split('-')[0].split('/')[-1]))

            elif 'wheelbase' == key.strip(' '):
                specs['wheelbase'] = int(float(value.split(' mm')[0].split('-')[0].split('/')[-1]))

            elif 'clearance' in key:
                specs['clearance'] = int(float(value.split(' mm')[0].split('-')[0].split('/')[-1]))

            elif 'tires' in key:
                specs['tires'] = value.split('; ')

        # phase 2
        if not 'power' in specs or not specs['power']:
            specs['power'] = power_no_system

        if 'powertrain_architecture' in specs and specs['powertrain_architecture']:
            if 'PHEV' in specs['powertrain_architecture']:
                specs['powertrain_architecture'] = 'PHEV'
                specs['fuel_type'] = 'plug-in hybrid'
            elif 'BEV' in specs['powertrain_architecture']:
                specs['powertrain_architecture'] = 'BEV'
                specs['fuel_type'] = 'electric'
            elif 'FHEV' in specs['powertrain_architecture']:
                specs['powertrain_architecture'] = 'FHEV'
                if 'fuel_type' not in specs:
                    specs['fuel_type'] = 'hybrid gasoline'
                if specs['fuel_type'] == 'gasoline':
                    specs['fuel_type'] = 'hybrid gasoline'
                elif specs['fuel_type'] == 'diesel':
                    specs['fuel_type'] = 'hybrid diesel'
            elif 'internal combustion engine' in specs['powertrain_architecture'].lower():
                specs['powertrain_architecture'] = 'ICE'
            elif 'FCEV' in specs['powertrain_architecture']:
                specs['powertrain_architecture'] = 'FCEV'

        if 'body_type' in specs and specs['body_type']:
            body_type = specs['body_type'].lower()
            if 'crossover' in body_type or 'cuv' in body_type:
                specs['body_type'] = 'crossover'
            elif 'suv' in body_type or 'mpv' in body_type or 'sav' in body_type or 'sac' in body_type or 'off-road' in body_type:
                specs['body_type'] = 'suv'
            elif 'coupe' in body_type:
                specs['body_type'] = 'coupe'
            elif 'hatchback' in body_type:
                specs['body_type'] = 'hatchback'
            elif 'sedan' in body_type:
                specs['body_type'] = 'sedan'
            elif 'liftback' in body_type:
                specs['body_type'] = 'liftback'
            elif 'targa' in body_type:
                specs['body_type'] = 'targa'
            elif 'minivan' in body_type:
                specs['body_type'] = 'minivan'
            elif 'pickup' in body_type or 'pick-up' in body_type:
                specs['body_type'] = 'pickup'
            elif 'cabriolet' in body_type or 'cabrio' in body_type:
                specs['body_type'] = 'cabriolet'
            elif 'roadster' in body_type:
                specs['body_type'] = 'roadster'
            elif 'fastback' in body_type:
                specs['body_type'] = 'fastback'
            elif 'grand tourer' in body_type:
                specs['body_type'] = 'grand tourer'
            elif 'estate' in body_type or 'wagon' in body_type:
                specs['body_type'] = 'wagon'
            elif 'van' in body_type:
                specs['body_type'] = 'van'
            else:
                print(specs['body_type'])
                specs['body_type'] = 'other'

        for k, v in specs.items():
            if v is not None and v != 'null':
                self.indexed[self._current_make][self._current_model][self._current_generation][self._current_variant]['specs'][k] = v


    def _write_json(self, ):
        with open(self._output_file, 'w') as f:
            json.dump(self.indexed, f, indent=2)
