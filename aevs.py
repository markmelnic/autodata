import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(message)s")


import os, enum, json, time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import NoSuchElementException, WebDriverException


class LinksEnum(enum.Enum):
    base = "https://www.autoevolution.com/cars/"


class AEVS:
    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("log-level=3")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option(
            "prefs", {"profile.default_content_setting_values.notifications": 2}
        )
        self.dv = webdriver.Chrome(
            chrome_options=chrome_options, executable_path=r"chromedriver.exe"
        )
        self._break = True

        if 'data.json' in os.listdir():
            with open('data.json', 'r') as f:
                self.indexed = json.load(f)
        else:
            self.indexed = {}

        self._current_make = None
        self._current_model = None
        self._current_generation = None
        self._current_variant = None

    def scrape(self, ):
        self.dv.get(LinksEnum.base.value)

        while self._break:
            try:
                _el_cars = self.dv.find_elements(By.CLASS_NAME, "carman")
                cars = [c.find_element(By.TAG_NAME, "h5") for c in _el_cars]
                cars = [(
                            c.find_element(By.TAG_NAME, "span").text,
                            c.find_element(By.TAG_NAME, "a").get_attribute("href"),
                        ) for c in cars]
                self._break = False
            except WebDriverException:
                pass
            finally:
                pass
        self._break = True

        for i, car in enumerate(cars):
            self._current_make = car[0]
            if self._current_make in self.indexed.keys():
                continue

            self.indexed[self._current_make] = {}
            logging.info(f'Scraping [{i+1}/{len(cars)}] {self._current_make}')

            self._scrape_make(car[1])

            self._write_json()


    def _scrape_make(self, link: str):
        while self._break:
            try:
                self.dv.get(link)
                WebDriverWait(self.dv, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "carmod"))
                )

                _el_models = self.dv.find_elements(By.CLASS_NAME, "carmod")
                models = [m.find_element(By.TAG_NAME, "a") for m in _el_models]
                models = [(
                            m.find_element(By.TAG_NAME, "h4").text[len(self._current_make)+1:],
                            m.find_element(By.TAG_NAME, "a").get_attribute("href"),
                        ) for m in _el_models]
                self._break = False
            except WebDriverException:
                pass
            finally:
                pass
        self._break = True

        for i, model in enumerate(models):
            self._current_model = model[0]
            if self._current_make in self.indexed[self._current_make].keys():
                continue

            self.indexed[self._current_make][self._current_model] = {}
            logging.info(f'   [{i+1}/{len(models)}] {self._current_model}')
            self._scrape_model(model[1])

            self._write_json()


    def _scrape_model(self, link: str):
        while self._break:
            try:
                self.dv.get(link)
                WebDriverWait(self.dv, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "carmodel"))
                )

                _el_generations = self.dv.find_elements(By.CLASS_NAME, "carmodel")
                generations = [m.find_element(By.TAG_NAME, "a") for m in _el_generations]
                generations = [(
                                g1.find_element(By.CLASS_NAME, "col-red").text,
                                g1.get_attribute("href"),
                                g2.find_element(By.CLASS_NAME, "years").text,
                                [(
                                    v.find_element(By.CLASS_NAME, "col-green2").text,
                                    v.find_element(By.TAG_NAME, "a").get_attribute("href"),
                                ) for v in g2.find_elements(By.CLASS_NAME, "engitm")],
                            ) for g1, g2 in zip(generations, _el_generations)]
                self._break = False
            except WebDriverException:
                pass
            finally:
                pass
        self._break = True

        for i, gen in enumerate(generations):
            self._current_generation = f'{gen[0]} {gen[2]}'
            if self._current_generation in self.indexed[self._current_make][self._current_model].keys():
                continue

            self.indexed[self._current_make][self._current_model][self._current_generation] = {}
            self.indexed[self._current_make][self._current_model][self._current_generation]['from'] = gen[2].split(' - ')[0]
            self.indexed[self._current_make][self._current_model][self._current_generation]['to'] = gen[2].split(' - ')[1]
            self.indexed[self._current_make][self._current_model][self._current_generation]['variants'] = []
            logging.info(f'      {self._current_generation}')

            for variant in gen[3]:
                self._current_variant = variant[0]
                logging.info(f'         {self._current_variant}')
                self._scrape_variant(variant[1])

            self._write_json()


    def _scrape_variant(self, link: str):
        while self._break:
            try:
                self.dv.get(link)
                time.sleep(3)

                self.dv.refresh()
                time.sleep(3)
                WebDriverWait(self.dv, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "techdata"))
                )

                variant = {}
                variant['engine'] = self._current_variant
                specs = self.dv.find_elements(By.CLASS_NAME, "techdata")

                for spec in specs:
                    spec_name = spec.find_element(By.CLASS_NAME, "title").text
                    if spec_name == '':
                        continue
                    if '\u2013' in spec_name:
                        spec_name = spec_name.split(' \u2013 ')[0]
                    variant[spec_name] = {}

                    cols1 = spec.find_elements(By.TAG_NAME, "dt")
                    cols2 = spec.find_elements(By.TAG_NAME, "dd")
                    for c1, c2 in zip(cols1, cols2):
                        if '\n' in c2.text:
                            variant[spec_name][c1.text] = c2.text.split('\n')
                        else:
                            variant[spec_name][c1.text] = c2.text

                self.indexed[self._current_make][self._current_model][self._current_generation]['variants'].append(variant)
                self._break = False
            except WebDriverException:
                pass
            finally:
                pass
        self._break = True


    def _write_json(self, ):
        with open('data.json', 'w') as f:
            json.dump(self.indexed, f, indent=2)


    def _dispose(self):
        self.dv.quit()
