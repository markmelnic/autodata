from aevs import AEVS
from adnet import ADNET

# if __name__ == "__main__":
    # scraper = AEVS()
    # scraper.scrape()
    # scraper._dispose()

if __name__ == "__main__":
    only_include_makes = [
        "Abarth",
        "Acura",
        "Alfa Romeo",
        "Alpina",
        "Aston Martin",
        "Audi",
        "Bentley",
        "BMW",
        "Cadillac",
        "Chery",
        "Chevrolet",
        "Chrysler",
        "Citroen",
        "Dacia",
        "Daewoo",
        "Dodge",
        "Fiat",
        "Ford",
        "GMC",
        "Haval",
        "Honda",
        "Hyundai",
        "Infiniti",
        "Jaguar",
        "Jeep",
        "Kia",
        "Lancia",
        "Land Rover",
        "Lexus",
        "Lincoln",
        "Maserati",
        "Maybach",
        "Mazda",
        "Mercedes-Benz",
        "Mini",
        "Mitsubishi",
        "Nissan",
        "Opel",
        "Peugeot",
        "Porsche",
        "RAM",
        "Renault",
        "Rolls-Royce",
        "Rover",
        "Saab",
        "Seat",
        "Skoda",
        "Smart",
        "Subaru",
        "Suzuki",
        "Tesla",
        "Toyota",
        "Vauxhall",
        "Volkswagen",
        "Volvo",
    ]

    scraper = ADNET(
        'last-autodata-extended-full.json',
        True,
    )

    # scraper = ADNET(
    #     'last-autodata-extended.json',
    #     True,
    #     only_include_makes=only_include_makes
    # )

    scraper.scrape()
